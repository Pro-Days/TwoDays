import traceback
from datetime import date

import data_manager as dm
import get_character_info as gci
import get_rank_info as gri
import misc
import register_player as rp
import send_msg as sm


def update_1D(event):
    """
    플레이어, 랭킹 업데이트
    """
    days_before = event.get("days_before", 0)

    today: date = misc.get_today(days_before + 1)

    # 플레이어 업데이트
    try:
        players = rp.get_registered_players()

        threads = []
        for player in players:
            update_player(event, player["uuid"], player["name"])

            # 쓰레드로 업데이트
            # t = threading.Thread(target=update_player, args=(event, player["name"], player["id"]))
            # t.start()
            # threads.append(t)

            # 10 players/sec: 1000 players -> 100 sec
            # time.sleep(0.1)

        for t in threads:
            t.join()
    except:
        sm.send_log(5, event, "플레이어 데이터 업데이트 실패" + traceback.format_exc())

    # 랭커 등록, 업데이트
    try:
        rankdata = gri.get_current_rank_data()

        failed_list = []
        for i, j in enumerate(rankdata):
            try:
                item = {
                    "date": today.strftime("%Y-%m-%d"),
                    "rank": i + 1,
                    "uuid": j.uuid,
                    "level": j.level,
                }

                dm.write_data("Ranks", item)

            except:
                failed_list.append(j)

        if failed_list:
            for i, j in enumerate(failed_list):
                try:

                    item = {
                        "date": today.strftime("%Y-%m-%d"),
                        "rank": i + 1,
                        "uuid": j.uuid,
                        "level": j.level,
                    }

                    dm.write_data("Ranks", item)

                except:
                    sm.send_log(
                        5,
                        event,
                        f"랭킹 데이터 업데이트 실패: {j}" + traceback.format_exc(),
                    )

    except:
        sm.send_log(5, event, "랭킹 데이터 업데이트 실패" + traceback.format_exc())

    sm.send_log(4, event, "데이터 업데이트 완료")


def update_player(event, uuid, name):
    days_before = event.get("days_before", 0)

    failed_list = []
    today = misc.get_today(days_before + 1)

    try:
        data = gci.get_current_character_data(name, days_before + 1)  # 어제(DEV)

        item = {
            "uuid": uuid,
            "date": today.strftime("%Y-%m-%d"),
            "level": data.level,
        }

        dm.write_data("DailyData", item)
    except:
        failed_list.append(name)

    if failed_list:
        try:
            data = gci.get_current_character_data(name, days_before + 1)  # 어제

            item = {
                "uuid": uuid,
                "date": today.strftime("%Y-%m-%d"),
                "level": data.level,
            }

            dm.write_data("DailyData", item)
        except:
            sm.send_log(
                5, event, f"{name} 데이터 업데이트 실패" + traceback.format_exc()
            )


if __name__ == "__main__":
    update_1D({"action": "update_1D"})
    pass
