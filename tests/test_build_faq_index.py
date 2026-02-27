"""FAQ 인덱스 빌더 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tests.support import bootstrap  # noqa: F401
from scripts._manage_cmd import build_faq_index
from scripts.main.integrations.bedrock import bedrock_embeddings


def _make_entry(
    entry_id: str,
    question: str,
    answer: str = "답변입니다.",
    aliases: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, object]:
    # 테스트용 FAQ 엔트리 생성
    return {
        "id": entry_id,
        "question": question,
        "answer": answer,
        "aliases": aliases or [],
        "tags": tags or [],
    }


def _write_faq_data(tmp_path: Path, entries: list[dict[str, object]]) -> str:
    # FAQ 데이터 파일 저장
    data_path = tmp_path / "faq_data.json"
    data_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    return str(data_path)


def _write_index(
    path: Path,
    ids: list[str],
    embeddings: list[list[float]],
    hashes: list[str] | None = None,
    model_id: str | None = None,
    schema_version: str | None = None,
) -> str:
    # FAQ 인덱스 파일 생성
    payload: dict[str, object] = {
        "embeddings": np.asarray(embeddings, dtype=np.float32),
        "ids": np.asarray(ids),
    }

    if hashes is not None:
        payload["hashes"] = np.asarray(hashes)

    if model_id is not None:
        payload["model_id"] = np.asarray(model_id)

    if schema_version is not None:
        payload["schema_version"] = np.asarray(schema_version)

    np.savez(path, **payload)

    return str(path)


def _configure_env(monkeypatch, data_path: str, index_path: str) -> None:
    # 환경 변수 설정
    monkeypatch.setenv("FAQ_DATA_PATH", data_path)
    monkeypatch.setenv("FAQ_INDEX_PATH", index_path)


def _read_strings(values: np.ndarray) -> list[str]:
    # NumPy 문자열 배열 정규화
    flattened = values.reshape(-1)

    return [build_faq_index._normalize_index_text(value) for value in flattened]


def test_hash_uses_delimiter() -> None:
    # 구분자 포함 여부에 따른 해시 차이 검증
    first = _make_entry("faq-001", "ab", aliases=["c"])
    second = _make_entry("faq-002", "a", aliases=["bc"])

    first_hash = build_faq_index._build_text_hash(first)
    second_hash = build_faq_index._build_text_hash(second)

    assert first_hash != second_hash


def test_prune_deleted_entries(monkeypatch, tmp_path: Path) -> None:
    # 삭제된 FAQ 항목 정리 시나리오 준비
    entry_first = _make_entry("faq-001", "첫 번째 질문")
    entry_second = _make_entry("faq-002", "두 번째 질문")
    data_path = _write_faq_data(tmp_path, [entry_first])
    index_path = tmp_path / "faq_index.npz"
    hashes = [
        build_faq_index._build_text_hash(entry_first),
        build_faq_index._build_text_hash(entry_second),
    ]
    _write_index(
        index_path,
        ids=["faq-001", "faq-002"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        hashes=hashes,
        model_id=bedrock_embeddings.EMBED_MODEL_ID,
        schema_version=build_faq_index.INDEX_SCHEMA_VERSION,
    )
    _configure_env(monkeypatch, data_path, str(index_path))

    # 임베딩 호출 금지 검증용 모킹
    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        raise AssertionError("embed_texts should not be called.")

    monkeypatch.setattr(bedrock_embeddings, "embed_texts", fake_embed_texts)

    # 인덱스 갱신 실행
    build_faq_index.main()

    with np.load(index_path) as data:
        ids = _read_strings(data["ids"])
        embeddings = np.asarray(data["embeddings"], dtype=np.float32)
        hashes = _read_strings(data["hashes"])

    # 삭제 항목 반영 결과 검증
    assert ids == ["faq-001"]
    assert embeddings.tolist() == [[1.0, 0.0]]
    assert hashes == [build_faq_index._build_text_hash(entry_first)]


def test_reuse_unchanged_entries(monkeypatch, tmp_path: Path) -> None:
    # 변경 없는 엔트리 재사용 시나리오 준비
    entries = [
        _make_entry("faq-001", "첫 번째 질문"),
        _make_entry("faq-002", "두 번째 질문"),
    ]
    data_path = _write_faq_data(tmp_path, entries)
    index_path = tmp_path / "faq_index.npz"
    hashes = [build_faq_index._build_text_hash(entry) for entry in entries]
    original_embeddings = [[1.0, 0.0], [0.0, 1.0]]
    _write_index(
        index_path,
        ids=["faq-001", "faq-002"],
        embeddings=original_embeddings,
        hashes=hashes,
        model_id=bedrock_embeddings.EMBED_MODEL_ID,
        schema_version=build_faq_index.INDEX_SCHEMA_VERSION,
    )
    _configure_env(monkeypatch, data_path, str(index_path))

    # 임베딩 호출 금지 검증용 모킹
    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        raise AssertionError("embed_texts should not be called.")

    monkeypatch.setattr(bedrock_embeddings, "embed_texts", fake_embed_texts)

    # 인덱스 갱신 실행
    build_faq_index.main()

    with np.load(index_path) as data:
        embeddings = np.asarray(data["embeddings"], dtype=np.float32)

    # 기존 임베딩 유지 검증
    assert embeddings.tolist() == original_embeddings


def test_update_only_changed_entry(monkeypatch, tmp_path: Path) -> None:
    # 일부 엔트리 변경 시나리오 준비
    entries = [
        _make_entry("faq-001", "첫 번째 질문"),
        _make_entry("faq-002", "두 번째 질문"),
    ]
    updated_entries = [
        entries[0],
        _make_entry("faq-002", "두 번째 질문 (수정)"),
    ]
    data_path = _write_faq_data(tmp_path, updated_entries)
    index_path = tmp_path / "faq_index.npz"
    hashes = [build_faq_index._build_text_hash(entry) for entry in entries]
    _write_index(
        index_path,
        ids=["faq-001", "faq-002"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        hashes=hashes,
        model_id=bedrock_embeddings.EMBED_MODEL_ID,
        schema_version=build_faq_index.INDEX_SCHEMA_VERSION,
    )
    _configure_env(monkeypatch, data_path, str(index_path))
    captured: list[list[str]] = []

    # 변경 항목만 임베딩 호출되도록 모킹
    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        captured.append(texts)
        return [[2.0, 2.0]]

    monkeypatch.setattr(bedrock_embeddings, "embed_texts", fake_embed_texts)

    # 인덱스 갱신 실행
    build_faq_index.main()

    expected_text = build_faq_index._build_embedding_text(updated_entries[1])

    # 변경 항목 단일 호출 검증
    assert captured == [[expected_text]]

    with np.load(index_path) as data:
        embeddings = np.asarray(data["embeddings"], dtype=np.float32)

    # 변경 임베딩 반영 검증
    assert embeddings.tolist() == [[1.0, 0.0], [2.0, 2.0]]


def test_full_rebuild_when_metadata_missing(monkeypatch, tmp_path: Path) -> None:
    # 메타데이터 누락 시 전체 재빌드 시나리오 준비
    entries = [
        _make_entry("faq-001", "첫 번째 질문"),
        _make_entry("faq-002", "두 번째 질문"),
    ]
    data_path = _write_faq_data(tmp_path, entries)
    index_path = tmp_path / "faq_index.npz"
    _write_index(
        index_path,
        ids=["faq-001", "faq-002"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
    )
    _configure_env(monkeypatch, data_path, str(index_path))
    captured: list[list[str]] = []

    # 전체 임베딩 호출 모킹
    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        captured.append(texts)
        return [[3.0, 3.0], [4.0, 4.0]]

    monkeypatch.setattr(bedrock_embeddings, "embed_texts", fake_embed_texts)

    # 인덱스 재빌드 실행
    build_faq_index.main()

    expected_texts = [build_faq_index._build_embedding_text(entry) for entry in entries]

    # 전체 임베딩 호출 여부 검증
    assert captured == [expected_texts]

    with np.load(index_path) as data:
        # 메타데이터 저장 여부 검증
        assert build_faq_index.HASHES_KEY in data.files
        assert build_faq_index.MODEL_ID_KEY in data.files
        assert build_faq_index.SCHEMA_VERSION_KEY in data.files
        assert _read_strings(data[build_faq_index.MODEL_ID_KEY]) == [
            bedrock_embeddings.EMBED_MODEL_ID
        ]


def test_full_rebuild_on_model_change(monkeypatch, tmp_path: Path) -> None:
    # 모델 변경 시 전체 재빌드 시나리오 준비
    entries = [
        _make_entry("faq-001", "첫 번째 질문"),
        _make_entry("faq-002", "두 번째 질문"),
    ]
    data_path = _write_faq_data(tmp_path, entries)
    index_path = tmp_path / "faq_index.npz"
    hashes = [build_faq_index._build_text_hash(entry) for entry in entries]
    _write_index(
        index_path,
        ids=["faq-001", "faq-002"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        hashes=hashes,
        model_id="legacy-model",
        schema_version=build_faq_index.INDEX_SCHEMA_VERSION,
    )
    _configure_env(monkeypatch, data_path, str(index_path))
    captured: list[list[str]] = []

    # 전체 임베딩 호출 모킹
    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        captured.append(texts)
        return [[5.0, 5.0], [6.0, 6.0]]

    monkeypatch.setattr(bedrock_embeddings, "embed_texts", fake_embed_texts)

    # 인덱스 재빌드 실행
    build_faq_index.main()

    # 전체 임베딩 호출 검증
    assert len(captured) == 1
    assert len(captured[0]) == 2

    with np.load(index_path) as data:
        assert _read_strings(data[build_faq_index.MODEL_ID_KEY]) == [
            bedrock_embeddings.EMBED_MODEL_ID
        ]
