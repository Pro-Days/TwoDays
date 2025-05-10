import random
import datetime
from decimal import Decimal

import misc
import data_manager
import register_player


def get_current_rank_data(event) -> dict:
    """
    현재 전체 캐릭터 랭킹 데이터 반환
    {"name": "ProDays", "job": "검호", "level": "100"}
    """
    days_before = event.get("days_before", 0)

    today = misc.get_today(days_before) - datetime.timedelta(days=1)
    today_str = today.strftime("%Y-%m-%d")

    players = register_player.get_registered_players()
    data = []

    for player in players:
        playerdata = data_manager.read_data(
            "DailyData",
            None,
            {"id": player["id"], "date-slot": [f"{today_str}#0", f"{today_str}#4"]},
        )
        if playerdata is None:
            continue
        # data.append(playerdata[int(player["mainSlot"]) - 1])

        for i in range(5):
            data.append(playerdata[i])

    rankdata = []

    for d in data:
        rankdata.append(
            {
                "name": misc.get_name(id=d["id"]),
                "job": misc.convert_job(d["job"]),
                "level": Decimal(d["level"]),
            }
        )

    rankdata = sorted(rankdata, key=lambda x: x["level"], reverse=True)[:100]

    return rankdata


if __name__ == "__main__":
    print(get_current_rank_data({}))
    pass
