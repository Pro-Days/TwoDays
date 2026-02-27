"""FAQ 시맨틱 검색 및 응답 조립."""

from __future__ import annotations

import json
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from scripts.main.integrations.bedrock import bedrock_embeddings
from scripts.main.shared.utils.log_utils import get_logger, truncate_text
from scripts.main.shared.utils.path_utils import convert_path

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)

FAQ_INDEX_PATH_ENV: str = "FAQ_INDEX_PATH"
FAQ_DATA_PATH_ENV: str = "FAQ_DATA_PATH"
FAQ_MATCH_THRESHOLD_ENV: str = "FAQ_MATCH_THRESHOLD"
FAQ_QUERY_CACHE_TTL_ENV: str = "FAQ_QUERY_CACHE_TTL_SEC"
FAQ_UNANSWERED_TABLE_ENV: str = "FAQ_UNANSWERED_TABLE"

CANDIDATE_COUNT: int = 3
CACHE_MAX_SIZE: int = 256
REQUIRED_ENV_VARS: tuple[str, ...] = (
    FAQ_INDEX_PATH_ENV,
    FAQ_DATA_PATH_ENV,
    FAQ_MATCH_THRESHOLD_ENV,
    FAQ_QUERY_CACHE_TTL_ENV,
    FAQ_UNANSWERED_TABLE_ENV,
)

_INDEX: "FaqIndex | None" = None
_INDEX_PATH: str | None = None
_DATA_PATH: str | None = None
_CACHE: "FaqQueryCache | None" = None


@dataclass(frozen=True)
class FaqEntry:
    entry_id: str
    question: str
    answer: str
    aliases: list[str]
    tags: list[str]


@dataclass(frozen=True)
class FaqMatch:
    entry: FaqEntry
    score: float


@dataclass(frozen=True)
class FaqAnswerResult:
    message: str
    matched: bool
    top_score: float | None
    top_ids: list[str]


@dataclass(frozen=True)
class FaqIndex:
    embeddings: np.ndarray
    ids: list[str]
    entries_by_id: dict[str, FaqEntry]


class FaqQueryCache:
    """FAQ 질문-응답 캐시 (LRU + TTL)"""

    def __init__(self, max_size: int, ttl_seconds: int) -> None:
        self.max_size: int = max_size
        self.ttl_seconds: int = ttl_seconds
        self._items: "OrderedDict[str, tuple[float, FaqAnswerResult]]" = OrderedDict()

    def get(self, key: str) -> FaqAnswerResult | None:
        now: float = time.time()
        cached: tuple[float, FaqAnswerResult] | None = self._items.get(key)

        if cached is None:
            return None

        expires_at, value = cached

        if expires_at <= now:
            self._items.pop(key, None)
            return None

        # 캐시 히트 시 LRU 순서 갱신
        self._items.move_to_end(key)

        return value

    def set(self, key: str, value: FaqAnswerResult) -> None:
        expires_at: float = time.time() + self.ttl_seconds
        self._items[key] = (expires_at, value)
        self._items.move_to_end(key)

        if len(self._items) > self.max_size:
            # 캐시 용량 초과 시 오래된 항목 제거
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()


def _require_env(name: str) -> str:
    # 필수 환경 변수 누락 시 즉시 실패
    value: str | None = os.getenv(name)

    if not value:
        raise RuntimeError(f"missing required env: {name}")

    return value


def _validate_required_envs() -> None:
    # 진입 시점 환경 변수 일괄 검증
    missing: list[str] = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]

    if missing:
        raise RuntimeError(f"missing required envs: {', '.join(missing)}")


def _resolve_asset_path(env_name: str) -> str:
    # FAQ 리소스 경로 환경 변수 기반 정규화
    env_value: str = _require_env(env_name)

    return convert_path(os.path.normpath(env_value))


def _parse_float_env(name: str) -> float:
    # 환경 변수 float 파싱
    raw_value: str = _require_env(name)

    try:
        return float(raw_value)

    except ValueError as exc:
        raise RuntimeError(f"invalid float env: {name}={raw_value}") from exc


def _parse_int_env(name: str) -> int:
    # 환경 변수 int 파싱
    raw_value: str = _require_env(name)

    try:
        return int(raw_value)

    except ValueError as exc:
        raise RuntimeError(f"invalid int env: {name}={raw_value}") from exc


