from __future__ import annotations

import os
from typing import TYPE_CHECKING

import requests

from scripts.main.shared.utils.log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)

HTTP_TIMEOUT: tuple[int, int] = (3, 10)


def get_ip() -> str:
    # 관리자 진단용 기능이라 별도 모듈로 분리해 명령 핸들러를 단순화
    logger.info("requesting public IP address")

    response: requests.Response = requests.get(
        "https://api64.ipify.org?format=json",
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()

    logger.debug(f"get_ip response_status={response.status_code}")

    data = response.json()

    return data["ip"]


def get_guild_name(guild_id: str) -> str:
    # 로그 포맷터에서 길드명 해석만 필요하므로 읽기 전용 API만 제공
    logger.info(f"requesting guild name: guild_id={guild_id}")

    url: str = f"https://discord.com/api/v10/guilds/{guild_id}"
    headers: dict[str, str] = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

    response: requests.Response = requests.get(
        url,
        headers=headers,
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()

    logger.debug(
        f"get_guild_name response_status={response.status_code} " f"guild_id={guild_id}"
    )

    data: dict[str, str] = response.json()

    return data["name"]


def get_guild_list() -> list[dict[str, str]]:
    # 관리자 명령에서만 쓰는 호출이라 일반 도메인 로직과 분리
    logger.info("requesting guild list")

    url: str = "https://discord.com/api/v10/users/@me/guilds"
    headers: dict[str, str] = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

    response: requests.Response = requests.get(
        url,
        headers=headers,
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()

    logger.debug(f"get_guild_list response_status={response.status_code}")

    data: list[dict[str, str]] = response.json()

    logger.info(
        f"guild list fetched: count={len(data) if isinstance(data, list) else None}"
    )

    return data
