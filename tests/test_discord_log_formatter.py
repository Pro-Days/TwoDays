"""디스코드 로그 포맷터 테스트."""

from __future__ import annotations

import json

from scripts.main.integrations.discord import discord_log_formatter as dlf


def _make_event() -> dict[str, str]:
    body: str = json.dumps(
        {
            "data": {"name": "질문", "options": [{"name": "질문", "value": "hi"}]},
            "channel_id": "channel",
            "user": {"id": "user", "username": "name"},
        }
    )

    return {"body": body}


def test_build_log_payload_faq_unmatched() -> None:
    event = _make_event()
    msg_payload: dict[str, object] = {
        "question": "hi",
        "response": "유사 질문을 확인해주세요.",
        "top_score": 0.2,
        "top_ids": ["faq-001", "faq-002"],
    }
    msg: str = json.dumps(msg_payload, ensure_ascii=False)
    payload = dlf.build_log_payload(
        dlf.LogType.FAQ_UNMATCHED,
        event,
        msg,
        admin_id="admin",
    )

    assert payload is not None
    assert payload["content"] == "<@admin>"

    embed: dict[str, object] = payload["embeds"][0]
    assert embed["title"] == "투데이즈 FAQ 미매칭 로그"

    fields = {field["name"]: field["value"] for field in embed["fields"]}
    assert fields["faq_question"] == "hi"
    assert fields["faq_response"] == "유사 질문을 확인해주세요."
    assert fields["faq_top_score"] == "0.2"
    assert fields["faq_top_ids"] == "faq-001, faq-002"
