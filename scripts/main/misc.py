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


def pchip_slopes(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    (x, y)가 주어졌을 때, 각 x[i]에서의 접선 기울기 m[i]를
    Fritsch-Carlson 방법에 따라 계산하여 반환합니다.
    """
    n = len(x)
    m = np.zeros(n)

    # 1) h, delta 계산
    h = np.diff(x)  # 길이 n-1
    delta = np.diff(y) / h  # 길이 n-1

    # 내부 점(1 ~ n-2)에 대한 기울기 계산
    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] > 0:  # 부호가 같을 때만 보정
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])
        else:
            # 만약 delta[i-1]과 delta[i] 부호가 다르거나
            # 하나라도 0이면 모노토닉 유지 위해 기울기 0
            m[i] = 0.0

    # 양 끝점 기울기 (여기서는 간단히 1차 근사로 계산)
    m[0] = delta[0]
    m[-1] = delta[-1]

    return m


def pchip_interpolate(x: np.ndarray, y: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    """
    x, y 데이터를 PCHIP 방식으로 보간하여,
    새로 주어진 x_new에서의 보간값을 반환합니다.
    """
    # y를 float으로 변환
    y = np.array(y, dtype=float)

    # 길이 확인
    if len(x) != len(y):
        raise ValueError("x와 y의 길이가 다름!")
    if np.any(np.diff(x) <= 0):
        raise ValueError("x는 오름차순으로 정렬되어 있어야 합니다.")

    # 각 점에서의 기울기 계산
    m = pchip_slopes(x, y)

    # 보간결과를 담을 배열
    y_new = np.zeros_like(x_new, dtype=float)

    # 구간별로 x_new를 찾아가며 보간
    # 각 x_new[i]에 대해 어느 구간에 속하는지를 찾아서
    # 해당 구간의 3차 Hermite 다항식을 이용해 계산
    for i, xn in enumerate(x_new):
        # xn이 어느 구간에 속하는지 찾기
        if xn <= x[0]:
            # 범위 밖이면, 여기서는 그냥 가장 왼쪽 값으로 extrapolation
            y_new[i] = y[0]
            continue
        elif xn >= x[-1]:
            # 범위 밖이면, 여기서는 가장 오른쪽 값으로 extrapolation
            y_new[i] = y[-1]
            continue
        else:
            idx = np.searchsorted(x, xn) - 1

            x0, x1 = x[idx], x[idx + 1]
            y0, y1 = y[idx], y[idx + 1]
            m0, m1 = m[idx], m[idx + 1]
            h = x1 - x0
            t = (xn - x0) / h

            a = y0
            b = m0
            c = (3 * (y1 - y0) / h - 2 * m0 - m1) / h
            d = (m0 + m1 - 2 * (y1 - y0) / h) / (h**2)

            val = a + b * (t * h) + c * (t * h) ** 2 + d * (t * h) ** 3

            y_new[i] = val

    return y_new


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
