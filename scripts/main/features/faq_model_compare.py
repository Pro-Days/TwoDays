"""FAQ 모델별 비교 리포트 생성."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from scripts.main.integrations.bedrock import bedrock_embeddings
from scripts.main.shared.utils.path_utils import convert_path

if TYPE_CHECKING:
    from typing import Any


FAQ_MATCH_THRESHOLD_ENV: str = "FAQ_MATCH_THRESHOLD"
DEFAULT_TOP_K: int = 3


@dataclass(frozen=True)
class FaqEntry:
    entry_id: str
    question: str
    answer: str
    aliases: list[str]
    tags: list[str]


@dataclass(frozen=True)
class QuestionSpec:
    text: str
    expected_faq_id: str


@dataclass(frozen=True)
class ModelSpec:
    label: str
    index_path: str
    threshold: float | None
    top_k: int | None


@dataclass(frozen=True)
class CompareConfig:
    data_path: str
    questions: list[QuestionSpec]
    models: list[ModelSpec]
    threshold: float | None
    top_k: int
    output_path: str | None


@dataclass(frozen=True)
class FaqIndex:
    embeddings: np.ndarray
    ids: list[str]
    entries_by_id: dict[str, FaqEntry]
    model_id: str


@dataclass(frozen=True)
class ModelRuntime:
    label: str
    index_path: str
    threshold: float
    top_k: int
    index: FaqIndex


@dataclass(frozen=True)
class Candidate:
    entry: FaqEntry
    score: float


def _require_env(name: str) -> str:
    # 필수 환경 변수 누락 검증
    value: str | None = os.getenv(name)

    if not value:
        raise RuntimeError(f"missing required env: {name}")

    return value


def _parse_float_env(name: str) -> float:
    # 환경 변수 float 파싱
    raw_value: str = _require_env(name)

    try:
        return float(raw_value)

    except ValueError as exc:
        raise RuntimeError(f"invalid float env: {name}={raw_value}") from exc


def _normalize_string_list(value: list | None) -> list[str]:
    # 문자열 리스트 정규화
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
    # FAQ 데이터 파일 로드
    with open(path, "r", encoding="utf-8") as file_obj:
        raw_data = json.load(file_obj)

    if not isinstance(raw_data, list):
        raise ValueError("FAQ data must be a list.")

    entries_by_id: dict[str, FaqEntry] = {}

    for item in raw_data:
        # 엔트리 타입 검증
        if not isinstance(item, dict):
            raise ValueError("FAQ entry must be an object.")

        entry: FaqEntry = _parse_entry(item)

        if entry.entry_id in entries_by_id:
            raise ValueError(f"Duplicate FAQ id: {entry.entry_id}")

        entries_by_id[entry.entry_id] = entry

    return entries_by_id


def _normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    # 코사인 유사도 정규화
    norms = np.linalg.norm(embeddings, axis=1)
    safe_norms = np.clip(norms, 1e-12, None)

    return embeddings / safe_norms[:, None]


def _normalize_index_text(value: object) -> str:
    # NumPy bytes 문자열 변환
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode("utf-8")

    return str(value)


def _read_scalar_text(value: np.ndarray) -> str:
    # 메타데이터 단일 값 검증
    if value.size != 1:
        raise ValueError("FAQ index metadata must be a single value.")

    return _normalize_index_text(value.reshape(-1)[0])


def _load_faq_index(path: str, entries_by_id: dict[str, FaqEntry]) -> FaqIndex:
    # 인덱스 파일 로드
    with np.load(path) as data:
        if "embeddings" not in data or "ids" not in data:
            raise ValueError("FAQ index must contain embeddings and ids arrays.")

        if "model_id" not in data:
            raise ValueError("FAQ index must contain model_id metadata.")

        embeddings: np.ndarray = np.asarray(data["embeddings"], dtype=np.float32)
        ids: list[str] = [_normalize_index_text(value) for value in data["ids"]]
        model_id: str = _read_scalar_text(data["model_id"])

    if embeddings.ndim != 2:
        raise ValueError("FAQ embeddings must be a 2D array.")

    if len(ids) != embeddings.shape[0]:
        raise ValueError("FAQ ids and embeddings length mismatch.")

    for entry_id in ids:
        # FAQ 데이터 존재 여부 검증
        if entry_id not in entries_by_id:
            raise ValueError(f"FAQ id not found in data: {entry_id}")

    normalized: np.ndarray = _normalize_embeddings(embeddings)

    return FaqIndex(
        embeddings=normalized,
        ids=ids,
        entries_by_id=entries_by_id,
        model_id=model_id,
    )


def _build_candidates(
    index: FaqIndex,
    scores: np.ndarray,
    top_k: int,
) -> list[Candidate]:
    if scores.size == 0:
        return []

    # 상위 후보 개수 계산
    limit: int = min(top_k, scores.size)
    sorted_indices: np.ndarray = np.argsort(-scores, kind="mergesort")[:limit]
    candidates: list[Candidate] = []

    for idx in sorted_indices:
        # 후보 엔트리/점수 매핑
        entry_id: str = index.ids[int(idx)]
        entry: FaqEntry = index.entries_by_id[entry_id]
        score: float = float(scores[int(idx)])
        candidates.append(Candidate(entry=entry, score=score))

    return candidates


def _embed_question(model_id: str, question: str) -> np.ndarray:
    # 질문 임베딩 생성
    embeddings: list[list[float]] = bedrock_embeddings.embed_texts(
        [question],
        model_id,
    )

    if not embeddings:
        raise ValueError("FAQ embedding result is empty.")

    vector: np.ndarray = np.asarray(embeddings[0], dtype=np.float32)

    if vector.ndim != 1:
        raise ValueError("FAQ embedding vector must be 1D.")

    norm: np.floating = np.linalg.norm(vector)

    if norm <= 0:
        raise ValueError("FAQ embedding vector norm is zero.")

    return vector / norm


def _parse_required_str(value: object, field: str) -> str:
    # 필수 문자열 필드 검증
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string.")

    cleaned: str = value.strip()

    if not cleaned:
        raise ValueError(f"{field} must not be blank.")

    return cleaned


def _parse_optional_float(value: object, field: str) -> float | None:
    # 선택 float 필드 파싱
    if value is None:
        return None

    try:
        return float(value)

    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a float.") from exc


def _parse_optional_top_k(value: object, field: str) -> int | None:
    # 선택 top_k 필드 파싱
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer.")

    try:
        parsed = int(value)

    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer.") from exc

    if parsed <= 0:
        raise ValueError(f"{field} must be positive.")

    return parsed


def _parse_questions(value: object) -> list[QuestionSpec]:
    # 질문 목록 파싱
    if not isinstance(value, list):
        raise ValueError("questions must be a list.")

    questions: list[QuestionSpec] = []

    for item in value:
        if not isinstance(item, dict):
            raise ValueError("questions item must be an object.")

        text: str = _parse_required_str(item.get("text"), "questions.text")
        expected_faq_id: str = _parse_required_str(
            item.get("expected_faq_id"),
            "questions.expected_faq_id",
        )
        questions.append(
            QuestionSpec(
                text=text,
                expected_faq_id=expected_faq_id,
            )
        )

    if not questions:
        raise ValueError("questions must not be empty.")

    return questions


def _parse_models(value: object) -> list[ModelSpec]:
    # 모델 목록 파싱
    if not isinstance(value, list):
        raise ValueError("models must be a list.")

    models: list[ModelSpec] = []

    for item in value:
        if not isinstance(item, dict):
            raise ValueError("models item must be an object.")

        label: str = _parse_required_str(item.get("label"), "models.label")
        index_path: str = _parse_required_str(
            item.get("index_path"),
            "models.index_path",
        )
        threshold: float | None = _parse_optional_float(
            item.get("threshold"),
            "models.threshold",
        )
        top_k: int | None = _parse_optional_top_k(item.get("top_k"), "models.top_k")
        models.append(
            ModelSpec(
                label=label,
                index_path=index_path,
                threshold=threshold,
                top_k=top_k,
            )
        )

    if not models:
        raise ValueError("models must not be empty.")

    return models


def _normalize_path(value: str) -> str:
    # 운영체제 경로 정규화
    return convert_path(os.path.normpath(value))


def _load_raw_json(path: str) -> dict[str, Any]:
    # JSON 설정 파일 로드
    with open(path, "r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    if not isinstance(payload, dict):
        raise ValueError("config must be an object.")

    return payload


def load_config(path: str) -> CompareConfig:
    # 설정 파일 경로 정규화
    config_path: str = _normalize_path(path)
    payload: dict[str, Any] = _load_raw_json(config_path)

    # 필수 필드 파싱
    data_path: str = _parse_required_str(payload.get("data_path"), "data_path")
    threshold: float | None = _parse_optional_float(
        payload.get("threshold"),
        "threshold",
    )
    raw_top_k: object = payload.get("top_k", DEFAULT_TOP_K)
    top_k: int = _parse_optional_top_k(raw_top_k, "top_k") or DEFAULT_TOP_K
    output_path: str | None = None
    questions: list[QuestionSpec] = _parse_questions(payload.get("questions"))
    models: list[ModelSpec] = _parse_models(payload.get("models"))

    # 출력 경로 선택 처리
    if payload.get("output_path") is not None:
        output_path = _parse_required_str(payload.get("output_path"), "output_path")

    # 경로/모델 정규화 적용
    return CompareConfig(
        data_path=_normalize_path(data_path),
        questions=questions,
        models=[
            ModelSpec(
                label=model.label,
                index_path=_normalize_path(model.index_path),
                threshold=model.threshold,
                top_k=model.top_k,
            )
            for model in models
        ],
        threshold=threshold,
        top_k=top_k,
        output_path=_normalize_path(output_path) if output_path else None,
    )


def _resolve_default_threshold(config_threshold: float | None) -> float:
    # 전역 임계값 결정
    if config_threshold is not None:
        return config_threshold

    return _parse_float_env(FAQ_MATCH_THRESHOLD_ENV)


def _resolve_top_k(model_top_k: int | None, default_top_k: int) -> int:
    # 모델별 top_k 결정
    if model_top_k is not None:
        return model_top_k

    return default_top_k


def _resolve_threshold(
    model_threshold: float | None, default_threshold: float
) -> float:
    # 모델별 임계값 결정
    if model_threshold is not None:
        return model_threshold

    return default_threshold


def _build_model_runtime(
    entries_by_id: dict[str, FaqEntry],
    model: ModelSpec,
    default_threshold: float,
    default_top_k: int,
) -> ModelRuntime:
    # 모델 런타임 준비
    index: FaqIndex = _load_faq_index(model.index_path, entries_by_id)
    threshold: float = _resolve_threshold(model.threshold, default_threshold)
    top_k: int = _resolve_top_k(model.top_k, default_top_k)

    return ModelRuntime(
        label=model.label,
        index_path=model.index_path,
        threshold=threshold,
        top_k=top_k,
        index=index,
    )


def _build_candidates_payload(candidates: list[Candidate]) -> list[dict[str, object]]:
    # 후보 결과 변환
    payload: list[dict[str, object]] = []

    for candidate in candidates:
        payload.append(
            {
                "entry_id": candidate.entry.entry_id,
                "question": candidate.entry.question,
                "score": candidate.score,
                "answer": candidate.entry.answer,
            }
        )

    return payload


def _build_model_result(
    question: QuestionSpec,
    model: ModelRuntime,
) -> dict[str, object]:
    # 모델별 질문 비교 수행
    # 질문 임베딩 및 점수 계산
    query_vector: np.ndarray = _embed_question(model.index.model_id, question.text)
    scores: np.ndarray = model.index.embeddings @ query_vector
    candidates: list[Candidate] = _build_candidates(model.index, scores, model.top_k)
    top_ids: list[str] = [candidate.entry.entry_id for candidate in candidates]
    top_score: float | None = candidates[0].score if candidates else None
    # 결과 판정 계산
    matched: bool = top_score is not None and top_score >= model.threshold
    is_correct: bool = bool(top_ids) and top_ids[0] == question.expected_faq_id
    confidence: float | None = (
        top_score - model.threshold if top_score is not None else None
    )
    answer: str = candidates[0].entry.answer if matched else ""

    # 결과 페이로드 구성
    return {
        "model_label": model.label,
        "model_id": model.index.model_id,
        "index_path": model.index_path,
        "threshold": model.threshold,
        "top_score": top_score,
        "confidence": confidence,
        "matched": matched,
        "is_correct": is_correct,
        "top_ids": top_ids,
        "answer": answer,
        "candidates": _build_candidates_payload(candidates),
    }


def _build_report_questions(
    questions: list[QuestionSpec],
    models: list[ModelRuntime],
) -> list[dict[str, object]]:
    # 질문별 비교 결과 구성
    report: list[dict[str, object]] = []

    for question in questions:
        # 질문별 모델 비교 리스트 구성
        results: list[dict[str, object]] = []

        for model in models:
            # 모델별 결과 추가
            results.append(_build_model_result(question, model))

        # 질문 단위 결과 추가
        report.append(
            {
                "text": question.text,
                "expected_faq_id": question.expected_faq_id,
                "results": results,
            }
        )

    return report


def _build_model_aggregates(
    report_questions: list[dict[str, object]],
) -> list[dict[str, object]]:
    # 모델별 집계 구성
    aggregates: dict[str, dict[str, object]] = {}

    for question in report_questions:
        # 질문별 결과 추출
        results = question.get("results", [])

        for result in results:
            # 모델별 누적 버킷 확보
            model_label: str = str(result.get("model_label"))
            current = aggregates.get(model_label)

            if current is None:
                current = {
                    "model_label": model_label,
                    "model_id": result.get("model_id"),
                    "index_path": result.get("index_path"),
                    "correct_count": 0,
                    "total_count": 0,
                    "confidence_sum": 0.0,
                    "confidence_count": 0,
                }
                aggregates[model_label] = current

            # 전체 카운트 누적
            current["total_count"] = int(current["total_count"]) + 1

            # 정답 카운트 누적
            if bool(result.get("is_correct")):
                current["correct_count"] = int(current["correct_count"]) + 1

            # 확신도 누적
            confidence_value = result.get("confidence")

            if confidence_value is not None:
                current["confidence_sum"] = float(current["confidence_sum"]) + float(
                    confidence_value
                )
                current["confidence_count"] = int(current["confidence_count"]) + 1

    aggregates_list: list[dict[str, object]] = []

    for aggregate in aggregates.values():
        # 모델별 지표 계산
        correct_count: int = int(aggregate["correct_count"])
        total_count: int = int(aggregate["total_count"])
        confidence_sum: float = float(aggregate["confidence_sum"])
        confidence_count: int = int(aggregate["confidence_count"])
        accuracy_top1: float = correct_count / total_count if total_count else 0.0
        avg_confidence: float | None = (
            confidence_sum / confidence_count if confidence_count else None
        )
        aggregates_list.append(
            {
                "model_label": aggregate["model_label"],
                "model_id": aggregate["model_id"],
                "index_path": aggregate["index_path"],
                "accuracy_top1": accuracy_top1,
                "correct_count": correct_count,
                "total_count": total_count,
                "avg_confidence": avg_confidence,
            }
        )

    return aggregates_list


def run_compare(config: CompareConfig) -> dict[str, object]:
    # 기본 임계값/데이터 준비
    default_threshold: float = _resolve_default_threshold(config.threshold)
    default_top_k: int = config.top_k
    entries_by_id: dict[str, FaqEntry] = _load_faq_data(config.data_path)

    # 모델 런타임 구성
    models: list[ModelRuntime] = [
        _build_model_runtime(entries_by_id, model, default_threshold, default_top_k)
        for model in config.models
    ]

    # 질문별 리포트 생성
    report_questions: list[dict[str, object]] = _build_report_questions(
        config.questions,
        models,
    )
    model_aggregates: list[dict[str, object]] = _build_model_aggregates(
        report_questions
    )

    # 최종 리포트 반환
    return {
        "settings": {
            "threshold": default_threshold,
            "top_k": default_top_k,
        },
        "models": model_aggregates,
        "questions": report_questions,
    }


def write_report(report: dict[str, object], output_path: str | None) -> None:
    # 리포트 출력 경로 처리
    serialized: str = json.dumps(report, ensure_ascii=False, indent=2)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")

        return

    print(serialized)
