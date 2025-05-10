import random
import datetime
from decimal import Decimal

import misc


def get_current_character_data(event, name):
    days_before = event.get("days_before", 0)

    data = [
        {"job": "검호", "level": "1.0"},
        {"job": "검호", "level": "1.0"},
        {"job": "검호", "level": "1.0"},
        {"job": "검호", "level": "1.0"},
        {"job": "검호", "level": "1.0"},
    ]

    today = misc.get_today(days_before) - datetime.timedelta(days=1)
    base_date = datetime.date(2025, 1, 1)

    delta_days = (today - base_date).days

    name = misc.get_name(name=name)

    if name is None:
        return None

    for i, d in enumerate(data):
        random.seed(sum(ord(c) for c in name.lower()) + i + 1)
        coef = random.uniform(0.3, 0.7)

        d["level"] = Decimal(d["level"])

        for _ in range(delta_days):
            d["level"] += Decimal(
                round(
                    40
                    / (d["level"] ** Decimal(0.5))
                    / (i + 2)
                    * Decimal(coef + random.uniform(-0.3, 0.3)),
                    4,
                )
            )

    return data


if __name__ == "__main__":
    print(get_current_character_data({}, "12u3h1u23"))
    pass
