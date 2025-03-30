import requests
import datetime

import data_manager
import lambda_function


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


def get_name(name="", id=""):
    if name:
        data = data_manager.read_data("Users", "lower_name-index", {"lower_name": name.lower()})
    elif id:
        data = data_manager.read_data("Users", condition_dict={"id": id})

    return data[0]["name"] if data else None


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


def get_today(days_before=0):
    kst_now = (
        datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(hours=9)
        - datetime.timedelta(days=days_before)
    )
    today_kst = kst_now.date()

    return today_kst


if __name__ == "__main__":
    # print(get_guild_list())
    # print(get_max_id())
    # print(get_profile_from_mc(name="aasdwdddddwdwdwd"))
    # print(get_main_slot("prodays"))
    # print(get_today())

    for i in range(87, -1, -1):
        print(i, lambda_function.lambda_handler({"action": "update_1D", "days_before": i}, None))
    # print(lambda_function.lambda_handler({"action": "update_1D", "days_before": 83}, None))

    pass
