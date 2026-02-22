from __future__ import annotations

import json
import logging
import os
from typing import Any

# 로깅 설정 여부를 추적하는 전역 변수
_CONFIGURED = False


def _resolve_level(level: str | int | None = None) -> int:
    """로깅 레벨을 문자열 또는 정수로 받아서 정수 레벨로 변환"""

    if isinstance(level, int):
        return level

    level_name: str = level or os.getenv("TWODAYS_LOG_LEVEL") or "INFO"
    return getattr(logging, str(level_name).upper(), logging.INFO)


def setup_logging(level: str | int | None = None) -> None:
    """
    설정된 로깅 레벨에 따라 로깅을 초기화
    """

    global _CONFIGURED

    resolved_level: int = _resolve_level(level)
    root_logger: logging.Logger = logging.getLogger()

    # 이미 핸들러가 설정되어 있으면 중복 설정 방지
    if not root_logger.handlers:
        handler: logging.StreamHandler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(handler)

    root_logger.setLevel(resolved_level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)


def truncate_text(value: Any, max_length: int = 500) -> str:
    """긴 텍스트를 지정된 최대 길이로 자르고, 잘린 부분이 있으면 표시"""

    text: str = str(value)

    if len(text) <= max_length:
        return text

    return f"{text[:max_length]}... (truncated {len(text) - max_length} chars)"


def to_json(value: Any, max_length: int = 1000) -> str:
    try:
        text: str = json.dumps(value, ensure_ascii=False, default=str)

    except Exception:
        text = str(value)

    return truncate_text(text, max_length=max_length)


def summarize_event(event: dict) -> dict[str, Any]:
    """이벤트 객체에서 주요 정보를 추출하여 요약"""

    summary: dict[str, Any] = {"keys": sorted(event.keys())}

    if "action" in event:
        summary["action"] = event.get("action")

    body: str | None = event.get("body")
    if not isinstance(body, str):
        return summary

    try:
        body_json: dict[str, Any] = json.loads(body)

    except Exception:
        summary["body"] = truncate_text(body, 300)
        return summary

    data: dict[str, Any] = body_json.get("data", {})
    member: dict[str, Any] = body_json.get("member", {}).get("user", {})
    channel: dict[str, Any] = body_json.get("channel", {})

    summary.update(
        {
            "command": data.get("name"),
            "option_count": len(data.get("options", [])),
            "member_id": member.get("id"),
            "member_username": member.get("username"),
            "channel_id": channel.get("id"),
            "guild_id": body_json.get("guild_id"),
        }
    )

    return summary