def _normalize_string_list(value: list | None) -> list[str]:
    # 입력 문자열 리스트 정규화
    if value is None:
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def _parse_entry(item: dict) -> FaqEntry:
    # FAQ 엔트리 필수 필드 검증
    entry_id: str = str(item.get("id", "")).strip()
    question: str = str(item.get("question", "")).strip()
    answer: str = str(item.get("answer", "")).strip()
    aliases: list[str] = _normalize_string_list(item.get("aliases"))
    tags: list[str] = _normalize_string_list(item.get("tags"))

    if not entry_id or not question or not answer:
        raise ValueError("FAQ entry requires id/question/answer fields.")

    return FaqEntry(
        entry_id=entry_id,
        question=question,
        answer=answer,
        aliases=aliases,
        tags=tags,
    )


def _load_faq_data(path: str) -> dict[str, FaqEntry]:
    # JSON 데이터 엔트리 로드 및 유효성 검증
    with open(path, "r", encoding="utf-8") as file_obj:
        raw_data = json.load(file_obj)

    if not isinstance(raw_data, list):
        raise ValueError("FAQ data must be a list.")

    entries_by_id: dict[str, FaqEntry] = {}

    for item in raw_data:
        if not isinstance(item, dict):
            raise ValueError("FAQ entry must be an object.")

        entry: FaqEntry = _parse_entry(item)

        if entry.entry_id in entries_by_id:
            raise ValueError(f"Duplicate FAQ id: {entry.entry_id}")

        entries_by_id[entry.entry_id] = entry

    return entries_by_id


def _normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    # 코사인 유사도용 L2 정규화
    norms = np.linalg.norm(embeddings, axis=1)
    safe_norms = np.clip(norms, 1e-12, None)

    return embeddings / safe_norms[:, None]


def _load_faq_index(path: str, entries_by_id: dict[str, FaqEntry]) -> FaqIndex:
    with np.load(path) as data:
        # 필수 배열 존재 여부 확인
        if "embeddings" not in data or "ids" not in data:
            raise ValueError("FAQ index must contain embeddings and ids arrays.")

        embeddings: np.ndarray = np.asarray(data["embeddings"], dtype=np.float32)
        ids: list[str] = [str(value) for value in data["ids"]]

    # 임베딩 배열 차원 검증
    if embeddings.ndim != 2:
        raise ValueError("FAQ embeddings must be a 2D array.")

    # 임베딩/ID 길이 일치 검증
    if len(ids) != embeddings.shape[0]:
        raise ValueError("FAQ ids and embeddings length mismatch.")

    for entry_id in ids:
        # 데이터 파일 존재 여부 검증
        if entry_id not in entries_by_id:
            raise ValueError(f"FAQ id not found in data: {entry_id}")

    # 조회 시점 정규화 상태 유지
    normalized: np.ndarray = _normalize_embeddings(embeddings)

    return FaqIndex(
        embeddings=normalized,
        ids=ids,
        entries_by_id=entries_by_id,
    )


def _get_index() -> FaqIndex:
    global _INDEX, _INDEX_PATH, _DATA_PATH

    index_path: str = _resolve_asset_path(FAQ_INDEX_PATH_ENV)
    data_path: str = _resolve_asset_path(FAQ_DATA_PATH_ENV)

    if _INDEX is None or _INDEX_PATH != index_path or _DATA_PATH != data_path:
        # 경로 변경/캐시 부재 시 데이터 재로딩
        entries_by_id: dict[str, FaqEntry] = _load_faq_data(data_path)
        _INDEX = _load_faq_index(index_path, entries_by_id)
        _INDEX_PATH = index_path
        _DATA_PATH = data_path

        logger.info(
            "FAQ index loaded: "
            f"index_path={index_path} "
            f"data_path={data_path} "
            f"entries={len(entries_by_id)}"
        )

    return _INDEX


def _get_cache() -> FaqQueryCache:
    global _CACHE

    if _CACHE is None:
        # TTL 환경 변수 기반 캐시 지연 생성
        ttl_seconds: int = _parse_int_env(FAQ_QUERY_CACHE_TTL_ENV)
        _CACHE = FaqQueryCache(max_size=CACHE_MAX_SIZE, ttl_seconds=ttl_seconds)

    return _CACHE


