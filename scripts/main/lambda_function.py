from __future__ import annotations

import datetime
import json
import os
import traceback

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

import get_character_info as gci
import get_level_distribution as gld
import get_rank_info as gri
import misc
import register_player as rp
import send_msg as sm
import update

ADMIN_ID: str | None = os.getenv("DISCORD_ADMIN_ID")
if ADMIN_ID is None:
    raise Exception("DISCORD_ADMIN_ID is not set")


def lambda_handler(event, context) -> dict:
    print(f"start!\nevent: {event}")

    # 전체 코드 실행 후 오류가 발생하면 로그에 출력하고 400 반환
    try:
        return command_handler(event)

    except:
        traceback.print_exc()
        sm.send(event, "오류가 발생했습니다.", log_type=3, error=traceback.format_exc())
        return {"statusCode": 400, "body": json.dumps(traceback.format_exc())}


def command_handler(event) -> dict:

    # 업데이트 커맨드
    if event.get("action", None) == "update_1D":
        update.update_1D(event)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "업데이트 완료"}, ensure_ascii=False),
        }

    body: dict = json.loads(event["body"])
    cmd: str = body["data"]["name"]
    options: list[dict[str, str]] = body["data"].get("options", [])

    print(f"command: {cmd}, options: {options}")

    # 어드민 커맨드
    if body["member"]["user"]["id"] == ADMIN_ID:
        # ip 주소
        if cmd == "ip":
            ip: str = misc.get_ip()

            return sm.send(event, f"아이피 주소: {ip}", log_type=2)

        # 등록된 유저 수
        elif cmd == "user_count":
            pl_list: list = rp.get_registered_players()

            return sm.send(event, f"등록된 유저 수: {len(pl_list)}", log_type=2)

        # 설치된 서버 목록
        elif cmd == "server_list":
            server_list: list[dict[str, str]] = misc.get_guild_list()

            msg: str = (
                f"서버 수: {len(server_list)}\n서버 목록\n"
                + "```"
                + ", ".join([server["name"] for server in server_list])
                + "```"
            )

            return sm.send(event, msg, log_type=2)

    # 일반 커맨드
    if cmd == "랭킹":
        return cmd_ranking(event, options)

    elif cmd == "검색":
        return cmd_search(event, options)

    elif cmd == "유저분포":
        return cmd_user_distribution(event, options)

    elif cmd == "등록":
        return cmd_register(event, options)

    else:
        sm.send(
            event, "오류가 발생했습니다.", log_type=3, error=f"unhandled command: {cmd}"
        )
        return {"statusCode": 400, "body": json.dumps(f"unhandled command: {cmd}")}


def _parse_date(day_expression: str | None) -> datetime.date | None:
    """
    None: 날짜 입력이 올바르지 않음
    YYYY-MM-DD, MM-DD, DD, -1, ...
    """

    try:
        today: datetime.date = misc.get_today()

        if day_expression:
            if day_expression[0] == "-" and day_expression[1:].isdigit():
                date = int(day_expression[1:])
                today = today - datetime.timedelta(days=date)

            else:
                date_type: int = day_expression.count("-")
                today_list: list[str] = str(today).split("-")

                if date_type == 0:  # 날짜만
                    day_expression = "-".join(today_list[:2]) + "-" + day_expression

                if date_type == 1:
                    day_expression = today_list[0] + "-" + day_expression

                today = datetime.datetime.strptime(day_expression, "%Y-%m-%d").date()

        else:
            today = today

    except:
        return None

    return today


def cmd_ranking(event: dict, options: list[dict]) -> dict:
    range_str: str = "1..10"
    date_expression: str | None = None
    period: str | None = None

    # 옵션에서 입력값 가져오기
    for i in options:
        if i["name"] == "랭킹범위":
            range_str = i["value"]

        elif i["name"] == "날짜":
            date_expression = i["value"]

        elif i["name"] == "기간":
            period = i["value"]

    # 날짜 불러오기
    target_date: datetime.date | None = _parse_date(date_expression)

    # 날짜 입력이 올바르지 않다면
    if not target_date:
        return sm.send(
            event,
            "날짜 입력이 올바르지 않습니다: YYYY-MM-DD, MM-DD, DD, -n (예시: 2025-12-31, 12-01, 05, -1, -20)",
        )

    # 미래 날짜라면
    elif target_date > misc.get_today():
        return sm.send(event, "미래 날짜는 조회할 수 없습니다.")

    # 랭킹 범위 파싱
    range_list: list[str] = range_str.split("..")
    rank_start, rank_end = map(int, range_list)

    # 랭킹 범위 입력이 올바르지 않다면
    if len(range_list) != 2:
        return sm.send(event, "랭킹 범위는 '시작..끝' 형식으로 입력해주세요.")

    elif rank_start < 1 or rank_end > 100:
        return sm.send(event, "랭킹 범위는 1~100 사이의 숫자로 입력해주세요.")

    elif rank_start > rank_end:
        return sm.send(event, "랭킹 범위는 시작이 끝보다 작거나 같아야 합니다.")

    # 랭킹 정보 가져오기
    # 기간이 입력되지 않았다면 해당 날짜의 랭킹 정보 가져오기
    if period is None:
        msg, image_path = gri.get_rank_info(rank_start, rank_end, target_date)

    # 기간이 입력되었다면 랭킹 변화량 정보 가져오기
    else:
        if not period.isdigit() or int(period) < 1:
            return sm.send(event, "기간은 1 이상의 숫자로 입력해주세요.")

        msg, image_path = gri.get_rank_history(
            rank_start, rank_end, int(period), target_date
        )

    # 랭킹 정보 가져오기에 실패했다면
    if not msg:
        raise Exception("cannot get rank info")

    return sm.send(event, msg, image=image_path)


