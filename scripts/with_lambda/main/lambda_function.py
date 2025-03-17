import os
import json
import datetime
import traceback

import misc
import send_msg as sm
import get_rank_info as gri
import register_player as rp
import get_character_info as gci


ADMIN_ID = os.getenv("DISCORD_ADMIN_ID")


def lambda_handler(event, context):
    print(f"start!\nevent: {event}")

    try:
        return command_handler(event)

    except:
        sm.send(event, "오류가 발생했습니다.", log_type=3, error=traceback.format_exc())
        return {"statusCode": 400, "body": json.dumps(traceback.format_exc())}


def command_handler(event):

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

        page = 1
        today = None
        period = None
        for i in options:
            if i["name"] == "페이지":
                page = i["value"]

            elif i["name"] == "날짜":
                today = i["value"]

            elif i["name"] == "기간":
                period = i["value"]

        # if not (1 <= page <= 10):
        if not (1 <= page <= 3):  # 임시로 3까지만
            return sm.send(event, "페이지는 1부터 10까지만 가능합니다.")

        today = misc.get_today_from_input(today)
        if today == -1:
            return sm.send(event, "날짜 입력이 올바르지 않습니다. (YYYY-MM-DD, MM-DD, DD, 1일전, ...)")
        elif today == -2:
            return sm.send(event, "미래 날짜는 조회할 수 없습니다.")

        msg, image_path = gri.get_rank_info(page, period, today)

        return sm.send(event, msg, image=image_path)

    elif cmd == "검색":

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

        reg_msg = None
        if rp.is_registered(name) is False:
            result = rp.register_player(name, 1)
            if result:
                reg_msg = f"등록되어있지 않은 플레이어네요. {name}님을 등록했어요.\n\n"
            else:
                return sm.send(event, f"오류가 발생했어요. 등록을 먼저 해주세요.")

        if slot is None:
            slot = misc.get_main_slot(name)
        default = True if slot == 1 else False

        if not (slot in [1, 2, 3, 4, 5]):
            return sm.send(event, "슬롯은 1부터 5까지만 가능합니다.")

        if not (1 <= period <= 365):
            return sm.send(event, "기간은 1부터 365까지만 가능합니다.")

        today = misc.get_today_from_input(today)
        if today == -1:
            return sm.send(event, "날짜 입력이 올바르지 않습니다. (YYYY-MM-DD, MM-DD, DD, 1일전, ...)")
        elif today == -2:
            return sm.send(event, "미래 날짜는 조회할 수 없습니다.")

        msg, image_path = gci.get_character_info(name, slot, period, default, today)

        if reg_msg:
            msg = reg_msg + msg

        return sm.send(event, msg, image=image_path)

    elif cmd == "등록":

        slot = 1
        for i in options:

            if i["name"] == "닉네임":
                name = i["value"]

            elif i["name"] == "슬롯":
                slot = i["value"]

        if not (slot in [1, 2, 3, 4, 5]):
            return sm.send(event, "슬롯은 1부터 5까지만 가능합니다.")

        result = rp.register_player(name, slot)

        if result:
            msg = f"{name}님을 등록했습니다."
        else:
            msg = f"{name}님의 등록에 실패했습니다. 닉네임을 확인해주세요."

        return sm.send(event, msg)

    else:
        sm.send(event, "오류가 발생했습니다.", log_type=3, error=f"unhandled command: {cmd}")
        return {"statusCode": 400, "body": json.dumps(f"unhandled command: {cmd}")}
