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


def update_1D(event):
    """
    플레이어, 랭킹 업데이트
    """
    days_before = event.get("days_before", 0)

    today = misc.get_today(days_before + 1)

    # 플레이어 업데이트
    try:
        players = rp.get_registered_players()

        threads = []
        for player in players:
            update_player(event, player["name"], player["id"])

            ## 쓰레드로 업데이트
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
        rankdata = gri.get_current_rank_data(None, days_before=days_before + 1)

        failed_list = []
        registered_players = rp.get_registered_players()
        registered_names = [player["name"] for player in registered_players]
        for i, j in enumerate(rankdata):
            try:
                name = j["name"]

                if name not in registered_names:  # 등록 안된 유저
                    result = rp.register_player(name, 1)

                    if result == 1:
                        sm.send_log(6, event, f"{name} 등록 not name1")
                    elif result == 2:
                        changed_name = misc.get_profile_from_mc(name=name)
                        sm.send_log(
                            6, event, f"{name} -> {changed_name} 업데이트 not name1"
                        )

                item = {
                    "date": today.strftime("%Y-%m-%d"),
                    "rank": i + 1,
                    "id": misc.get_id(name=name),
                    "job": misc.convert_job(j["job"]),
                    "level": j["level"],
                    "slot": j["slot"],
                }

                dm.write_data("Ranks", item)
            except:
                failed_list.append(j)

        if failed_list:
            for i, j in enumerate(failed_list):
                try:
                    name = j["name"]

                    if name not in registered_names:  # 등록 안된 유저
                        result = rp.register_player(name, 1)

                        if result == 1:
                            sm.send_log(6, event, f"{name} 등록 not name2")
                        elif result == 2:
                            changed_name = misc.get_profile_from_mc(name=name)
                            sm.send_log(
                                6, event, f"{name} -> {changed_name} 업데이트 not name2"
                            )

                    item = {
                        "date": today.strftime("%Y-%m-%d"),
                        "rank": i + 1,
                        "id": misc.get_id(name=name),
                        "job": misc.convert_job(j["job"]),
                        "level": j["level"],
                        "slot": j["slot"],
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


def update_player(event, name, id):
    days_before = event.get("days_before", 0)

    failed_list = []
    today = misc.get_today(days_before + 1)

    try:
        data = gci.get_current_character_data(name, days_before + 1)  # 어제

        # 웹사이트 열리면 코드 필요 없음
        if not misc.get_profile_from_mc(
            name
        ):  # name에 해당하는 유저 없음, 등록은 되어있음 -> 닉네임 변경함 => uuid로 등록
            uuid = misc.get_uuid(name)
            if not uuid:
                sm.send_log(5, event, f"{name} 닉네임 변경, 등록된 uuid 없음1")
                raise Exception

            changed_name = misc.get_profile_from_mc(uuid=uuid)
            result = rp.register_player(changed_name, misc.get_main_slot(name))

            if result == 1:
                sm.send_log(6, event, f"{name} -> {changed_name} 등록 mcprofile1")
            elif result == 2:
                sm.send_log(6, event, f"{name} -> {changed_name} 업데이트 mcprofile1")

        if (
            not data
        ):  # 웹사이트에 검색 안됨, 등록 되어있음 -> 닉네임 변경함 => uuid로 등록
            uuid = misc.get_uuid(name)
            if not uuid:
                sm.send_log(5, event, f"{name} 닉네임 변경, 등록된 uuid 없음1")
                raise Exception

            changed_name = misc.get_profile_from_mc(uuid=uuid)
            result = rp.register_player(changed_name, misc.get_main_slot(name))

            if result == 1:
                sm.send_log(6, event, f"{name} -> {changed_name} 등록 not data1")
            elif result == 2:
                sm.send_log(6, event, f"{name} -> {changed_name} 업데이트 not data1")

        else:
            for i, j in enumerate(data):
                item = {
                    "id": id,
                    "date-slot": f"{today.strftime("%Y-%m-%d")}#{i}",
                    "job": misc.convert_job(j["job"]),
                    "level": j["level"],
                }

                dm.write_data("DailyData", item)
    except:
        failed_list.append(name)

    if failed_list:
        try:
            data = gci.get_current_character_data(name, days_before + 1)  # 어제

            # 웹사이트 열리면 코드 필요 없음
            if not misc.get_profile_from_mc(
                name
            ):  # name에 해당하는 유저 없음, 등록은 되어있음 -> 닉네임 변경함 => uuid로 등록
                uuid = misc.get_uuid(name)
                if not uuid:
                    sm.send_log(5, event, f"{name} 닉네임 변경, 등록된 uuid 없음2")
                    raise Exception

                changed_name = misc.get_profile_from_mc(uuid=uuid)
                result = rp.register_player(changed_name, misc.get_main_slot(name))

                if result == 1:
                    sm.send_log(6, event, f"{name} -> {changed_name} 등록 mcprofile2")
                elif result == 2:
                    sm.send_log(
                        6, event, f"{name} -> {changed_name} 업데이트 mcprofile2"
                    )

            if (
                not data
            ):  # 웹사이트에 검색 안됨, 등록 되어있음 -> 닉네임 변경함 => uuid로 등록
                uuid = misc.get_uuid(name)
                if not uuid:
                    sm.send_log(5, event, f"{name} 닉네임 변경, 등록된 uuid 없음2")
                    raise Exception

                changed_name = misc.get_profile_from_mc(uuid=uuid)
                result = rp.register_player(changed_name, misc.get_main_slot(name))

                if result == 1:
                    sm.send_log(6, event, f"{name} -> {changed_name} 등록 not data2")
                elif result == 2:
                    sm.send_log(
                        6, event, f"{name} -> {changed_name} 업데이트 not data2"
                    )

            else:
                for i, j in enumerate(data):
                    item = {
                        "id": id,
                        "date-slot": f"{today.strftime("%Y-%m-%d")}#{i}",
                        "job": misc.convert_job(j["job"]),
                        "level": j["level"],
                    }

                    dm.write_data("DailyData", item)
        except:
            sm.send_log(
                5, event, f"{name} 데이터 업데이트 실패" + traceback.format_exc()
            )


if __name__ == "__main__":
    update_1D({})
    pass
