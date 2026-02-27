"""FAQ 답변 기능 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tests.support import bootstrap  # noqa: F401
from scripts.main.features import faq_answer
from scripts.main.integrations.bedrock import bedrock_embeddings


def _write_faq_files(tmp_path: Path) -> tuple[str, str]:
    # 테스트용 FAQ 데이터 구성
    entries = [
        {
            "id": "faq-001",
            "question": "봇 사용법이 궁금해요.",
            "answer": "슬래시 명령을 사용하면 됩니다.",
            "aliases": ["명령어 사용법"],
            "tags": ["사용법"],
        },
        {
            "id": "faq-002",
            "question": "데이터가 갱신되는 시간은 언제인가요?",
            "answer": "다음 날 00시 전후에 갱신됩니다.",
            "aliases": ["업데이트 시간"],
            "tags": ["업데이트"],
        },
    ]

    data_path = tmp_path / "faq_data.json"
    data_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    # 테스트용 임베딩/인덱스 생성
    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    ids = np.array([entry["id"] for entry in entries])
    index_path = tmp_path / "faq_index.npz"
    np.savez(index_path, embeddings=embeddings, ids=ids)

    return str(data_path), str(index_path)


def _configure_env(monkeypatch, data_path: str, index_path: str) -> None:
    # FAQ 환경 변수 설정
    monkeypatch.setenv("FAQ_DATA_PATH", data_path)
    monkeypatch.setenv("FAQ_INDEX_PATH", index_path)
    monkeypatch.setenv("FAQ_MATCH_THRESHOLD", "0.8")
    monkeypatch.setenv("FAQ_QUERY_CACHE_TTL_SEC", "300")
    monkeypatch.setenv("FAQ_UNANSWERED_TABLE", "faq-unanswered")

    # 캐시/인덱스 초기화
    faq_answer.reset_cache_for_tests()
    faq_answer.reset_index_for_tests()


def test_answer_question_matched(monkeypatch, tmp_path: Path) -> None:
    # FAQ 데이터/환경 준비
    data_path, index_path = _write_faq_files(tmp_path)
    _configure_env(monkeypatch, data_path, index_path)

    # 임베딩 결과 모킹
    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0]]

    monkeypatch.setattr(bedrock_embeddings, "embed_texts", fake_embed_texts)

    # FAQ 답변 실행
    result = faq_answer.answer_question("사용법 알려줘")

    # 매칭 결과 검증
    assert result.matched is True
    assert result.message == "슬래시 명령을 사용하면 됩니다."
    assert result.top_ids == ["faq-001"]


def test_answer_question_requires_envs(monkeypatch) -> None:
    # 필수 환경 변수 제거
    for name in faq_answer.REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    # 캐시/인덱스 초기화
    faq_answer.reset_cache_for_tests()
    faq_answer.reset_index_for_tests()

    # 누락 환경 변수 오류 검증
    with pytest.raises(RuntimeError):
        faq_answer.answer_question("테스트")


def test_answer_question_unmatched(monkeypatch, tmp_path: Path) -> None:
    # FAQ 데이터/환경 준비
    data_path, index_path = _write_faq_files(tmp_path)
    _configure_env(monkeypatch, data_path, index_path)
    monkeypatch.setenv("FAQ_MATCH_THRESHOLD", "0.95")
    faq_answer.reset_cache_for_tests()

    # 임베딩 결과 모킹
    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        return [[0.0, 0.0, 1.0]]

    monkeypatch.setattr(bedrock_embeddings, "embed_texts", fake_embed_texts)

    # FAQ 답변 실행
    result = faq_answer.answer_question("전혀 다른 질문")

    # 미매칭 결과 검증
    assert result.matched is False
    assert "답변을 찾지 못했어요" in result.message
    assert result.top_ids == ["faq-001", "faq-002"]
    lines = result.message.splitlines()
    assert lines[1] == "1. 봇 사용법이 궁금해요."
    assert lines[2] == "2. 데이터가 갱신되는 시간은 언제인가요?"


def test_answer_question_cache(monkeypatch, tmp_path: Path) -> None:
    # FAQ 데이터/환경 준비
    data_path, index_path = _write_faq_files(tmp_path)
    _configure_env(monkeypatch, data_path, index_path)
    calls = {"count": 0}

    # 임베딩 호출 횟수 추적 모킹
    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        calls["count"] += 1
        return [[1.0, 0.0, 0.0]]

    monkeypatch.setattr(bedrock_embeddings, "embed_texts", fake_embed_texts)

    # 동일 질문 연속 호출
    first = faq_answer.answer_question("캐시 테스트")
    second = faq_answer.answer_question("캐시 테스트")

    # 캐시 재사용 검증
    assert first.message == second.message
    assert calls["count"] == 1
