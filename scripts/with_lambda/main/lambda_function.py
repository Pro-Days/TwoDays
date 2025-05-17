import os
import json
import traceback
from rich.console import Console
import misc
import send_msg as sm
import get_rank_info as gri
import register_player as rp
import get_character_info as gci
import get_level_distribution as gld
import update


ADMIN_ID = os.getenv("DISCORD_ADMIN_ID")
console = Console()


def lambda_handler(event, context):
    print(f"start!\nevent: {event}")

    try:
        return command_handler(event)

    except:
        console.print_exception(show_locals=True)
        sm.send(event, "오류가 발생했습니다.", log_type=3, error=traceback.format_exc())
        return {"statusCode": 400, "body": json.dumps(traceback.format_exc())}


def command_handler(event):

    if event.get("action", None) == "update_1D":
        update.update_1D(event)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "업데이트 완료"}, ensure_ascii=False),
        }

    body = json.loads(event["body"])
    cmd = body["data"]["name"]
    options = body["data"]["options"] if "options" in body["data"] else []

    print(f"command: {cmd}, options: {options}")

    # 어드민 커맨드
    if body["member"]["user"]["id"] == ADMIN_ID:
        if cmd == "ip":
            ip = misc.get_ip()

            return sm.send(event, f"아이피 주소: {ip}", log_type=2)

        elif cmd == "user_count":
            pl_list = rp.get_registered_players()

            return sm.send(event, f"등록된 유저 수: {len(pl_list)}", log_type=2)

        elif cmd == "server_list":
            server_list = misc.get_guild_list()

            msg = (
                f"서버 수: {len(server_list)}\n서버 목록\n"
                + "```"
                + ", ".join([server["name"] for server in server_list])
                + "```"
            )

            return sm.send(event, msg, log_type=2)

    # 일반 커맨드
    if cmd == "랭킹":

        range_str = "1..10"
        today = None
        period = None
        for i in options:
            if i["name"] == "랭킹범위":
                range_str = i["value"]

            elif i["name"] == "날짜":
                today = i["value"]

            elif i["name"] == "기간":
                period = i["value"]

        today = misc.get_today_from_input(today)
        if today == -1:
            return sm.send(
                event,
                "날짜 입력이 올바르지 않습니다: YYYY-MM-DD, MM-DD, DD, -n (예시: 2025-12-31, 12-01, 05, -1, -20)",
            )
        elif today == -2:
            return sm.send(event, "미래 날짜는 조회할 수 없습니다.")

        range_str = range_str.split("..")
        _range = list(map(int, range_str))
        if len(_range) != 2:
            return sm.send(event, "랭킹 범위는 '시작..끝' 형식으로 입력해주세요.")
        elif _range[0] < 1 or _range[1] > 100:
            return sm.send(event, "랭킹 범위는 1~100 사이의 숫자로 입력해주세요.")
        elif _range[0] >= _range[1]:
            return sm.send(event, "랭킹 범위는 시작이 끝보다 작아야 합니다.")

        if period is None:
            msg, image_path = gri.get_rank_info(_range, today)
        else:
            msg, image_path = gri.get_rank_history(_range, period, today)

        if not msg:
            raise Exception("cannot get rank info")

        return sm.send(event, msg, image=image_path)

    elif cmd == "검색":

        _type = options[0]["name"]
        options = options[0]["options"]

        name = None
        slot = None
        period = 7
        today = None

        for i in options:
            if i["name"] == "닉네임":
                name = i["value"]

            elif i["name"] == "슬롯":
                slot = i["value"]

            elif i["name"] == "기간":
                period = i["value"]

            elif i["name"] == "날짜":
                today = i["value"]

        if name is None:
            return sm.send(event, "닉네임을 입력해주세요.")

        register_msg = None
        if not rp.is_registered(name):
            result = rp.register_player(name, 1)

            if result == 1:
                register_msg = (
                    f"등록되어있지 않은 플레이어네요. {name}님을 등록했어요.\n\n"
                )
            elif result == -1:
                return sm.send(event, f"오류가 발생했어요. 닉네임을 확인해주세요.")

        today = misc.get_today_from_input(today)
        if today == -1:
            return sm.send(
                event,
                "날짜 입력이 올바르지 않습니다: YYYY-MM-DD, MM-DD, DD, -n (예시: 2025-12-31, 12-01, 05, -1, -20)",
            )
        elif today == -2:
            return sm.send(event, "미래 날짜는 조회할 수 없습니다.")

        if _type == "레벨":
            msg, image_path = gci.get_character_info(name, slot, period, today)
        else:  # 랭킹
            msg, image_path = gci.get_charater_rank_history(name, period, today)

        if register_msg:
            msg = register_msg + msg

        return sm.send(event, msg, image=image_path)

    elif cmd == "유저분포":

        today = "-1"
        for i in options:
            if i["name"] == "날짜":
                today = i["value"]

        today = misc.get_today_from_input(today)
        if today == -1:
            return sm.send(
                event,
                "날짜 입력이 올바르지 않습니다: YYYY-MM-DD, MM-DD, DD, -n (예시: 2025-12-31, 12-01, 05, -1, -20)",
            )
        elif today == -2:
            return sm.send(event, "미래 날짜는 조회할 수 없습니다.")
        elif today == misc.get_today():
            return sm.send(event, "오늘 날짜는 조회할 수 없습니다.")

        msg, image_path = gld.get_level_distribution(today)

        return sm.send(event, msg, image=image_path)

    elif cmd == "등록":

        name = None
        slot = 1
        for i in options:

            if i["name"] == "닉네임":
                name = i["value"]

            elif i["name"] == "슬롯":
                slot = i["value"]

        if name is None:
            return sm.send(event, "닉네임을 입력해주세요.")

        result = rp.register_player(name, slot)

        if result == -1:
            msg = f"{name}님의 등록에 실패했습니다. 닉네임을 확인해주세요."
        else:  # 1, 2
            msg = f"{name}님을 등록했습니다."

        return sm.send(event, msg)

    else:
        sm.send(
            event, "오류가 발생했습니다.", log_type=3, error=f"unhandled command: {cmd}"
        )
        return {"statusCode": 400, "body": json.dumps(f"unhandled command: {cmd}")}


if __name__ == "__main__":
    for i in range(135, -1, -1):
        lambda_handler({"action": "update_1D", "days_before": i}, None)
    event = {
        "body": """
        {"authorizing_integration_owners":
            {
                "0":"738633695186911232",
                "1":"407775594714103808"
            },
        "channel":
            {
                "id":"1248627932037910558",
                "name":"채팅"
            },
        "data":{
            "name":"랭킹",
            "options":[
                {
                    "name":"랭킹 범위",
                    "value":"80..90"
                },
                {
                    "name":"기간",
                    "value":5
                }
            ]
        },
        "guild_id":"738633695186911232",
        "member":{
            "user":{
                "global_name":"데이즈",
                "id":"407775594714103808",
                "username":"prodays"
                }
            }
        }""",
    }
    # lambda_handler(event, None)
    pass