def _embed_question(question: str) -> np.ndarray:
    # 질문 임베딩 및 1차원 정규화
    embeddings: list[list[float]] = bedrock_embeddings.embed_texts([question])

    if not embeddings:
        raise ValueError("FAQ embedding result is empty.")

    vector: np.ndarray = np.asarray(embeddings[0], dtype=np.float32)

    # 벡터 차원 검증
    if vector.ndim != 1:
        raise ValueError("FAQ embedding vector must be 1D.")

    norm: np.floating = np.linalg.norm(vector)

    # 영벡터 방지
    if norm <= 0:
        raise ValueError("FAQ embedding vector norm is zero.")

    return vector / norm


def _build_candidates(
    index: FaqIndex,
    scores: np.ndarray,
    top_k: int,
) -> list[FaqMatch]:
    if scores.size == 0:
        return []

    # 점수 상위 후보 선택
    limit: int = min(top_k, scores.size)
    sorted_indices: np.ndarray = np.argsort(scores)[::-1][:limit]
    candidates: list[FaqMatch] = []

    for idx in sorted_indices:
        entry_id: str = index.ids[int(idx)]
        entry: FaqEntry = index.entries_by_id[entry_id]
        score: float = float(scores[int(idx)])
        candidates.append(FaqMatch(entry=entry, score=score))

    return candidates


def _format_candidate_message(candidates: list[FaqMatch]) -> str:
    if not candidates:
        return "관련된 FAQ를 찾지 못했습니다."

    # 정확 매칭 부재 시 유사 질문 리스트 구성
    lines: list[str] = ["답변을 찾지 못했어요. 아래 질문이 비슷한지 확인해주세요:"]

    for idx, candidate in enumerate(candidates, start=1):
        lines.append(f"{idx}. {candidate.entry.question}")

    return "\n".join(lines)


def answer_question(question: str) -> FaqAnswerResult:
    # 환경 변수 누락 즉시 실패 처리
    _validate_required_envs()
    normalized_question: str = question.strip()

    if not normalized_question:
        # 빈 질문 입력 처리
        return FaqAnswerResult(
            message="질문을 입력해주세요.",
            matched=False,
            top_score=None,
            top_ids=[],
        )

    # 캐시 결과 우선 확인
    cache: FaqQueryCache = _get_cache()
    cached: FaqAnswerResult | None = cache.get(normalized_question)

    if cached is not None:
        # 캐시 히트 즉시 반환
        return cached

    # 임계값/인덱스 준비 및 코사인 유사도 계산
    threshold: float = _parse_float_env(FAQ_MATCH_THRESHOLD_ENV)
    top_k: int = CANDIDATE_COUNT
    index: FaqIndex = _get_index()

    query_vector: np.ndarray = _embed_question(normalized_question)
    scores: np.ndarray = index.embeddings @ query_vector

    candidates: list[FaqMatch] = _build_candidates(index, scores, top_k)

    top_ids: list[str] = [candidate.entry.entry_id for candidate in candidates]
    top_score: float | None = candidates[0].score if candidates else None

    if candidates and candidates[0].score >= threshold:
        # 최고 점수 임계값 이상 시 답변 반환
        message: str = candidates[0].entry.answer
        result = FaqAnswerResult(
            message=message,
            matched=True,
            top_score=top_score,
            top_ids=top_ids[:1],
        )

    else:
        # 임계값 미달 시 유사 질문 목록 제공
        message: str = _format_candidate_message(candidates)
        result = FaqAnswerResult(
            message=message,
            matched=False,
            top_score=top_score,
            top_ids=top_ids,
        )

    # 동일 질문 중복 호출 방지 캐시 저장
    cache.set(normalized_question, result)

    logger.info(
        "FAQ answer generated: "
        f"matched={result.matched} "
        f"top_score={result.top_score} "
        f"question={truncate_text(normalized_question, 120)}"
    )

    return result


# def reset_cache_for_tests() -> None:
#     global _CACHE

#     if _CACHE is not None:
#         _CACHE.clear()

#     _CACHE = None


# def reset_index_for_tests() -> None:
#     global _INDEX, _INDEX_PATH, _DATA_PATH

#     _INDEX = None
#     _INDEX_PATH = None
#     _DATA_PATH = None
