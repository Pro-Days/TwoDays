"""FAQ 명령 처리 테스트."""

from __future__ import annotations

import importlib
import json

from tests.support import bootstrap  # noqa: F401
from scripts.main.features import faq_answer


class _FakeSender:
    def __init__(self) -> None:
        # 전송 메시지/옵션 기록 초기화
        self.messages: list[str] = []
        self.kwargs: list[dict] = []

    def __call__(self, event: dict, msg: str, **kwargs) -> dict:
        # 전송 요청 기록
        self.messages.append(msg)
        self.kwargs.append(kwargs)
        return {"statusCode": 200, "body": json.dumps({"msg": msg})}


def _load_lambda(monkeypatch):
    # Lambda 환경 변수 설정
    monkeypatch.setenv("DISCORD_ADMIN_ID", "admin")
    monkeypatch.setenv("DISCORD_APP_ID", "app")
    monkeypatch.setenv("DISCORD_LOG_CHANNEL_ID", "log")
    monkeypatch.setenv("DISCORD_TOKEN", "token")

    import scripts.main.lambda_function as lf

    # 모듈 재로딩으로 환경 변수 반영
    return importlib.reload(lf)


def test_cmd_question_requires_text(monkeypatch) -> None:
    # Lambda/발신자 준비
    lf = _load_lambda(monkeypatch)
    sender = _FakeSender()
    monkeypatch.setattr(lf.sm, "send", sender)

    # 질문 옵션 없는 요청 실행
    event = {"body": json.dumps({"data": {"name": "질문", "options": []}})}
    lf.cmd_question(event, [])

    # 안내 메시지 검증
    assert sender.messages[-1] == "질문을 입력해주세요."


def test_cmd_question_matched(monkeypatch) -> None:
    # Lambda/발신자 준비
    lf = _load_lambda(monkeypatch)
    sender = _FakeSender()
    monkeypatch.setattr(lf.sm, "send", sender)

    # 매칭 답변 결과 구성
    result = faq_answer.FaqAnswerResult(
        message="답변입니다.",
        matched=True,
        top_score=0.9,
        top_ids=["faq-001"],
    )

    # FAQ 답변 모킹
    monkeypatch.setattr(lf.faq, "answer_question", lambda _: result)

    # 질문 요청 실행
    event = {
        "body": json.dumps(
            {
                "data": {"name": "질문", "options": [{"name": "질문", "value": "hi"}]},
                "channel_id": "123",
            }
        )
    }
    lf.cmd_question(event, [{"name": "질문", "value": "hi"}])

    # 매칭 응답/로그 검증
    assert sender.messages[-1] == "답변입니다."
    assert sender.kwargs[-1]["error"] == "질문: hi\n답변: 답변입니다."


def test_cmd_question_unmatched_saves(monkeypatch) -> None:
    # Lambda/발신자 준비
    lf = _load_lambda(monkeypatch)
    sender = _FakeSender()
    monkeypatch.setattr(lf.sm, "send", sender)
    saved: dict[str, object] = {}

    # 미응답 저장소 모킹
    class _FakeStore:
        def __init__(self) -> None:
            saved["store"] = self

        def save_unanswered_question(self, data) -> None:
            saved["data"] = data

    # 유사 질문 결과 구성
    result = faq_answer.FaqAnswerResult(
        message="유사 질문을 확인해주세요.",
        matched=False,
        top_score=0.2,
        top_ids=["faq-001", "faq-002"],
    )

    # FAQ 답변/저장소 모킹
    monkeypatch.setattr(lf.faq, "answer_question", lambda _: result)
    monkeypatch.setattr(lf.fus, "FaqUnansweredStore", _FakeStore)

    # 질문 요청 실행
    event = {
        "body": json.dumps(
            {
                "data": {"name": "질문", "options": [{"name": "질문", "value": "hi"}]},
                "guild_id": "guild",
                "channel": {"id": "channel"},
                "member": {"user": {"id": "user"}},
            }
        )
    }
    lf.cmd_question(event, [{"name": "질문", "value": "hi"}])

    # 저장 요청 및 응답 검증
    assert sender.messages[-1] == "유사 질문을 확인해주세요."
    assert sender.kwargs[-1]["log_type"] == lf.sm.LogType.FAQ_UNMATCHED

    error_payload = json.loads(sender.kwargs[-1]["error"])
    assert error_payload["question"] == "hi"
    assert error_payload["response"] == "유사 질문을 확인해주세요."
    assert error_payload["top_score"] == 0.2
    assert error_payload["top_ids"] == ["faq-001", "faq-002"]
    assert saved["data"].question == "hi"
    assert saved["data"].guild_id == "guild"
    assert saved["data"].channel_id == "channel"
    assert saved["data"].requester_id == "user"
