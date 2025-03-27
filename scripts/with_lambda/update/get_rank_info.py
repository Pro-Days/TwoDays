import time
import random
import datetime
import requests
from decimal import Decimal

import misc
import data_manager


def get_current_rank_data(page=0) -> dict:
    """
    현재 전체 캐릭터 랭킹 데이터 반환
    {"name": "ProDays", "job": "검호", "level": "100"}
    """

    data = [
        {"level": "200.0", "job": "검호", "name": "ProDays"},
        {"level": "199.0", "job": "검호", "name": "Aventurine_0"},
        {"level": "198.0", "job": "매화", "name": "heekp"},
        {"level": "197.0", "job": "매화", "name": "krosh0127"},
        {"level": "196.0", "job": "살수", "name": "_IIN"},
        {"level": "195.0", "job": "살수", "name": "YOUKONG"},
        {"level": "194.0", "job": "검호", "name": "ino2423"},
        {"level": "193.0", "job": "매화", "name": "Route88"},
        {"level": "192.0", "job": "검호", "name": "ljinsoo"},
        {"level": "191.0", "job": "살수", "name": "ggameee"},
        {"level": "190.0", "job": "살수", "name": "Lemong_0"},
        {"level": "189.0", "job": "매화", "name": "1yeons"},
        {"level": "188.0", "job": "도제", "name": "sungchanmom"},
        {"level": "187.0", "job": "술사", "name": "tmdwns0818"},
        {"level": "186.0", "job": "도사", "name": "poro_rany"},
        {"level": "185.0", "job": "도제", "name": "Master_Rakan_"},
        {"level": "184.0", "job": "도제", "name": "Protect_Choco"},
        {"level": "183.0", "job": "빙궁", "name": "LGJ20000"},
        {"level": "182.0", "job": "도사", "name": "1mkr"},
        {"level": "181.0", "job": "귀궁", "name": "Kozi0518"},
        {"level": "180.0", "job": "술사", "name": "roadhyeon03"},
        {"level": "179.0", "job": "술사", "name": "aaqq2005y"},
        {"level": "178.0", "job": "술사", "name": "spemdnjs"},
        {"level": "177.0", "job": "도제", "name": "Moncler02"},
        {"level": "176.0", "job": "도사", "name": "Welcome_Pasta"},
        {"level": "175.0", "job": "도사", "name": "world_3034"},
        {"level": "174.0", "job": "빙궁", "name": "ArtBeat"},
        {"level": "173.0", "job": "빙궁", "name": "TinySlayers"},
        {"level": "172.0", "job": "귀궁", "name": "neoreow"},
        {"level": "171.0", "job": "빙궁", "name": "d_capo"},
    ]

    today = misc.get_today()
    base_date = datetime.date(2025, 2, 1)

    delta_days = (today - base_date).days

    random.seed(delta_days)

    for d in data:
        d["level"] = str(Decimal(d["level"]) + random.random() * 0.5)

        # uuid = data_manager.read_data("TA_DEV-Users", "lower_name-index", {"lower_name": d["name"].lower()})[
        #     0
        # ]["uuid"]

        # response = requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}").json()
        # while "name" not in response:
        #     response = requests.get(f"https://api.mojang.com/user/profile/{uuid}").json()
        #     if "name" in response:
        #         break
        #     time.sleep(0.1)

        #     response = requests.get(
        #         f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}"
        #     ).json()
        #     time.sleep(0.1)

        # d["name"] = response["name"]

    data = sorted(data, key=lambda x: Decimal(x["level"]), reverse=True)

    return data[page * 10 - 9 : page * 10 + 1] if page != 0 else data


if __name__ == "__main__":
    # print(get_current_rank_data(10))
    pass
