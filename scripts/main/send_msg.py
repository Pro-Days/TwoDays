from __future__ import annotations

import json
import os
import time
from typing import Any

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

from typing import TYPE_CHECKING

import misc
import requests
from log_utils import get_logger, truncate_text

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)
DISCORD_HTTP_TIMEOUT: tuple[float, float] = (3, 10)

LOG_CHANNEL_ID: str | None = os.getenv("DISCORD_LOG_CHANNEL_ID")
ADMIN_ID: str | None = os.getenv("DISCORD_ADMIN_ID")
DISCORD_TOKEN: str | None = os.getenv("DISCORD_TOKEN")
DISCORD_APP_ID: str | None = os.getenv("DISCORD_APP_ID")

if not LOG_CHANNEL_ID or not ADMIN_ID or not DISCORD_TOKEN or not DISCORD_APP_ID:
    logger.error(
        "missing discord env vars: "
        f"LOG_CHANNEL_ID={LOG_CHANNEL_ID} "
        f"ADMIN_ID={ADMIN_ID} "
        f"DISCORD_TOKEN={DISCORD_TOKEN} "
        f"DISCORD_APP_ID={DISCORD_APP_ID}"
    )

    raise ValueError(
        "DISCORD_LOG_CHANNEL_ID, DISCORD_ADMIN_ID, DISCORD_TOKEN, and DISCORD_APP_ID must be set in environment variables."
    )


def _safe_response_body(response: requests.Response) -> Any:
    try:
        return response.json()

    except Exception:
        return truncate_text(response.text, 500)


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


def _message_preview(msg: str) -> str:
    return truncate_text(msg.replace("\n", "\\n"), 300)


def _safe_send_log(
    log_type: int, event: dict, msg: str = "", image: str | None = None
) -> None:
    try:
        send_log(log_type, event, msg, image)

    except Exception:
        logger.exception(
            "send_log failed: "
            f"log_type={log_type} "
            f"image={bool(image)} "
            f"msg_preview={_message_preview(str(msg))}"
        )


def send(
    event: dict,
    msg: str,
    image: str | None = None,
    log_type: int = 1,
    error: str | None = None,
) -> dict:

    logger.info(
        "send start: "
        f"log_type={log_type} "
        f"image={bool(image)} "
        f"msg_preview={_message_preview(str(msg))}"
    )

    body = json.loads(event["body"])
    interaction_token = body.get("token")

    payload = {"content": msg}

    # 이미지가 포함된 경우
    if image:
        with open(image, "rb") as f:
            file_data = f.read()

        url = (
            f"https://discord.com/api/v10/webhooks/{DISCORD_APP_ID}/{interaction_token}"
        )
        multipart_data = {
            "payload_json": (None, json.dumps(payload), "application/json"),
            "file": (image, file_data, "application/octet-stream"),
        }

        response: requests.Response | None = None
        try:
            response = requests.post(
                url,
                files=multipart_data,
                timeout=DISCORD_HTTP_TIMEOUT,
            )
            response_body = _safe_response_body(response)
            response.raise_for_status()

        # 요청 실패한 경우
        except requests.RequestException:
            response_body = (
                _safe_response_body(response) if response is not None else None
            )

            status_code = response.status_code if response is not None else None

            logger.exception(
                "discord message send failed (multipart): "
                f"status={status_code} "
                f"response={truncate_text(response_body, 600)} "
                f"msg_preview={_message_preview(str(msg))}"
            )

            return {
                "statusCode": 502,
                "body": json.dumps(
                    {
                        "message": "디스코드 메시지 전송 실패",
                        "response": response_body,
                        "msg": msg,
                    }
                ),
            }

        logger.info(
            "discord message sent (multipart): "
            f"status={response.status_code} "
            f"response={truncate_text(response_body, 600)} "
            f"msg_preview={_message_preview(str(msg))}"
        )

        _safe_send_log(log_type, event, msg if error is None else error, image)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "메시지 전송 성공", "response": response_body, "msg": msg}
            ),
        }

    # 이미지가 없는 경우

    url: str = (
        f"https://discord.com/api/v10/webhooks/{DISCORD_APP_ID}/{interaction_token}/messages/@original"
    )

    headers: dict[str, str] = {"Content-Type": "application/json"}

    response: requests.Response | None = None
    try:
        response = requests.patch(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=DISCORD_HTTP_TIMEOUT,
        )
        response_body = _safe_response_body(response)
        response.raise_for_status()

    # 요청 실패한 경우
    except requests.RequestException:
        response_body = _safe_response_body(response) if response is not None else None

        status_code = response.status_code if response is not None else None

        logger.exception(
            "discord message send failed (patch): "
            f"status={status_code} "
            f"response={truncate_text(response_body, 600)} "
            f"msg_preview={_message_preview(str(msg))}"
        )

        return {
            "statusCode": 502,
            "body": json.dumps(
                {
                    "message": "디스코드 메시지 전송 실패",
                    "response": response_body,
                    "msg": msg,
                }
            ),
        }

    logger.info(
        "discord message sent (patch): "
        f"status={response.status_code} "
        f"response={truncate_text(response_body, 600)} "
        f"msg_preview={_message_preview(str(msg))}"
    )

    _safe_send_log(log_type, event, msg if error is None else error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "메시지 전송 성공", "response": response_body, "msg": msg}
        ),
    }


