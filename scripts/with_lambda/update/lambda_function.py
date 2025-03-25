import os
import json
import time
import datetime
import threading
import traceback

import misc
import send_msg as sm
import data_manager as dm
import get_rank_info as gri
import register_player as rp
import get_character_info as gci


def lambda_handler(event, context):
    print(f"start!\nevent: {event}")

    try:
        if event["action"] == "update_1D":
            update_1D(event)

            return {"statusCode": 200, "body": json.dumps({"message": "업데이트 완료"}, ensure_ascii=False)}

    except:
        sm.send_log(5, event, traceback.format_exc())
        return {"statusCode": 400, "body": json.dumps(traceback.format_exc())}


def update_1D(event):
    """
    플레이어, 랭킹 업데이트
    """

    # 랭킹 업데이트
    today = misc.get_today() - datetime.timedelta(days=1)

    try:
        # 랭커 등록, 업데이트
        rankdata = gri.get_current_rank_data()

        failed_list = []
        for i, j in enumerate(rankdata):
            try:
                name = j["name"]

                if not rp.is_registered(name):
                    result = rp.register_player(name, 1)

                    if result == 1:
                        sm.send_log(6, event, f"{name} 등록")
                    elif result == 2:
                        sm.send_log(6, event, f"{name} 업데이트")

                item = {
                    "date": today.strftime("%Y-%m-%d"),
                    "rank": i + 1,
                    "id": misc.get_id(name=name),
                    "job": misc.convert_job(j["job"]),
                    "level": float(j["level"]),
                }

                dm.write_data("Ranks", item)
            except:
                failed_list.append(j)

        if failed_list:
            for i, j in enumerate(failed_list):
                try:
                    name = j["name"]

                    if not rp.is_registered(name):
                        result = rp.register_player(name, 1)

                        if result == 1:
                            sm.send_log(6, event, f"{name} 등록")
                        elif result == 2:
                            sm.send_log(6, event, f"{name} 업데이트")

                    item = {
                        "date": today.strftime("%Y-%m-%d"),
                        "rank": i + 1,
                        "id": misc.get_id(name=name),
                        "job": misc.convert_job(j["job"]),
                        "level": float(j["level"]),
                    }

                    dm.write_data("Ranks", item)
                except:
                    sm.send_log(5, event, f"랭킹 데이터 업데이트 실패: {j}" + traceback.format_exc())

    except:
        sm.send_log(5, event, "랭킹 데이터 업데이트 실패" + traceback.format_exc())

    # 플레이어 업데이트
    try:
        players = rp.get_registered_players()

        threads = []
        for player in players:
            t = threading.Thread(target=update_player, args=(event, player["name"], player["id"]))
            t.start()
            threads.append(t)

            # 2 players/sec: 600 players -> 5 min: 50 won/month
            time.sleep(0.5)

        for t in threads:
            t.join()
    except:
        sm.send_log(5, event, "플레이어 데이터 업데이트 실패" + traceback.format_exc())

    sm.send_log(4, event, "데이터 업데이트 완료")


def update_player(event, name, id):
    failed_list = []
    try:
        data = gci.get_current_character_data(name)
        today = misc.get_today() - datetime.timedelta(days=1)

        if not data:
            result = rp.register_player(name, misc.get_main_slot(name))

            if result == 1:
                sm.send_log(6, event, f"{name} 등록")
            elif result == 2:
                sm.send_log(6, event, f"{name} 업데이트")

        for i, j in enumerate(data):
            item = {
                "id": id,
                "date-slot": f"{today.strftime("%Y-%m-%d")}#{i}",
                "job": misc.convert_job(j["job"]),
                "level": float(j["level"]),
            }

            dm.write_data("DailyData", item)
    except:
        failed_list.append(name)

    if failed_list:
        try:
            data = gci.get_current_character_data(name)
            today = misc.get_today() - datetime.timedelta(days=1)

            if not data:
                result = rp.register_player(name, misc.get_main_slot(name))

                if result == 1:
                    sm.send_log(6, event, f"{name} 등록")
                elif result == 2:
                    sm.send_log(6, event, f"{name} 업데이트")

            for i, j in enumerate(data):
                item = {
                    "id": id,
                    "date-slot": f"{today.strftime("%Y-%m-%d")}#{i}",
                    "job": misc.convert_job(j["job"]),
                    "level": float(j["level"]),
                }

                dm.write_data("DailyData", item)
        except:
            sm.send_log(5, event, f"{name} 데이터 업데이트 실패" + traceback.format_exc())


if __name__ == "__main__":
    print(lambda_handler({"action": "update_1D"}, None))
    pass
