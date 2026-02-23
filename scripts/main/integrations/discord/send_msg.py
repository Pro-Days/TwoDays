from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

import requests

from scripts.main.integrations.discord.discord_client import (
    DISCORD_HTTP_TIMEOUT,
    DiscordHttpResult,
    patch_json,
    post_json,
    post_multipart,
)
from scripts.main.integrations.discord.discord_log_formatter import (
    LogType,
    build_log_payload,
)
from scripts.main.shared.utils.log_utils import get_logger, truncate_text

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)

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


def _message_preview(msg: str) -> str:
    return truncate_text(msg.replace("\n", "\\n"), 300)


def _safe_send_log(
    log_type: LogType,
    event: dict,
    msg: str = "",
    image: str | None = None,
) -> None:
    # 본문 응답 성공 이후 로그 전송 실패가 사용자 응답을 깨지 않도록 분리
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
    log_type: LogType = LogType.COMMAND,
    error: str | None = None,
) -> dict:
    logger.info(
        "send start: "
        f"log_type={log_type} "
        f"image={bool(image)} "
        f"msg_preview={_message_preview(str(msg))}"
    )

    body: dict[str, Any] = json.loads(event["body"])
    interaction_token: str | None = body.get("token")
    payload: dict[str, str] = {"content": msg}

    # Discord 인터랙션 응답은 파일 포함 여부에 따라 endpoint/전송 방식이 달라짐
    if image:
        with open(image, "rb") as file_obj:
            file_data: bytes = file_obj.read()

        url: str = (
            f"https://discord.com/api/v10/webhooks/{DISCORD_APP_ID}/{interaction_token}"
        )
        multipart_data: dict[str, tuple] = {
            "payload_json": (None, json.dumps(payload), "application/json"),
            "file": (image, file_data, "application/octet-stream"),
        }

        # 실패 시에도 상태/응답 본문을 로깅하려고 result를 바깥에 유지
        result: DiscordHttpResult | None = None
        try:
            result = post_multipart(
                url,
                multipart_data=multipart_data,
                timeout=DISCORD_HTTP_TIMEOUT,
            )
            result.response.raise_for_status()

        except requests.RequestException:
            response_body: Any | None = result.body if result is not None else None
            status_code: int | None = (
                result.response.status_code if result is not None else None
            )

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
            f"status={result.response.status_code} "
            f"response={truncate_text(result.body, 600)} "
            f"msg_preview={_message_preview(str(msg))}"
        )

        _safe_send_log(log_type, event, msg if error is None else error, image)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "메시지 전송 성공", "response": result.body, "msg": msg}
            ),
        }

    # 이미지가 없으면 원본 메시지 패치 경로를 사용
    url = f"https://discord.com/api/v10/webhooks/{DISCORD_APP_ID}/{interaction_token}/messages/@original"
    headers: dict[str, str] = {"Content-Type": "application/json"}

    result = None
    try:
        result = patch_json(
            url,
            headers=headers,
            payload=payload,
            timeout=DISCORD_HTTP_TIMEOUT,
        )
        result.response.raise_for_status()

    except requests.RequestException:
        response_body = result.body if result is not None else None
        status_code = result.response.status_code if result is not None else None

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
        f"status={result.response.status_code} "
        f"response={truncate_text(result.body, 600)} "
        f"msg_preview={_message_preview(str(msg))}"
    )

    _safe_send_log(log_type, event, msg if error is None else error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "메시지 전송 성공", "response": result.body, "msg": msg}
        ),
    }


def send_log(
    log_type: LogType,
    event: dict,
    msg: str = "",
    image: str | None = None,
) -> None:

    logger.debug(
        "send_log start: "
        f"log_type={log_type} "
        f"image={bool(image)} "
        f"msg_preview={_message_preview(str(msg))}"
    )

    # payload 조립 로직을 분리해 send_msg는 전송 흐름만 담당
    payload: dict[str, Any] | None = build_log_payload(
        log_type,
        event,
        str(msg),
        admin_id=str(ADMIN_ID),
    )

    if payload is None:
        return

    url: str = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"
    headers: dict[str, str] = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
    }

    result: DiscordHttpResult = post_json(
        url,
        headers=headers,
        payload=payload,
        timeout=DISCORD_HTTP_TIMEOUT,
    )
    result.response.raise_for_status()

    logger.info(
        "discord log sent: "
        f"type={log_type} "
        f"status={result.response.status_code} "
        f"response={truncate_text(result.body, 600)}"
    )

    if image:
        with open(image, "rb") as file_obj:
            file_data: bytes = file_obj.read()

        # 로그 본문과 이미지를 분리 전송해 Discord embed/file 처리 실패를 분리함
        image_payload: dict[str, Any] = {"content": ""}
        image_headers: dict[str, str] = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        multipart_data: dict[str, tuple[None | str, str | bytes, str]] = {
            "payload_json": (None, json.dumps(image_payload), "application/json"),
            "file": (image, file_data, "application/octet-stream"),
        }

        image_result: DiscordHttpResult = post_multipart(
            url,
            headers=image_headers,
            multipart_data=multipart_data,
            timeout=DISCORD_HTTP_TIMEOUT,
        )
        image_result.response.raise_for_status()

        logger.info(
            "discord log image sent: "
            f"type={log_type} "
            f"status={image_result.response.status_code} "
            f"response={truncate_text(image_result.body, 600)} "
            f"image={image}"
        )
