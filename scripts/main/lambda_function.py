"""메인 Lambda 엔트리포인트와 디스코드 명령 라우팅을 담당한다."""

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

from typing import TYPE_CHECKING

import scripts.main.features.get_character_info as gci
import scripts.main.features.get_level_distribution as gld
import scripts.main.features.get_rank_info as gri
import scripts.main.features.register_player as rp
import scripts.main.integrations.discord.discord_admin_api as daa
import scripts.main.integrations.discord.message_actions as ma
import scripts.main.integrations.discord.send_msg as sm
import scripts.main.integrations.minecraft.minecraft_profile_service as mps
import scripts.main.interface.command_parsers as cp
import scripts.main.interface.command_validation as cv
import scripts.main.interface.interaction_parsers as ip
import scripts.main.jobs.update as update
from scripts.main.shared.utils.log_utils import (
    get_logger,
    setup_logging,
    summarize_event,
    truncate_text,
)

if TYPE_CHECKING:
    from logging import Logger

setup_logging()
logger: Logger = get_logger(__name__)

ADMIN_ID: str | None = os.getenv("DISCORD_ADMIN_ID")
if ADMIN_ID is None:
    raise Exception("DISCORD_ADMIN_ID is not set")

DISCORD_APP_ID: str | None = os.getenv("DISCORD_APP_ID")


def lambda_handler(event, context) -> dict:
    logger.info("lambda_handler start: " f"{summarize_event(event)}")

    # 전체 코드 실행 후 오류가 발생하면 로그에 출력하고 400 반환
    try:
        result: dict = command_handler(event)

        logger.info(
            "lambda_handler success: "
            f"statusCode={result.get('statusCode') if isinstance(result, dict) else None}"
        )

        return result

    except Exception:
        logger.exception("lambda_handler failed: " f"{summarize_event(event)}")

        sm.send(
            event,
            "오류가 발생했습니다.",
            log_type=sm.LogType.COMMAND_ERROR,
            error=traceback.format_exc(),
        )

        return {"statusCode": 400, "body": json.dumps(traceback.format_exc())}


def command_handler(event) -> dict:
    logger.debug(f"command_handler input event={summarize_event(event)}")

    # 스케줄러/운영 액션과 디스코드 인터랙션 이벤트를 같은 엔트리포인트에서 처리
    # 업데이트 커맨드
    if event.get("action", None) == "update_1D":
        logger.info("handling update action: " f"{event.get('action')}")

        # 1D 업데이트 실행 후 결과에 따라 메시지와 상태 코드 결정
        update_result: dict = update.update_1D(event)

        is_ok: bool = bool(update_result.get("ok"))
        status_text: str = str(update_result.get("status", "failed"))

        if is_ok:
            message = "업데이트 완료"
            status_code = 200

        elif status_text == "partial_failure":
            message = "업데이트 일부 실패"
            status_code = 500

        else:
            message = "업데이트 실패"
            status_code = 500

        return {
            "statusCode": status_code,
            "body": json.dumps(
                {"message": message, "result": update_result}, ensure_ascii=False
            ),
        }

    body: dict = json.loads(event["body"])
    data: dict = body.get("data", {})
    cmd: str = data.get("name", "")
    options: list[dict[str, str]] = data.get("options", []) or []
    cmd_type: int | None = data.get("type")

    if cmd_type == ip.ApplicationCommandType.MESSAGE and cmd == "메시지 삭제":
        return _handle_message_delete(event, body)

    logger.info(
        "discord command received: "
        f"cmd={cmd} "
        f"options={truncate_text(options, 1000)}"
    )

    requester_id: str | None = ip.resolve_requester_id(body)

    # 어드민 커맨드
    if requester_id == ADMIN_ID:
        # ip 주소
        # TODO: 제거 고려
        if cmd == "ip":
            ip_address: str = daa.get_ip()

            return sm.send(
                event, f"아이피 주소: {ip_address}", log_type=sm.LogType.ADMIN_COMMAND
            )

        # 등록된 유저 수
        elif cmd == "user_count":
            pl_list: list = rp.get_registered_players()

            return sm.send(
                event,
                f"등록된 유저 수: {len(pl_list)}",
                log_type=sm.LogType.ADMIN_COMMAND,
            )

        # 설치된 서버 목록
        elif cmd == "server_list":
            server_list: list[dict[str, str]] = daa.get_guild_list()

            msg: str = (
                f"서버 수: {len(server_list)}\n서버 목록\n"
                + "```"
                + ", ".join([server["name"] for server in server_list])
                + "```"
            )

            return sm.send(event, msg, log_type=sm.LogType.ADMIN_COMMAND)

    # 실제 명령 구현은 아래 cmd_* 함수에서 처리
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
        logger.warning("unhandled command: " f"{cmd}")

        sm.send(
            event,
            "오류가 발생했습니다.",
            log_type=sm.LogType.COMMAND_ERROR,
            error=f"unhandled command: {cmd}",
        )
        return {"statusCode": 400, "body": json.dumps(f"unhandled command: {cmd}")}


