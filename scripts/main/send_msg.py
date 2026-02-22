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

LOG_CHANNEL_ID: str | None = os.getenv("DISCORD_LOG_CHANNEL_ID")
ADMIN_ID: str | None = os.getenv("DISCORD_ADMIN_ID")
DISCORD_TOKEN: str | None = os.getenv("DISCORD_TOKEN")
DISCORD_APP_ID: str | None = os.getenv("DISCORD_APP_ID")

if not LOG_CHANNEL_ID or not ADMIN_ID or not DISCORD_TOKEN:
    logger.error(
        "missing discord env vars: "
        f"LOG_CHANNEL_ID={LOG_CHANNEL_ID} "
        f"ADMIN_ID={ADMIN_ID} "
        f"DISCORD_TOKEN={DISCORD_TOKEN}"
    )

    raise ValueError(
        "DISCORD_LOG_CHANNEL_ID, DISCORD_ADMIN_ID, and DISCORD_TOKEN must be set in environment variables."
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


def send(event, msg, image=None, log_type=1, error=None):
    logger.info(
        "send start: "
        f"log_type={log_type} "
        f"image={bool(image)} "
        f"msg_preview={_message_preview(str(msg))}"
    )

    body = json.loads(event["body"])
    interaction_token = body.get("token")

    payload = {"content": msg}

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

        response = requests.post(url, files=multipart_data)
        response_body = _safe_response_body(response)

        logger.info(
            "discord message sent (multipart): "
            f"status={response.status_code} "
            f"response={truncate_text(response_body, 600)} "
            f"msg_preview={_message_preview(str(msg))}"
        )

        send_log(log_type, event, msg if error is None else error, image)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "메시지 전송 성공", "response": response_body, "msg": msg}
            ),
        }

    url = f"https://discord.com/api/v10/webhooks/{DISCORD_APP_ID}/{interaction_token}/messages/@original"
    headers = {"Content-Type": "application/json"}
    response = requests.patch(url, headers=headers, data=json.dumps(payload))
    response_body = _safe_response_body(response)

    logger.info(
        "discord message sent (patch): "
        f"status={response.status_code} "
        f"response={truncate_text(response_body, 600)} "
        f"msg_preview={_message_preview(str(msg))}"
    )

    send_log(log_type, event, msg if error is None else error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "메시지 전송 성공", "response": response_body, "msg": msg}
        ),
    }


def send_log(log_type, event, msg="", image=None):
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
        body = json.loads(event["body"])
        command_type = body["authorizing_integration_owners"].keys()  # 0: 서버, 1: 유저

        guild_id = body["guild_id"]
        channel_id = body["channel"]["id"]
        member_id = body["member"]["user"]["id"]
        member_name = body["member"]["user"]["global_name"]
        member_username = body["member"]["user"]["username"]

        guild_name = misc.get_guild_name(guild_id)
        channel_name = body["channel"]["name"]
        cmd_text = _command_text(body)
        is_server_command = "0" in command_type

        common_embed = {
            "time": now,
            "type": "서버" if is_server_command else "유저",
            "server": (
                f"{guild_name} ({guild_id})" if is_server_command else f"{guild_id}"
            ),
            "channel": (
                f"{channel_name} ({channel_id})"
                if is_server_command
                else f"{channel_id}"
            ),
            "author": f"{member_name} - {member_username} ({member_id})",
            "cmd": cmd_text,
        }

        if log_type in [1, 2]:
            embed_json = {**common_embed, "msg": msg}

            if log_type == 1:
                title = "투데이즈 명령어 로그"
                color = 3447003
            else:
                title = "투데이즈 관리자 명령어 로그"
                color = 10181046

            fields = _build_fields(embed_json)

        else:  # 3
            embed_json = {**common_embed, "error": msg}
            title = "투데이즈 명령어 에러 로그"
            color = 15548997
            fields = _build_fields(embed_json)

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

    payload = {
        "content": "" if log_type in [1, 2, 4] else f"<@{ADMIN_ID}>",
        "embeds": [{"title": title, "color": color, "fields": fields}],
    }

    url = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response_body = _safe_response_body(response)

    logger.info(
        "discord log sent: "
        f"type={log_type} "
        f"status={response.status_code} "
        f"response={truncate_text(response_body, 600)}"
    )

    if image:
        with open(image, "rb") as f:
            file_data = f.read()

        payload = {"content": ""}
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        multipart_data = {
            "payload_json": (None, json.dumps(payload), "application/json"),
            "file": (image, file_data, "application/octet-stream"),
        }

        response = requests.post(url, headers=headers, files=multipart_data)
        response_body = _safe_response_body(response)

        logger.info(
            "discord log image sent: "
            f"type={log_type} "
            f"status={response.status_code} "
            f"response={truncate_text(response_body, 600)} "
            f"image={image}"
        )
