"""FAQ 인덱스 바이너리 증분 갱신."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from scripts.main.integrations.bedrock import bedrock_embeddings
from scripts.main.shared.utils.path_utils import convert_path

FAQ_INDEX_PATH_ENV: str = "FAQ_INDEX_PATH"
FAQ_DATA_PATH_ENV: str = "FAQ_DATA_PATH"
INDEX_SCHEMA_VERSION: str = "v1"
HASHES_KEY: str = "hashes"
MODEL_ID_KEY: str = "model_id"
SCHEMA_VERSION_KEY: str = "schema_version"
HASH_DELIMITER: str = "\n"


@dataclass(frozen=True)
class ExistingIndex:
    embeddings: np.ndarray
    ids: list[str]
    hashes: list[str]
    model_id: str
    schema_version: str


def _require_env(name: str) -> str:
    # 필수 환경 변수 조회
    value: str | None = os.getenv(name)

    if not value:
        raise RuntimeError(f"missing required env: {name}")

    return value


def _resolve_asset_path(env_name: str, override: str | None) -> str:
    # 환경 변수/인자 기반 경로 정규화
    if override:
        normalized_override: str = convert_path(os.path.normpath(override))
        return normalized_override

    env_value: str = _require_env(env_name)

    return convert_path(os.path.normpath(env_value))


def _resolve_model_id(override: str | None) -> str:
    # 모델 ID 우선순위 처리
    if override and override.strip():
        return override.strip()

    return bedrock_embeddings.EMBED_MODEL_ID


def _parse_args(argv: list[str]) -> argparse.Namespace:
    # CLI 인자 파싱
    parser = argparse.ArgumentParser(description="FAQ 인덱스 빌더")
    parser.add_argument("--data-path", type=str)
    parser.add_argument("--index-path", type=str)
    parser.add_argument("--model-id", type=str)

    return parser.parse_args(argv)


def _normalize_string_list(value: list | None) -> list[str]:
    if value is None:
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def _build_text_parts(entry: dict) -> list[str]:
    # 질문/별칭/태그 결합 리스트 구성
    question: str = str(entry.get("question", "")).strip()
    aliases: list[str] = _normalize_string_list(entry.get("aliases"))
    tags: list[str] = _normalize_string_list(entry.get("tags"))
    parts: list[str] = [question]

    if aliases:
        parts.extend(aliases)

    if tags:
        parts.extend(tags)

    return parts


def _build_embedding_text(entry: dict) -> str:
    # 임베딩 입력 텍스트 구성
    parts: list[str] = _build_text_parts(entry)

    return HASH_DELIMITER.join(parts)


def _build_text_hash(entry: dict) -> str:
    # 질문 텍스트 해시 생성
    parts: list[str] = _build_text_parts(entry)
    joined: str = HASH_DELIMITER.join(parts)

    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _normalize_index_text(value: object) -> str:
    # NumPy bytes 타입 문자열 정규화
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode("utf-8")

    return str(value)


def _read_scalar_text(value: np.ndarray) -> str:
    # 메타데이터 단일 값 검증
    if value.size != 1:
        raise ValueError("FAQ index metadata must be a single value.")

    return _normalize_index_text(value.reshape(-1)[0])


def _load_existing_index(path: str) -> ExistingIndex | None:
    # 기존 인덱스 파일 존재 여부 확인
    if not Path(path).exists():
        return None

    with np.load(path) as data:
        # 필수 배열 존재 여부 확인
        if "embeddings" not in data or "ids" not in data:
            return None

        embeddings: np.ndarray = np.asarray(data["embeddings"], dtype=np.float32)
        ids: list[str] = [_normalize_index_text(value) for value in data["ids"]]

        # 임베딩/ID 길이 및 차원 검증
        if embeddings.ndim != 2 or len(ids) != embeddings.shape[0]:
            return None

        # 메타데이터 키 존재 여부 확인
        if (
            HASHES_KEY not in data
            or MODEL_ID_KEY not in data
            or SCHEMA_VERSION_KEY not in data
        ):
            return None

        hashes: list[str] = [_normalize_index_text(value) for value in data[HASHES_KEY]]

        # 해시/ID 길이 일치 검증
        if len(hashes) != len(ids):
            return None

        model_id: str = _read_scalar_text(data[MODEL_ID_KEY])
        schema_version: str = _read_scalar_text(data[SCHEMA_VERSION_KEY])

    return ExistingIndex(
        embeddings=embeddings,
        ids=ids,
        hashes=hashes,
        model_id=model_id,
        schema_version=schema_version,
    )


def _load_entries(path: str) -> list[dict]:
    # 입력 JSON 검증 및 임베딩 대상 엔트리 추출
    with open(path, "r", encoding="utf-8") as file_obj:
        raw_data = json.load(file_obj)

    if not isinstance(raw_data, list):
        raise ValueError("FAQ data must be a list.")

    entries: list[dict] = []

    for item in raw_data:
        if not isinstance(item, dict):
            raise ValueError("FAQ entry must be an object.")

        entry_id: str = str(item.get("id", "")).strip()
        question: str = str(item.get("question", "")).strip()
        answer: str = str(item.get("answer", "")).strip()

        # 필수 필드 공백/누락 검증
        if not entry_id or not question or not answer:
            raise ValueError("FAQ entry requires id/question/answer fields.")

        entries.append(item)

    return entries


def main(argv: list[str] | None = None) -> None:
    # 인자 기본값 처리
    if argv is None:
        argv = []

    args = _parse_args(argv)

    # 데이터/인덱스 경로 해석
    data_path: str = _resolve_asset_path(FAQ_DATA_PATH_ENV, args.data_path)
    index_path: str = _resolve_asset_path(FAQ_INDEX_PATH_ENV, args.index_path)
    model_id: str = _resolve_model_id(args.model_id)

    # FAQ 데이터 텍스트/해시/ID 준비
    entries: list[dict] = _load_entries(data_path)
    texts: list[str] = [_build_embedding_text(entry) for entry in entries]

    ids: list[str] = [str(entry["id"]) for entry in entries]
    hashes: list[str] = [_build_text_hash(entry) for entry in entries]
    existing_index: ExistingIndex | None = _load_existing_index(index_path)

    embeddings_array: np.ndarray
    reused_count: int = 0
    embedded_count: int = 0
    pruned_count: int = 0

    if (
        existing_index is not None
        and existing_index.model_id == model_id
        and existing_index.schema_version == INDEX_SCHEMA_VERSION
    ):
        # 기존 인덱스 유효 시 변경 항목만 재임베딩
        existing_lookup: dict[str, tuple[np.ndarray, str]] = {
            entry_id: (existing_index.embeddings[idx], existing_index.hashes[idx])
            for idx, entry_id in enumerate(existing_index.ids)
        }
        pending_indices: list[int] = []
        pending_texts: list[str] = []
        embedding_rows: list[np.ndarray] = []

        for idx, entry_id in enumerate(ids):
            entry_hash: str = hashes[idx]
            existing_entry: tuple[np.ndarray, str] | None = existing_lookup.get(
                entry_id
            )

            if existing_entry is not None and existing_entry[1] == entry_hash:
                # 변경 없음 항목 재사용
                embedding_rows.append(existing_entry[0])
                reused_count += 1

            else:
                # 변경/신규 항목 임베딩 대기열 추가
                embedding_rows.append(np.empty((0,), dtype=np.float32))
                pending_indices.append(idx)
                pending_texts.append(texts[idx])

        if pending_texts:
            # 변경 질문 임베딩 요청
            new_embeddings: list[list[float]] = bedrock_embeddings.embed_texts(
                pending_texts, model_id
            )

            if len(new_embeddings) != len(pending_texts):
                raise ValueError("FAQ embedding count mismatch.")

            for offset, vector in enumerate(new_embeddings):
                target_idx: int = pending_indices[offset]
                embedding_rows[target_idx] = np.asarray(vector, dtype=np.float32)

        # 증분 결과 통계 계산
        embedded_count = len(pending_texts)
        pruned_count = len(set(existing_index.ids) - set(ids))

        if embedding_rows:
            embeddings_array: np.ndarray = np.stack(embedding_rows).astype(np.float32)

        else:
            # 전체 삭제 시 빈 행렬 저장
            embeddings_array: np.ndarray = np.zeros(
                (0, existing_index.embeddings.shape[1]), dtype=np.float32
            )

    else:
        # 신규 인덱스/메타데이터 변경 시 전체 재빌드
        embeddings: list[list[float]] = bedrock_embeddings.embed_texts(texts, model_id)

        if len(embeddings) != len(entries):
            raise ValueError("FAQ embedding count mismatch.")

        embeddings_array: np.ndarray = np.asarray(embeddings, dtype=np.float32)
        embedded_count = len(entries)

    ids_array: np.ndarray = np.asarray(ids)
    hashes_array: np.ndarray = np.asarray(hashes)

    index_dir: Path = Path(index_path).parent
    index_dir.mkdir(parents=True, exist_ok=True)

    # 인덱스/메타데이터 동시 저장
    np.savez(
        index_path,
        embeddings=embeddings_array,
        ids=ids_array,
        hashes=hashes_array,
        model_id=np.asarray(model_id),
        schema_version=np.asarray(INDEX_SCHEMA_VERSION),
    )

    print(
        "saved faq index: "
        f"path={index_path} "
        f"entries={len(entries)} "
        f"reused={reused_count} "
        f"embedded={embedded_count} "
        f"pruned={pruned_count}"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
