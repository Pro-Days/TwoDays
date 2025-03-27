import random
import datetime
from decimal import Decimal

import misc


def get_current_rank_data(page=0) -> dict:
    """
    현재 전체 캐릭터 랭킹 데이터 반환
    {"name": "ProDays", "job": "검호", "level": "100"}
    """

    data = [
        {"level": "345.0", "job": "검호", "name": "ProDays"},
        {"level": "345.0", "job": "검호", "name": "Aventurine_0"},
        {"level": "345.0", "job": "매화", "name": "heekp"},
        {"level": "345.0", "job": "매화", "name": "krosh0127"},
        {"level": "345.0", "job": "살수", "name": "_IIN"},
        {"level": "345.0", "job": "살수", "name": "YOUKONG"},
        {"level": "345.0", "job": "검호", "name": "ino2423"},
        {"level": "345.0", "job": "매화", "name": "Route88"},
        {"level": "345.0", "job": "검호", "name": "ljinsoo"},
        {"level": "345.0", "job": "살수", "name": "ggameee"},
        {"level": "345.0", "job": "살수", "name": "Lemong_0"},
        {"level": "345.0", "job": "매화", "name": "1yeons"},
        {"level": "345.0", "job": "도제", "name": "sungchanmom"},
        {"level": "345.0", "job": "술사", "name": "tmdwns0818"},
        {"level": "345.0", "job": "도사", "name": "poro_rany"},
        {"level": "345.0", "job": "도제", "name": "Master_Rakan_"},
        {"level": "345.0", "job": "도제", "name": "Protect_Choco"},
        {"level": "345.0", "job": "빙궁", "name": "LGJ20000"},
        {"level": "345.0", "job": "도사", "name": "1mkr"},
        {"level": "345.0", "job": "귀궁", "name": "Kozi0518"},
        {"level": "345.0", "job": "술사", "name": "roadhyeon03"},
        {"level": "345.0", "job": "술사", "name": "aaqq2005y"},
        {"level": "345.0", "job": "술사", "name": "spemdnjs"},
        {"level": "345.0", "job": "도제", "name": "Moncler02"},
        {"level": "345.0", "job": "도사", "name": "Welcome_Pasta"},
        {"level": "345.0", "job": "도사", "name": "world_3034"},
        {"level": "345.0", "job": "빙궁", "name": "ArtBeat"},
        {"level": "345.0", "job": "빙궁", "name": "TinySlayers"},
        {"level": "345.0", "job": "귀궁", "name": "neoreow"},
        {"level": "345.0", "job": "빙궁", "name": "d_capo"},
    ]

    today = misc.get_today()
    base_date = datetime.date(2025, 2, 1)

    delta_days = (today - base_date).days

    for d in data:
        random.seed(sum(ord(c) for c in d["name"]))

        d["level"] = Decimal(d["level"])
        l = d["level"]

        for _ in range(delta_days):
            d["level"] += Decimal(random.randint(0, 1000 - int(l))) / 1000

    data = sorted(data, key=lambda x: x["level"], reverse=True)

    return data[page * 10 - 10 : page * 10] if page != 0 else data


if __name__ == "__main__":
    # print(get_current_rank_data(10))
    pass
