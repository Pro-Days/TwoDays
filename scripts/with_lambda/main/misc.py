import os
import datetime
import requests
import platform
import numpy as np

import data_manager


def convert_path(path):
    """
    운영 체제에 따라 경로를 변환함.
    윈도우에서는 백슬래시를 사용하고, 유닉스에서는 슬래시를 사용.
    """
    if platform.system() == "Windows":
        system_path = path.replace("/", "\\")
    else:
        system_path = path.replace("\\", "/")

    return os.path.normpath(system_path)


def get_ip():
    response = requests.get("https://api64.ipify.org?format=json")

    data = response.json()

    return data["ip"]


def get_guild_name(guild_id):
    url = f"https://discord.com/api/v10/guilds/{guild_id}"

    headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data["name"]


def get_guild_list():
    url = "https://discord.com/api/v10/users/@me/guilds"

    headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data


def get_name(name="", id=""):
    if name:
        data = data_manager.read_data("Users", "lower_name-index", {"lower_name": name.lower()})
    elif id:
        data = data_manager.read_data("Users", condition_dict={"id": id})

    return data[0]["name"] if data else None


def get_uuid(name=""):
    data = data_manager.read_data("Users", "lower_name-index", {"lower_name": name.lower()})

    return data[0]["uuid"] if data else None


def get_profile_from_mc(name="", uuid="", names=None):
    if name:
        response = requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/name/{name}")
        if not "name" in response:
            response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}")

    elif uuid:
        response = requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}")
        if not "name" in response:
            response = requests.get(f"https://api.mojang.com/user/profile/{uuid}")

    elif names:
        # names를 10개 단위로 나눔
        chunk_size = 10
        chunked_list = [names[i : i + chunk_size] for i in range(0, len(names), chunk_size)]

        profiles = []

        for chunk in chunked_list:
            response = requests.post(
                "https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname", json=chunk
            )

            data = response.json()

            if len(data) != len(chunk):
                data.extend([{}] * (len(chunk) - len(data)))

            profiles.extend(data)

        return profiles

    return response.json() if response.status_code == 200 else None


def get_id(name="", uuid=""):
    if name:
        data = data_manager.read_data("Users", "lower_name-index", {"lower_name": name.lower()})
    elif uuid:
        data = data_manager.read_data("Users", "uuid-index", {"uuid": uuid})

    return int(data[0]["id"]) if data else None


def get_max_id():
    data = data_manager.scan_data("Users", key="id")

    max_id = max([int(item["id"]) for item in data])

    return max_id


def get_main_slot(name):
    data = data_manager.read_data("Users", "lower_name-index", {"lower_name": name.lower()})
    return int(data[0]["mainSlot"])


def convert_job(job):
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


def get_today():
    kst_now = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=9)
    today_kst = kst_now.date()

    return today_kst


def get_today_from_input(today):
    """
    -1: 날짜 입력이 올바르지 않음
    -2: 미래 날짜
    today: datetime.date
    """
    # YYYY-MM-DD, MM-DD, DD, 1일전, ...
    try:
        todayR = get_today()

        if today:
            if (idx := today.find("일전")) != -1:
                date = int(today[:idx])
                today = todayR - datetime.timedelta(days=date)

            else:
                date_type = today.count("-")
                today_list = str(todayR).split("-")

                if date_type == 0:  # 날짜만
                    today = "-".join(today_list[:2]) + "-" + today

                if date_type == 1:
                    today = today_list[0] + "-" + today

                today = datetime.datetime.strptime(today, "%Y-%m-%d").date()

        else:
            today = todayR

    except:
        return -1

    if today > todayR:
        return -2

    return today


def pchip_slopes(x, y):
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


def pchip_interpolate(x, y, x_new):
    """
    x, y 데이터를 PCHIP 방식으로 보간하여,
    새로 주어진 x_new에서의 보간값을 반환합니다.
    """
    # 길이 확인
    if len(x) != len(y):
        raise ValueError("x와 y의 길이가 달라요!")
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
    data = [0] + [int(100 * 1.03**i) for i in range(0, 500)]
    return data


if __name__ == "__main__":
    # print(get_guild_list())
    # print(get_max_id())
    # print(get_profile_from_mc(name="aasdwdddddwdwdwd"))
    # print(get_main_slot("prodays"))
    # print(get_today_from_input("12일전"))
    print(get_name(id=1))

    pass