def cmd_search(event: dict, options: list[dict]) -> dict:
    # 랭킹 또는 레벨 검색인지 확인
    _type = options[0]["name"]

    name: str | None = None
    period: str = "7"
    today: str | None = None

    for i in options[0]["options"]:
        if i["name"] == "닉네임":
            name = i["value"]

        elif i["name"] == "기간":
            period = i["value"]

        elif i["name"] == "날짜":
            today = i["value"]

    # name이 입력되지 않았다면
    if name is None:
        return sm.send(event, "닉네임을 입력해주세요.")

    real_name, uuid = misc.get_profile_from_name(name)

    if uuid is None or real_name is None:
        return sm.send(
            event, f"플레이어 정보를 가져올 수 없습니다. 닉네임을 확인해주세요."
        )

    # period 확인
    if period is not None and not period.isdigit():
        return sm.send(event, "기간은 숫자로 입력해주세요.")
    period_int: int = int(period) if period is not None else 7

    # name이 등록되어있지 않다면 등록하기
    register_msg: str = ""
    if not rp.is_registered(uuid):
        rp.register_player(uuid, real_name)
        register_msg = (
            f"등록되어있지 않은 플레이어네요. {real_name}님을 등록했어요.\n\n"
        )

    target_date: datetime.date | None = _parse_date(today)
    if target_date is None:
        return sm.send(
            event,
            "날짜 입력이 올바르지 않습니다: YYYY-MM-DD, MM-DD, DD, -n (예시: 2025-12-31, 12-01, 05, -1, -20)",
        )

    elif target_date > misc.get_today():
        return sm.send(event, "미래 날짜는 조회할 수 없습니다.")

    # 레벨 검색이라면 캐릭터 정보 가져오기
    if _type == "레벨":
        msg, image_path = gci.get_character_info(
            uuid, real_name, period_int, target_date
        )

    # 랭킹 검색이라면 랭킹 변화량 정보 가져오기
    elif _type == "랭킹":
        msg, image_path = gci.get_charater_rank_history(
            uuid, name, period_int, target_date
        )

    else:
        return sm.send(event, "검색 종류가 올바르지 않습니다.")

    msg: str = register_msg + msg

    return sm.send(event, msg, image=image_path)


def cmd_user_distribution(event: dict, options: list[dict]) -> dict:
    date: str = "-1"
    for i in options:
        if i["name"] == "날짜":
            date = i["value"]

    target_date: datetime.date | None = _parse_date(date)
    if target_date is None:
        return sm.send(
            event,
            "날짜 입력이 올바르지 않습니다: YYYY-MM-DD, MM-DD, DD, -n (예시: 2025-12-31, 12-01, 05, -1, -20)",
        )

    elif target_date > misc.get_today():
        return sm.send(event, "미래 날짜는 조회할 수 없습니다.")

    elif target_date == misc.get_today():
        return sm.send(event, "오늘 날짜는 조회할 수 없습니다.")

    msg, image_path = gld.get_level_distribution(target_date)

    return sm.send(event, msg, image=image_path)


def cmd_register(event: dict, options: list[dict]) -> dict:
    name: str | None = None
    for i in options:

        if i["name"] == "닉네임":
            name = i["value"]

    if name is None:
        return sm.send(event, "닉네임을 입력해주세요.")

    real_name, uuid = misc.get_profile_from_name(name)
    if uuid is None or real_name is None:
        return sm.send(
            event, f"플레이어 정보를 가져올 수 없습니다. 닉네임을 확인해주세요."
        )

    rp.register_player(uuid, real_name)

    return sm.send(event, f"{real_name}님을 등록했어요.\n\n")


if __name__ == "__main__":
    lambda_handler({"action": "update_1D"}, None)
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
