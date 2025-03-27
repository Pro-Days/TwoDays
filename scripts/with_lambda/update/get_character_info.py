import random
import datetime
from decimal import Decimal

import misc


def get_current_character_data(name):
    data = [
        {"job": "검호", "level": "345.0"},
        {"job": "검호", "level": "345.0"},
        {"job": "검호", "level": "345.0"},
        {"job": "검호", "level": "345.0"},
        {"job": "검호", "level": "345.0"},
    ]

    today = misc.get_today()
    base_date = datetime.date(2025, 2, 1)

    delta_days = (today - base_date).days

    for i, d in enumerate(data):
        random.seed(sum(ord(c) for c in name) + i)

        d["level"] = Decimal(d["level"])
        l = d["level"]

        for _ in range(delta_days):
            d["level"] += Decimal(random.randint(0, 1000 - int(l))) / 1000

    return data


if __name__ == "__main__":
    # print(get_current_character_data("ProDays"))
    pass
