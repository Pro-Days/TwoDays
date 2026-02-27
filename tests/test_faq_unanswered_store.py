"""FAQ 미응답 저장소 테스트."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

import pytest

from tests.support import bootstrap  # noqa: F401
from scripts.main.infrastructure.persistence import faq_unanswered_store as fus


def test_unanswered_store_requires_env(monkeypatch) -> None:
    # 필수 환경 변수 제거
    monkeypatch.delenv("FAQ_UNANSWERED_TABLE", raising=False)

    # 누락 환경 변수 오류 검증
    with pytest.raises(RuntimeError):
        fus.FaqUnansweredStore()


def test_save_unanswered_question_builds_keys(monkeypatch) -> None:
    # 환경 변수/고정 시간/UUID 준비
    monkeypatch.setenv("FAQ_UNANSWERED_TABLE", "faq-table")
    fixed_time = datetime.datetime(
        2026,
        2,
        26,
        12,
        34,
        56,
        tzinfo=datetime.timezone(datetime.timedelta(hours=9)),
    )
    fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")

    monkeypatch.setattr(fus, "_now_kst", lambda: fixed_time)
    monkeypatch.setattr(fus.uuid, "uuid4", lambda: fixed_uuid)

    # 저장 입력 데이터 구성
    store = fus.FaqUnansweredStore()
    data = fus.UnansweredQuestionInput(
        question="질문이 없어요",
        top_score=0.42,
        top_ids=["faq-001"],
        guild_id="guild",
        channel_id="channel",
        requester_id="user",
    )

    # 저장 실행
    item = store.save_unanswered_question(data)

    # 저장 결과 검증
    assert item is not None
    assert item["PK"] == "UNANSWERED#2026-02"
    assert (
        item["SK"]
        == "TS#2026-02-26T12:34:56+09:00#12345678-1234-5678-1234-567812345678"
    )
    assert item["question"] == "질문이 없어요"
    assert item["top_score"] == Decimal("0.42")
    assert item["top_ids"] == ["faq-001"]
    assert item["guild_id"] == "guild"
    assert item["channel_id"] == "channel"
    assert item["requester_id"] == "user"

    # DynamoDB put_item 호출 검증
    table = store.table
    assert table.last_put_item == item
