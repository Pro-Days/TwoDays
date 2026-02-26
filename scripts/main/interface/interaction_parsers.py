"""디스코드 인터랙션/컨텍스트 메뉴 파서."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class ApplicationCommandType(IntEnum):
    CHAT_INPUT = 1
    USER = 2
    MESSAGE = 3


@dataclass(frozen=True)
class MessageContextTarget:
    message_id: str
    channel_id: str
    author_id: str | None
    application_id: str | None
    interaction_user_id: str | None


def _stringify_id(value: Any) -> str | None:
    if value is None:
        return None

    return str(value)


def resolve_requester_id(body: dict[str, Any]) -> str | None:
    member: dict[str, Any] = body.get("member", {})
    member_user: dict[str, Any] = member.get("user", {})
    user: dict[str, Any] = body.get("user", {}) or member_user

    return _stringify_id(user.get("id"))


def resolve_message_target(body: dict[str, Any]) -> MessageContextTarget | None:
    data: dict[str, Any] = body.get("data", {})
    target_id: str | None = _stringify_id(data.get("target_id"))

    if not target_id:
        return None

    resolved: dict[str, Any] = data.get("resolved", {})
    messages: dict[str, Any] = resolved.get("messages", {})
    message: dict[str, Any] | None = messages.get(target_id) or messages.get(
        str(target_id)
    )

    if not isinstance(message, dict):
        return None

    message_id: str | None = _stringify_id(message.get("id")) or target_id
    channel_id: str | None = _stringify_id(message.get("channel_id"))
    channel_id = channel_id or _stringify_id(body.get("channel_id"))
    channel_id = channel_id or _stringify_id(body.get("channel", {}).get("id"))

    if not message_id or not channel_id:
        return None

    author_id: str | None = _stringify_id(message.get("author", {}).get("id"))
    application_id: str | None = _stringify_id(message.get("application_id"))
    interaction: dict[str, Any] = message.get("interaction", {}) or {}
    interaction_user_id: str | None = _stringify_id(
        interaction.get("user", {}).get("id")
    )

    return MessageContextTarget(
        message_id=message_id,
        channel_id=channel_id,
        author_id=author_id,
        application_id=application_id,
        interaction_user_id=interaction_user_id,
    )


def can_delete_message(
    requester_id: str | None,
    admin_id: str | None,
    app_id: str | None,
    target: MessageContextTarget,
) -> bool:
    if not app_id:
        return False

    if requester_id is None:
        return False

    if admin_id and requester_id == admin_id:
        return True

    if target.interaction_user_id and requester_id == target.interaction_user_id:
        return True

    return False