def _is_bot_message(
    target: ip.MessageContextTarget,
    app_id: str | None,
) -> bool:
    if not app_id:
        return False

    if target.author_id == app_id:
        return True

    if target.application_id == app_id:
        return True

    return False


def _handle_message_delete(event: dict, body: dict) -> dict:
    target: ip.MessageContextTarget | None = ip.resolve_message_target(body)

    if target is None:
        return sm.send(
            event,
            "삭제할 메시지를 찾을 수 없습니다.",
            log_type=sm.LogType.COMMAND_ERROR,
        )

    if not _is_bot_message(target, DISCORD_APP_ID):
        return sm.send(
            event,
            "봇이 보낸 메시지만 삭제할 수 있습니다.",
            log_type=sm.LogType.COMMAND_ERROR,
        )

    requester_id: str | None = ip.resolve_requester_id(body)
    can_delete: bool = ip.can_delete_message(
        requester_id,
        ADMIN_ID,
        DISCORD_APP_ID,
        target,
    )

    if not can_delete:
        return sm.send(
            event,
            "삭제 권한이 없습니다.",
            log_type=sm.LogType.COMMAND_ERROR,
        )

    result: ma.DiscordHttpResult = ma.delete_message(
        target.channel_id, target.message_id
    )
    status_code: int = result.response.status_code

    if status_code in (200, 204):
        return sm.send(
            event,
            "메시지를 삭제했습니다.",
            log_type=sm.LogType.COMMAND,
        )

    response_text: str = truncate_text(result.body, 600)
    error_text: str = (
        f"message delete failed: status={status_code} response={response_text}"
    )

    return sm.send(
        event,
        "메시지 삭제에 실패했습니다.",
        log_type=sm.LogType.COMMAND_ERROR,
        error=error_text,
    )


