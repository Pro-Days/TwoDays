from __future__ import annotations

import json
import time
from enum import IntEnum
from typing import TYPE_CHECKING, Any

import scripts.main.integrations.discord.discord_admin_api as daa
from scripts.main.shared.utils.log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)


class LogType(IntEnum):
    COMMAND = 1
    ADMIN_COMMAND = 2
    COMMAND_ERROR = 3
    UPDATE = 4
    UPDATE_ERROR = 5
    PLAYER_UPDATE = 6


def _build_fields(embed_json: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"name": key, "value": value, "inline": False}
        for key, value in embed_json.items()
        if value is not None
    ]


def _command_text(body: dict[str, Any]) -> str | None:
    data = body.get("data", {})
    cmd_name = data.get("name")

    if cmd_name is None:
        return None

    if "options" in data:
        return f"{cmd_name}\n{data['options']}"

    return str(cmd_name)


def build_log_payload(
    log_type: LogType,
    event: dict[str, Any],
    msg: str = "",
    *,
    admin_id: str,
) -> dict[str, Any] | None:
    # send_msg는 전송만 담당하고, 로그 payload 조립은 여기서 일괄 처리
    now: str = f"<t:{int(time.time())}:f>"

    # 명령어 로그와 업데이트 로그는 입력 이벤트 구조가 달라 분기 처리
    if log_type in (
        LogType.COMMAND,
        LogType.ADMIN_COMMAND,
        LogType.COMMAND_ERROR,
    ):
        raw_body: str = event.get("body", "{}")

        try:
            body: dict[str, Any] = json.loads(raw_body)

        except json.JSONDecodeError:
            logger.warning("send_log received invalid event body JSON")

            body = {}

        integration_owners: dict[str, Any] = body.get(
            "authorizing_integration_owners", {}
        )
        command_type: list[str] = list(integration_owners.keys())
        is_server_command: bool = "0" in command_type

        guild_id: str | None = body.get("guild_id")
        channel: dict[str, Any] = body.get("channel", {})
        channel_id: str | None = channel.get("id") or body.get("channel_id")
        channel_name: str | None = channel.get("name")

        member: dict[str, Any] = body.get("member", {})
        member_user: dict[str, Any] = member.get("user", {})
        user: dict[str, Any] = body.get("user", {}) or member_user

        member_id: str | None = user.get("id")
        member_name: str | None = user.get("global_name") or user.get("username")
        member_username: str | None = user.get("username")

        guild_name: str | None = None
        if is_server_command and guild_id:
            try:
                # 길드명 조회 실패는 로그 전송 자체를 막지 않도록 무시하고 계속 진행
                guild_name = daa.get_guild_name(guild_id)

            except Exception:
                logger.exception(
                    "failed to resolve guild name for log: " f"guild_id={guild_id}"
                )

        cmd_text: str | None = _command_text(body)
        author_value: str | None = None
        if member_id or member_name or member_username:
            display_name: str | None = member_name or member_username

            if display_name and member_username and member_id:
                author_value = f"{display_name} - {member_username} ({member_id})"

            elif display_name and member_id:
                author_value = f"{display_name} ({member_id})"

            else:
                author_value = str(display_name or member_id)

        common_embed: dict[str, str | None] = {
            "time": now,
            "type": "서버" if is_server_command else "유저",
            "server": (
                f"{guild_name or 'Unknown'} ({guild_id})"
                if is_server_command and guild_id
                else (guild_id or "DM")
            ),
            "channel": (
                f"{channel_name} ({channel_id})"
                if is_server_command and channel_name and channel_id
                else (channel_id or "DM")
            ),
            "author": author_value,
            "cmd": cmd_text,
        }

        if log_type in (LogType.COMMAND, LogType.ADMIN_COMMAND):
            embed_json: dict[str, str | None] = {**common_embed, "msg": msg}

            if log_type == LogType.COMMAND:
                title = "투데이즈 명령어 로그"
                color = 3447003

            else:
                title = "투데이즈 관리자 명령어 로그"
                color = 10181046

            fields = _build_fields(embed_json)

        # LogType.COMMAND_ERROR
        else:
            embed_json = {**common_embed, "error": msg}
            title = "투데이즈 명령어 에러 로그"
            color = 15548997
            fields: list[dict[str, Any]] = _build_fields(embed_json)

    elif log_type == LogType.UPDATE:
        embed_json = {"time": now, "cmd": event["action"]}
        title = "투데이즈 데이터 업데이트 로그"
        color = 3447003
        fields = _build_fields(embed_json)

    elif log_type == LogType.UPDATE_ERROR:
        embed_json = {"time": now, "cmd": event["action"], "error": msg}
        title = "투데이즈 데이터 업데이트 에러 로그"
        color = 15548997
        fields = _build_fields(embed_json)

    elif log_type == LogType.PLAYER_UPDATE:
        embed_json = {"time": now, "cmd": event["action"], "user-type": msg}
        title = "투데이즈 플레이어 등록 / 업데이트 로그"
        color = 3447003
        fields = _build_fields(embed_json)

    # 에러성 로그만 멘션을 붙여 노이즈를 줄임
    content: str = (
        ""
        if log_type in (LogType.COMMAND, LogType.ADMIN_COMMAND, LogType.UPDATE)
        else f"<@{admin_id}>"
    )

    return {
        "content": content,
        "embeds": [{"title": title, "color": color, "fields": fields}],
    }
