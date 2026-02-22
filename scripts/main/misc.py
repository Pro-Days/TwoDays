from __future__ import annotations

import datetime
import os
import platform

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

from typing import TYPE_CHECKING

import data_manager
import mojang
import numpy as np
import requests
from log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)


def convert_path(path: str) -> str:
    """
    운영 체제에 따라 경로를 변환함
    윈도우에서는 백슬래시를 사용하고, 유닉스에서는 슬래시를 사용
    """

    if platform.system() == "Windows":
        system_path: str = path.replace("/", "\\")
    else:
        system_path = path.replace("\\", "/")

    converted: str = os.path.normpath(system_path)

    logger.debug("convert_path: " f"input={path} " f"output={converted}")

    return converted


def get_ip() -> str:
    logger.info("requesting public IP address")

    response: requests.Response = requests.get("https://api64.ipify.org?format=json")

    logger.debug(f"get_ip response_status={response.status_code}")

    data = response.json()

    return data["ip"]


def get_guild_name(guild_id: str) -> str:
    logger.info(f"requesting guild name: guild_id={guild_id}")

    url: str = f"https://discord.com/api/v10/guilds/{guild_id}"

    headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

    response: requests.Response = requests.get(url, headers=headers)

    logger.debug(
        f"get_guild_name response_status={response.status_code} " f"guild_id={guild_id}"
    )

    data = response.json()

    return data["name"]


def get_guild_list() -> list[dict[str, str]]:
    logger.info("requesting guild list")

    url = "https://discord.com/api/v10/users/@me/guilds"

    headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

    response: requests.Response = requests.get(url, headers=headers)

    logger.debug(f"get_guild_list response_status={response.status_code}")

    data = response.json()

    logger.info(
        f"guild list fetched: count={len(data) if isinstance(data, list) else None}"
    )

    return data


def get_profile_from_name(name: str) -> tuple[str | None, str | None]:
    """
    닉네임으로 name, UUID 가져오기
    """

    logger.info(f"get_profile_from_name start: name={name}")

    # 닉네임이 등록되어있다면 데이터베이스에서 uuid 가져오기
    metadata = data_manager.manager.find_user_metadata_by_name(name)

    if metadata:
        logger.info(f"profile lookup source=metadata: name={name}")

        real_name = metadata.get("Name")
        pk = metadata.get("PK")
        uuid = (
            data_manager.manager.uuid_from_user_pk(pk) if isinstance(pk, str) else None
        )

    else:
        # 닉네임이 등록되어있지 않다면
        logger.info(f"profile lookup source=mojang: name={name}")

        api = mojang.API(retry_on_ratelimit=True, ratelimit_sleep_time=1)

        uuid: str | None = api.get_uuid(name)
        real_name: str | None = api.get_username(uuid) if uuid else None

        logger.info(
            "mojang profile lookup result: "
            f"input={name} "
            f"resolved_name={real_name} "
            f"uuid={uuid}"
        )

    if not uuid or not real_name:
        logger.warning("failed to resolve profile: " f"name={name}")

        return None, None

    logger.info(
        "resolved profile: "
        f"input={name} "
        f"resolved_name={real_name} "
        f"uuid={uuid}"
    )

    return real_name, uuid


def get_name_from_uuid(uuid: str) -> str | None:
    """
    UUID로 name 가져오기
    """

    logger.debug("get_name_from_uuid start: " f"uuid={uuid}")

    # UUID가 등록되어있다면 데이터베이스에서 name 가져오기
    metadata = data_manager.manager.get_user_metadata(uuid)

    if metadata:
        logger.debug("name found in metadata cache: " f"uuid={uuid}")

        real_name = metadata.get("Name")

    else:
        # UUID가 등록되어있지 않다면
        logger.debug("name not in metadata cache, querying Mojang API: " f"uuid={uuid}")

        api = mojang.API(retry_on_ratelimit=True, ratelimit_sleep_time=1)

        real_name: str | None = api.get_username(uuid)

    if not real_name:
        logger.warning("failed to resolve name: " f"uuid={uuid}")

        return None

    logger.debug("resolved name: " f"uuid={uuid} " f"name={real_name}")

    return real_name


def get_profile_from_mc(names: list[str]):
    logger.info("get_profile_from_mc start: " f"requested_count={len(names)}")

    api = mojang.API(retry_on_ratelimit=True, ratelimit_sleep_time=1)

    # names를 10개 단위로 나눔
    chunk_size = 10
    chunked_list: list[list[str]] = [
        names[i : i + chunk_size] for i in range(0, len(names), chunk_size)
    ]

    profiles: dict[str, dict[str, str]] = {}

    for chunk in chunked_list:
        try:
            uuids: dict[str, str] = api.get_uuids(chunk)
            logger.debug(
                "mojang bulk profile chunk resolved: "
                f"chunk_size={len(chunk)} "
                f"resolved={len(uuids)}"
            )

        except Exception:
            logger.exception("mojang bulk profile chunk failed: " f"chunk={chunk}")

            continue

        for name, uuid in uuids.items():
            for _name in names:
                if name.lower() == _name.lower():
                    profiles[_name] = {"uuid": uuid, "name": name}

    logger.info("get_profile_from_mc complete: " f"resolved_count={len(profiles)}")

    return profiles


def get_today(days_before=0) -> datetime.date:
    kst_now = (
        datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(hours=9)
        - datetime.timedelta(days=days_before)
    )
    today_kst = kst_now.date()

    logger.debug("get_today: " f"days_before={days_before} " f"result={today_kst}")
    return today_kst


def get_exp_data() -> list[int]:
    data: list[int] = [0] + [int(100 * 1.02**i) for i in range(0, 200)]
    return data


if __name__ == "__main__":
    # print(get_guild_list())
    # print(get_max_id())
    print(get_profile_from_mc(names=["prodays", "prodays2"]))
    # print(get_main_slot("prodays"))
    # print(get_today_from_input("12일전"))
    # print(get_name(id=1))

    pass
