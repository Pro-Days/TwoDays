from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)


def get_today(days_before: int = 0) -> datetime.date:
    # 프로젝트 전체 기준일을 KST로 통일해 날짜 해석 차이를 방지
    kst_now: datetime.datetime = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=9)
        - datetime.timedelta(days=days_before)
    )
    today_kst: datetime.date = kst_now.date()

    logger.debug("get_today: " f"days_before={days_before} " f"result={today_kst}")

    return today_kst
