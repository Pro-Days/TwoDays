import random
import datetime

import misc


def get_current_character_data(name):
    data = [
        {"job": "검호", "level": "200.0"},
        {"job": "검호", "level": "200.0"},
        {"job": "검호", "level": "200.0"},
        {"job": "검호", "level": "200.0"},
        {"job": "검호", "level": "200.0"},
    ]

    today = misc.get_today()
    base_date = datetime.date(2025, 2, 1)

    delta_days = (today - base_date).days

    random.seed(delta_days + sum(ord(c) for c in name))

    for d in data:
        d["level"] = str(float(d["level"]) + random.random() * 0.5)

    return data


if __name__ == "__main__":
    # print(get_current_character_data("ProDays"))
    pass
