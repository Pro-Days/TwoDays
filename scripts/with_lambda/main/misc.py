import os
import datetime
import requests
import platform
import numpy as np
import mojang

from typing import Optional, Literal

import data_manager


def convert_path(path: str) -> str:
    """
    운영 체제에 따라 경로를 변환함.
    윈도우에서는 백슬래시를 사용하고, 유닉스에서는 슬래시를 사용.
    """
    if platform.system() == "Windows":
        system_path = path.replace("/", "\\")
    else:
        system_path = path.replace("\\", "/")

    return os.path.normpath(system_path)


def get_ip() -> str:
    response = requests.get("https://api64.ipify.org?format=json")

    data = response.json()

    return data["ip"]


def get_guild_name(guild_id: str) -> str:
    url = f"https://discord.com/api/v10/guilds/{guild_id}"

    headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data["name"]


def get_guild_list() -> list[dict[str, str]]:
    url = "https://discord.com/api/v10/users/@me/guilds"

    headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data


def get_name(
    name: str = "", id: int = 0
) -> Optional[str]:  # get_profile으로 대체 Class Profile
    if name:
        data = data_manager.read_data(
            "Users", "lower_name-index", {"lower_name": name.lower()}
        )

    elif id:
        data = data_manager.read_data("Users", condition_dict={"id": id})

    else:
        return None

    return data[0]["name"] if data else None


def get_uuid(name: str) -> Optional[str]:
    data = data_manager.read_data(
        "Users", "lower_name-index", {"lower_name": name.lower()}
    )

    return data[0]["uuid"] if data else None


def get_profile_from_mc(
    name: str = "", uuid: str = "", names: Optional[list[str]] = None
) -> Optional[dict[str, dict[str, str]]]:
    api = mojang.API(retry_on_ratelimit=True, ratelimit_sleep_time=1)

    if name:
        try:
            _uuid = api.get_uuid(name)
        except:
            return None

        if not _uuid:
            return None

        try:
            _name = api.get_username(_uuid)
        except:
            return None

        if not _name:
            return None

        return {name: {"uuid": _uuid, "name": _name}}

        # response = requests.get(
        #     f"https://api.minecraftservices.com/minecraft/profile/lookup/name/{name}"
        # )
        # if not "name" in response:
        #     response = requests.get(
        #         f"https://api.mojang.com/users/profiles/minecraft/{name}"
        #     )

    elif uuid:
        try:
            _name = api.get_username(uuid)
        except:
            return None

        if not _name:
            return None

        try:
            _uuid = api.get_uuid(_name)
        except:
            return None

        if not _uuid:
            return None

        return {_uuid: {"uuid": _uuid, "name": _name}}

        # response = requests.get(
        #     f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}"
        # )
        # if not "name" in response:
        #     response = requests.get(f"https://api.mojang.com/user/profile/{uuid}")

    elif names:
        # names를 10개 단위로 나눔
        chunk_size = 10
        chunked_list = [
            names[i : i + chunk_size] for i in range(0, len(names), chunk_size)
        ]

        profiles: dict[str, dict[str, str]] = {}

        for chunk in chunked_list:
            try:
                uuids = api.get_uuids(chunk)
            except:
                continue

            for _name, _uuid in uuids.items():
                for __name in names:
                    if _name.lower() == __name.lower():
                        profiles[__name] = {"uuid": _uuid, "name": _name}

            # response = requests.post(
            #     "https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname",
            #     json=chunk,
            # )

            # data = response.json()

            # if len(data) != len(chunk):
            #     data.extend([{}] * (len(chunk) - len(data)))

            # profiles.extend(data)

        return profiles

    # return response.json() if response.status_code == 200 else None


def get_id(name: str = "", uuid: str = "") -> Optional[int]:
    if name:
        data = data_manager.read_data(
            "Users", "lower_name-index", {"lower_name": name.lower()}
        )

    elif uuid:
        data = data_manager.read_data("Users", "uuid-index", {"uuid": uuid})

    else:
        return None

    return int(data[0]["id"]) if data else None


def get_max_id() -> int:  # id -> uuid로 변경
    data = data_manager.scan_data("Users", key="id")

    if not data:
        return 0

    max_id = max([int(item["id"]) for item in data])

    return max_id


def get_main_slot(name: str) -> Optional[int]:
    data = data_manager.read_data(
        "Users", "lower_name-index", {"lower_name": name.lower()}
    )
    return int(data[0]["mainSlot"]) if data else None


def convert_job(job: int | str) -> Optional[str]:
    job_dict = {
        "0": "검호",
        "1": "매화",
        "2": "살수",
        "3": "도제",
        "4": "술사",
        "5": "도사",
        "6": "빙궁",
        "7": "귀궁",
        "검호": 0,
        "매화": 1,
        "살수": 2,
        "도제": 3,
        "술사": 4,
        "도사": 5,
        "빙궁": 6,
        "귀궁": 7,
    }

    return job_dict[str(job)]


def get_today(days_before=0) -> datetime.date:
    kst_now = (
        datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(hours=9)
        - datetime.timedelta(days=days_before)
    )
    today_kst = kst_now.date()

    return today_kst


def get_today_from_input(day: Optional[str]) -> datetime.date | Literal[-1, -2]:
    """
    -1: 날짜 입력이 올바르지 않음
    -2: 미래 날짜
    today: datetime.date
    """
    # YYYY-MM-DD, MM-DD, DD, -1, ...
    try:
        todayR = get_today()

        if day:
            if day[0] == "-" and day[1:].isdigit():
                date = int(day[1:])
                today = todayR - datetime.timedelta(days=date)

            else:
                date_type = day.count("-")
                today_list = str(todayR).split("-")

                if date_type == 0:  # 날짜만
                    day = "-".join(today_list[:2]) + "-" + day

                if date_type == 1:
                    day = today_list[0] + "-" + day

                today = datetime.datetime.strptime(day, "%Y-%m-%d").date()

        else:
            today = todayR

    except:
        return -1

    if today > todayR:
        return -2

    return today


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


def get_exp_data():
    data = [0] + [int(100 * 1.02**i) for i in range(0, 300)]
    return data


if __name__ == "__main__":
    # print(get_guild_list())
    # print(get_max_id())
    print(get_profile_from_mc(names=["prodays", "prodays2"]))
    # print(get_main_slot("prodays"))
    # print(get_today_from_input("12일전"))
    # print(get_name(id=1))

    pass