def cmd_ranking(event: dict, options: list[dict]) -> dict:
    logger.debug(f"cmd_ranking options={truncate_text(options, 1000)}")

    ranking_options: list[dict] = options

    if not (options and "options" in options[0]):
        return sm.send(event, "랭킹 종류가 올바르지 않습니다.")

    ranking_type: str = options[0]["name"]

    if ranking_type == "전투력":
        metric = "power"
    elif ranking_type == "레벨":
        metric = "level"
    else:
        return sm.send(event, "랭킹 종류가 올바르지 않습니다.")

    ranking_options = options[0].get("options", [])

    range_str: str = "1..10"
    date_expression: str | None = None
    period: int | None = None

    # 옵션에서 입력값 가져오기
    for i in ranking_options:
        if i["name"] == "랭킹범위":
            range_str = i["value"]

        elif i["name"] == "날짜":
            date_expression = i["value"]

        elif i["name"] == "기간":
            period = i["value"]

    # 파싱과 정책 검증을 분리해 같은 파서를 다른 명령에서도 재사용
    # 날짜 불러오기
    target_date: datetime.date | None = cp.parse_date_expression(date_expression)
    date_error: str | None = cv.validate_target_date(target_date)

    if date_error:
        return sm.send(event, date_error)

    if target_date is None:
        return sm.send(event, cv.DATE_INPUT_INVALID_MESSAGE)

    # 파서 에러 코드를 사용자 메시지로 변환하는 계층
    try:
        rank_start, rank_end = cp.parse_rank_range(range_str, min_rank=1, max_rank=100)

    except cp.OptionParseError as exc:
        if exc.code == "invalid_format":
            return sm.send(event, "랭킹 범위는 '시작..끝' 형식으로 입력해주세요.")

        if exc.code in {"invalid_number", "out_of_bounds"}:
            return sm.send(event, "랭킹 범위는 1~100 사이의 숫자로 입력해주세요.")

        if exc.code == "invalid_order":
            return sm.send(event, "랭킹 범위는 시작이 끝보다 작거나 같아야 합니다.")

        return sm.send(event, "랭킹 범위는 '시작..끝' 형식으로 입력해주세요.")

    # 랭킹 정보 가져오기
    # 기간이 입력되지 않았다면 해당 날짜의 랭킹 정보 가져오기
    if period is None:
        logger.info(
            "fetching rank info: "
            f"start={rank_start} "
            f"end={rank_end} "
            f"metric={metric} "
            f"date={target_date}"
        )

        msg, image_path = gri.get_rank_info(
            rank_start, rank_end, target_date, metric=metric
        )

    # 기간이 입력되었다면 랭킹 변화량 정보 가져오기
    else:
        try:
            period_int: int = cp.parse_positive_int_option(
                period,
                default=1,
                min_value=1,
            )

        except cp.OptionParseError:
            return sm.send(event, "기간은 1 이상의 숫자로 입력해주세요.")

        logger.info(
            "fetching rank history: "
            f"start={rank_start} "
            f"end={rank_end} "
            f"period={period_int} "
            f"metric={metric} "
            f"date={target_date}"
        )

        msg, image_path = gri.get_rank_history(
            rank_start, rank_end, period_int, target_date, metric=metric
        )

    # 랭킹 정보 가져오기에 실패했다면
    if not msg:
        raise Exception("cannot get rank info")

    return sm.send(event, msg, image=image_path)


