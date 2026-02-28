"""FAQ 모델 비교 기능 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tests.support import bootstrap  # noqa: F401
from scripts.main.features import faq_model_compare
from scripts.main.integrations.bedrock import bedrock_embeddings


def _write_faq_data(tmp_path: Path) -> str:
    # 테스트용 FAQ 데이터 저장
    entries = [
        {
            "id": "faq-001",
            "question": "첫 번째 질문",
            "answer": "첫 번째 답변",
            "aliases": [],
            "tags": [],
        },
        {
            "id": "faq-002",
            "question": "두 번째 질문",
            "answer": "두 번째 답변",
            "aliases": [],
            "tags": [],
        },
    ]
    data_path = tmp_path / "faq_data.json"
    data_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    return str(data_path)


def _write_index(
    tmp_path: Path,
    filename: str,
    ids: list[str],
    embeddings: list[list[float]],
    model_id: str | None,
) -> str:
    # 테스트용 FAQ 인덱스 저장
    payload: dict[str, object] = {
        "embeddings": np.asarray(embeddings, dtype=np.float32),
        "ids": np.asarray(ids),
    }

    if model_id is not None:
        payload["model_id"] = np.asarray(model_id)

    path = tmp_path / filename
    np.savez(path, **payload)

    return str(path)


def _write_config(tmp_path: Path, payload: dict[str, object]) -> str:
    # 테스트용 설정 파일 저장
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    return str(config_path)


def test_compare_reports_accuracy_and_confidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # 비교 입력 데이터 준비
    data_path = _write_faq_data(tmp_path)
    ids = ["faq-001", "faq-002"]
    index_a = _write_index(
        tmp_path,
        "faq_index_a.npz",
        ids=ids,
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        model_id="model-a",
    )
    index_b = _write_index(
        tmp_path,
        "faq_index_b.npz",
        ids=ids,
        embeddings=[[0.0, 1.0], [1.0, 0.0]],
        model_id="model-b",
    )
    config_path = _write_config(
        tmp_path,
        {
            "data_path": data_path,
            "threshold": 0.5,
            "top_k": 1,
            "questions": [
                {"text": "테스트 질문", "expected_faq_id": "faq-001"},
            ],
            "models": [
                {"label": "model-a", "index_path": index_a},
                {"label": "model-b", "index_path": index_b},
            ],
        },
    )

    # 임베딩 결과 고정
    def fake_embed_texts_with_model(
        model_id: str,
        texts: list[str],
    ) -> list[list[float]]:
        return [[1.0, 0.0]]

    monkeypatch.setattr(
        bedrock_embeddings,
        "embed_texts_with_model",
        fake_embed_texts_with_model,
    )

    # 비교 실행
    config = faq_model_compare.load_config(config_path)
    report = faq_model_compare.run_compare(config)

    # 모델별 집계 검증
    model_results = {item["model_label"]: item for item in report["models"]}
    assert model_results["model-a"]["accuracy_top1"] == pytest.approx(1.0)
    assert model_results["model-b"]["accuracy_top1"] == pytest.approx(0.0)
    assert model_results["model-a"]["avg_confidence"] == pytest.approx(0.5)

    # 질문 결과 검증
    question = report["questions"][0]
    results = {item["model_label"]: item for item in question["results"]}
    assert results["model-a"]["is_correct"] is True
    assert results["model-b"]["is_correct"] is False
    assert results["model-a"]["confidence"] == pytest.approx(0.5)


def test_compare_raises_on_missing_model_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # model_id 누락 인덱스 준비
    data_path = _write_faq_data(tmp_path)
    ids = ["faq-001"]
    index_path = _write_index(
        tmp_path,
        "faq_index_missing.npz",
        ids=ids,
        embeddings=[[1.0, 0.0]],
        model_id=None,
    )
    config_path = _write_config(
        tmp_path,
        {
            "data_path": data_path,
            "threshold": 0.5,
            "top_k": 1,
            "questions": [
                {"text": "테스트 질문", "expected_faq_id": "faq-001"},
            ],
            "models": [
                {"label": "model-x", "index_path": index_path},
            ],
        },
    )

    # 임베딩 호출 차단
    def fake_embed_texts_with_model(
        model_id: str,
        texts: list[str],
    ) -> list[list[float]]:
        return [[1.0, 0.0]]

    monkeypatch.setattr(
        bedrock_embeddings,
        "embed_texts_with_model",
        fake_embed_texts_with_model,
    )

    # model_id 누락 오류 검증
    config = faq_model_compare.load_config(config_path)

    with pytest.raises(ValueError):
        faq_model_compare.run_compare(config)


def test_load_config_requires_expected_id(tmp_path: Path) -> None:
    # 정답 FAQ ID 누락 설정 준비
    config_path = _write_config(
        tmp_path,
        {
            "data_path": "assets/faq/faq_data.json",
            "questions": [
                {"text": "테스트 질문"},
            ],
            "models": [
                {"label": "model-x", "index_path": "assets/faq/faq_index.npz"},
            ],
        },
    )

    # 설정 오류 검증
    with pytest.raises(ValueError):
        faq_model_compare.load_config(config_path)
