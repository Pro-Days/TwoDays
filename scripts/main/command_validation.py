from __future__ import annotations

import datetime

from time_utils import get_today

DATE_INPUT_INVALID_MESSAGE: str = (
    "날짜 입력이 올바르지 않습니다: YYYY-MM-DD, MM-DD, DD, -n "
    "(예시: 2025-12-31, 12-01, 05, -1, -20)"
)

# 파싱과 정책 검증을 분리해 같은 파서 결과를 명령별 정책으로 재사용
FUTURE_DATE_NOT_ALLOWED_MESSAGE: str = "미래 날짜는 조회할 수 없습니다."
TODAY_DATE_NOT_ALLOWED_MESSAGE: str = "오늘 날짜는 조회할 수 없습니다."


def validate_target_date(
    target_date: datetime.date | None,
    *,
    allow_today: bool = True,
) -> str | None:
    # 메시지를 직접 반환해 핸들러에서 분기 로직만 남기도록 함
    if target_date is None:
        return DATE_INPUT_INVALID_MESSAGE

    today: datetime.date = get_today()

    if target_date > today:
        return FUTURE_DATE_NOT_ALLOWED_MESSAGE

    if not allow_today and target_date == today:
        return TODAY_DATE_NOT_ALLOWED_MESSAGE

    return None