def cmd_search(event: dict, options: list[dict]) -> dict:
    logger.debug(f"cmd_search options={truncate_text(options, 1000)}")

    # 검색 타입 확인 (레벨 / 전투력)
    if not options:
        return sm.send(event, "검색 종류를 선택해주세요.")

    _type = options[0]["name"]

    name: str | None = None
    period: int | None = 7
    today: str | None = None

    sub_options = options[0].get("options", [])
    for i in sub_options:
        if i["name"] == "닉네임":
            name = i["value"]

        elif i["name"] == "기간":
            period = i["value"]

        elif i["name"] == "날짜":
            today = i["value"]

    # name이 입력되지 않았다면
    if name is None:
        return sm.send(event, "닉네임을 입력해주세요.")

    real_name, uuid = mps.get_profile_from_name(name)
    logger.info(
        "search resolved profile: "
        f"input={name} "
        f"resolved_name={real_name} "
        f"uuid={uuid} "
        f"type={_type}"
    )

    if uuid is None or real_name is None:
        return sm.send(
            event, f"플레이어 정보를 가져올 수 없습니다. 닉네임을 확인해주세요."
        )

    # Discord 옵션 타입이 환경에 따라 int/str로 올 수 있어 공통 파서로 정규화
    # period 확인
    try:
        period_int: int = cp.parse_positive_int_option(period, default=7, min_value=0)

    except cp.OptionParseError:
        return sm.send(event, "기간은 숫자로 입력해주세요.")

    # name이 등록되어있지 않다면 등록하기
    register_msg: str = ""
    if not rp.is_registered(uuid):

        logger.info(
            "auto-registering user during search: " f"uuid={uuid} " f"name={real_name}"
        )

        rp.register_player(uuid, real_name)
        register_msg = (
            f"등록되어있지 않은 플레이어네요. {real_name}님을 등록했어요.\n\n"
        )

    # 날짜 검증 정책은 검색 명령에서는 "오늘 허용"을 사용
    target_date: datetime.date | None = cp.parse_date_expression(today)
    date_error: str | None = cv.validate_target_date(target_date)
    if date_error:
        return sm.send(event, date_error)

    if target_date is None:
        return sm.send(event, cv.DATE_INPUT_INVALID_MESSAGE)

    # 레벨 검색이라면 캐릭터 정보 가져오기
    if _type == "레벨":
        logger.info(
            "running level search: "
            f"uuid={uuid} "
            f"period={period_int} "
            f"date={target_date}"
        )

        msg, image_path = gci.get_character_level_info(
            uuid, real_name, period_int, target_date
        )

    # 전투력 검색이라면 전투력 정보 가져오기
    elif _type == "전투력":
        logger.info(
            "running power search: "
            f"uuid={uuid} "
            f"period={period_int} "
            f"date={target_date}"
        )

        msg, image_path = gci.get_character_power_info(
            uuid, real_name, period_int, target_date
        )

    # 레벨 랭킹 검색이라면 레벨 랭킹 변화량 정보 가져오기
    elif _type == "레벨랭킹":
        logger.info(
            "running rank search: "
            f"uuid={uuid} "
            f"period={period_int} "
            f"date={target_date}"
        )

        msg, image_path = gci.get_character_rank_history(
            uuid, name, period_int, target_date, metric="level"
        )

    # 전투력 랭킹 검색이라면 전투력 랭킹 변화량 정보 가져오기
    elif _type == "전투력랭킹":
        logger.info(
            "running power rank search: "
            f"uuid={uuid} "
            f"period={period_int} "
            f"date={target_date}"
        )

        msg, image_path = gci.get_character_rank_history(
            uuid, name, period_int, target_date, metric="power"
        )

    else:
        return sm.send(event, "검색 종류가 올바르지 않습니다.")

    msg: str = register_msg + msg

    return sm.send(event, msg, image=image_path)


def cmd_user_distribution(event: dict, options: list[dict]) -> dict:
    logger.debug(f"cmd_user_distribution options={truncate_text(options, 1000)}")

    date: str = "-1"
    for i in options:
        if i["name"] == "날짜":
            date = i["value"]

    # 유저분포는 "오늘 금지" 정책 사용
    target_date: datetime.date | None = cp.parse_date_expression(date)
    date_error: str | None = cv.validate_target_date(target_date, allow_today=False)
    if date_error:
        return sm.send(event, date_error)

    if target_date is None:
        return sm.send(event, cv.DATE_INPUT_INVALID_MESSAGE)

    msg, image_path = gld.get_level_distribution(target_date)

    logger.info(f"user distribution generated for date={target_date}")

    return sm.send(event, msg, image=image_path)


def cmd_register(event: dict, options: list[dict]) -> dict:
    logger.debug(f"cmd_register options={truncate_text(options, 1000)}")

    name: str | None = None
    for i in options:

        if i["name"] == "닉네임":
            name = i["value"]

    if name is None:
        return sm.send(event, "닉네임을 입력해주세요.")

    real_name, uuid = mps.get_profile_from_name(name)
    if uuid is None or real_name is None:
        return sm.send(
            event, f"플레이어 정보를 가져올 수 없습니다. 닉네임을 확인해주세요."
        )

    rp.register_player(uuid, real_name)

    logger.info("player registered by command: " f"uuid={uuid} " f"name={real_name}")

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