def send_log(log_type: int, event: dict, msg="", image=None):
    """
    log_type: 1 - 명령어 로그
    log_type: 2 - 관리자 명령어 로그
    log_type: 3 - 디스코드 에러 로그
    log_type: 4 - 데이터 업데이트 로그
    log_type: 5 - 데이터 업데이트 에러 로그
    log_type: 6 - 플레이어 등록 / 업데이트 로그
    # TODO: enum
    """

    logger.debug(
        "send_log start: "
        f"log_type={log_type} "
        f"image={bool(image)} "
        f"msg_preview={_message_preview(str(msg))}"
    )

    now = f"<t:{int(time.time())}:f>"

    if log_type in [1, 2, 3]:
        raw_body: str = event.get("body", "{}")

        try:
            body: dict = json.loads(raw_body)

        except json.JSONDecodeError:
            logger.warning("send_log received invalid event body JSON")

            body = {}

        integration_owners: dict = body.get("authorizing_integration_owners", {})

        command_type: list = list(integration_owners.keys())

        is_server_command: bool = "0" in command_type

        # 서버 명령어인 경우 guild_id, channel 정보가 있을 수 있지만 유저 명령어인 경우에는 DM이므로 해당 정보가 없을 수 있음
        guild_id: str | None = body.get("guild_id")
        channel: dict = body.get("channel", {})
        channel_id: str | None = channel.get("id") or body.get("channel_id")
        channel_name: str | None = channel.get("name")

        member: dict = body.get("member", {})
        member_user: dict = member.get("user", {})
        user: dict = body.get("user", {}) or member_user

        member_id: str | None = user.get("id")
        member_name: str | None = user.get("global_name") or user.get("username")
        member_username: str | None = user.get("username")

        guild_name: str | None = None

        # 서버 명령어인 경우
        if is_server_command and guild_id:
            try:
                guild_name = misc.get_guild_name(guild_id)

            except Exception:
                logger.exception(
                    "failed to resolve guild name for log: " f"guild_id={guild_id}"
                )

        cmd_text: str | None = _command_text(body)
        author_value: str | None = None

        # member_id, member_name, member_username 중 하나라도 존재하면 author_value 구성
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

        if log_type in [1, 2]:
            embed_json: dict[str, str | None] = {**common_embed, "msg": msg}

            if log_type == 1:
                title = "투데이즈 명령어 로그"
                color = 3447003

            else:
                title = "투데이즈 관리자 명령어 로그"
                color = 10181046

            fields: list[dict[str, Any]] = _build_fields(embed_json)

        else:  # 3
            embed_json: dict[str, str | None] = {**common_embed, "error": msg}

            title = "투데이즈 명령어 에러 로그"
            color = 15548997

            fields: list[dict[str, Any]] = _build_fields(embed_json)

    else:
        if log_type == 4:
            embed_json = {"time": now, "cmd": event["action"]}

            title = "투데이즈 데이터 업데이트 로그"
            color = 3447003

            fields = _build_fields(embed_json)

        elif log_type == 5:
            embed_json = {"time": now, "cmd": event["action"], "error": msg}

            title = "투데이즈 데이터 업데이트 에러 로그"
            color = 15548997

            fields = _build_fields(embed_json)

        elif log_type == 6:
            embed_json = {"time": now, "cmd": event["action"], "user-type": msg}

            title = "투데이즈 플레이어 등록 / 업데이트 로그"
            color = 3447003

            fields = _build_fields(embed_json)

        else:
            logger.warning("send_log ignored unknown " f"log_type={log_type}")

            return

    payload: dict[str, Any] = {
        "content": "" if log_type in [1, 2, 4] else f"<@{ADMIN_ID}>",
        "embeds": [{"title": title, "color": color, "fields": fields}],
    }

    url: str = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"

    headers: dict[str, str] = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
    }

    response: requests.Response = requests.post(
        url,
        headers=headers,
        data=json.dumps(payload),
        timeout=DISCORD_HTTP_TIMEOUT,
    )
    response_body: str = _safe_response_body(response)
    response.raise_for_status()

    logger.info(
        "discord log sent: "
        f"type={log_type} "
        f"status={response.status_code} "
        f"response={truncate_text(response_body, 600)}"
    )

    if image:
        with open(image, "rb") as f:
            file_data: bytes = f.read()

        payload: dict[str, Any] = {"content": ""}
        headers: dict[str, str] = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        multipart_data: dict[str, tuple[None | str, str | bytes, str]] = {
            "payload_json": (None, json.dumps(payload), "application/json"),
            "file": (image, file_data, "application/octet-stream"),
        }

        response: requests.Response = requests.post(
            url,
            headers=headers,
            files=multipart_data,
            timeout=DISCORD_HTTP_TIMEOUT,
        )
        response_body: str = _safe_response_body(response)
        response.raise_for_status()

        logger.info(
            "discord log image sent: "
            f"type={log_type} "
            f"status={response.status_code} "
            f"response={truncate_text(response_body, 600)} "
            f"image={image}"
        )
