from __future__ import annotations

import datetime
from dataclasses import dataclass

from time_utils import get_today


@dataclass
class OptionParseError(ValueError):
    # 핸들러에서 사용자 메시지를 결정할 수 있도록 문자열 대신 코드로 전달
    code: str

    def __str__(self) -> str:
        return self.code


def parse_date_expression(day_expression: str | None) -> datetime.date | None:

    if day_expression is None:
        return get_today()

    # 파싱 실패는 예외 대신 None으로 반환해 핸들러 검증 단계와 분리
    try:
        today: datetime.date = get_today()

        # -n 형식: 오늘로부터 n일 전
        if day_expression[0] == "-" and day_expression[1:].isdigit():
            date_offset = int(day_expression[1:])
            today = today - datetime.timedelta(days=date_offset)

        # YYYY-MM-DD, MM-DD, DD 형식
        else:
            date_type: int = day_expression.count("-")
            today_list: list[str] = str(today).split("-")

            # DD
            if date_type == 0:
                day_expression = "-".join(today_list[:2]) + "-" + day_expression

            # MM-DD
            if date_type == 1:
                day_expression = today_list[0] + "-" + day_expression

            today = datetime.datetime.strptime(day_expression, "%Y-%m-%d").date()

    except Exception:
        return None

    return today


def parse_positive_int_option(
    value: int | None,
    *,
    default: int,
    min_value: int = 1,
) -> int:
    # Discord 옵션이 int/str로 섞여 들어와도 동일한 경로로 정규화
    if value is None:
        parsed: int = default

    elif isinstance(value, int):
        parsed = value

    else:
        raise OptionParseError("invalid_number")

    if parsed < min_value:
        raise OptionParseError("too_small")

    return parsed


def parse_rank_range(
    range_str: str,
    *,
    min_rank: int = 1,
    max_rank: int = 100,
) -> tuple[int, int]:
    # 범위 문자열 형식 검증과 숫자 검증을 한 곳에서 처리해 핸들러 분기 중복을 줄임
    normalized: str = range_str.strip()
    range_list: list[str] = normalized.split("..")

    if len(range_list) != 2:
        raise OptionParseError("invalid_format")

    try:
        rank_start, rank_end = map(int, range_list)

    except (TypeError, ValueError) as exc:
        raise OptionParseError("invalid_number") from exc

    if rank_start < min_rank or rank_end > max_rank:
        raise OptionParseError("out_of_bounds")

    if rank_start > rank_end:
        raise OptionParseError("invalid_order")

    return rank_start, rank_end
