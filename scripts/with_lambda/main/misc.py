import os
import datetime
import requests
import platform

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
        data = data_manager.read_data("TA_DEV-Users", "lower_name-index", {"lower_name": name.lower()})
    elif id:
        data = data_manager.read_data("TA_DEV-Users", None, {"id": id})

    return data[0]["name"] if data else None


def get_uuid(name=""):
    data = data_manager.read_data("TA_DEV-Users", "lower_name-index", {"lower_name": name.lower()})

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
        data = data_manager.read_data("TA_DEV-Users", "lower_name-index", {"lower_name": name.lower()})
    elif uuid:
        data = data_manager.read_data("TA_DEV-Users", "uuid-index", {"uuid": uuid})

    return int(data[0]["id"]) if data else None


def get_max_id():
    data = data_manager.scan_data("TA_DEV-Users", key="id")

    max_id = max([int(item["id"]) for item in data])

    return max_id


def get_main_slot(name):
    data = data_manager.read_data("TA_DEV-Users", "lower_name-index", {"lower_name": name.lower()})
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


if __name__ == "__main__":
    # print(get_guild_list())
    # print(get_max_id())
    # print(get_profile_from_mc(name="aasdwdddddwdwdwd"))
    # print(get_main_slot("prodays"))
    print(get_today_from_input("12일전"))

    pass
