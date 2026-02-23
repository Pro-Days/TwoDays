from __future__ import annotations

import datetime
import random
from decimal import Decimal
from typing import TYPE_CHECKING

from scripts.main.domain.models import CharacterData, PlayerSearchData
from scripts.main.integrations.minecraft.minecraft_profile_service import (
    get_profile_from_name,
)
from scripts.main.shared.utils.log_utils import get_logger
from scripts.main.shared.utils.time_utils import get_today

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)


def _estimate_level(uuid: str, delta_days: int) -> Decimal:
    """
    임시 레벨 계산식
    초반 급성장/후반 완만 성장 곡선에 UUID 기반 고정 편차를 반영해 결정적으로 계산
    """

    LEVEL_START: float = 1.0
    LEVEL_MAX: float = 200.0

    if delta_days <= 0:
        return Decimal(f"{LEVEL_START:.4f}")

    # UUID 기반 시드를 써서 같은 입력이면 항상 같은 결과가 나오도록 고정
    random.seed(uuid[5:])
    min_speed: float = 0.7
    speed: float = min_speed + random.random() * (1 - min_speed)
    random.random()

    level: float = LEVEL_START

    for _ in range(delta_days):
        remaining: float = max(0.0, LEVEL_MAX - level)
        if remaining <= 0:
            break

        # 하루에 한 번씩 하면 최초 격차가 너무 커서 20번으로 나눠서 점진적으로 증가시키도록 함
        total_gain: float = 0.0
        for __ in range(20):
            gain: float = 10 / ((level + 5) ** 0.9) * speed

            total_gain += gain

        total_gain *= random.uniform(0.7, 1.3)
        level = min(LEVEL_MAX, level + total_gain)

    return Decimal(f"{level:.4f}")


def _estimate_power(uuid: str, level: Decimal) -> Decimal:
    """
    임시 전투력 계산식
    레벨 기반 성장 + UUID 기반 편차를 조합해 결정적으로 계산
    """

    seed: int = sum(ord(c) for c in uuid)
    level_f: float = float(level)

    base_power: float = (level_f**3) * 18 + (level_f**2) * 140 + level_f * 700
    uuid_bias: float = 0.9 + ((seed % 31) / 100)
    level_band_bias: float = 0.96 + ((int(level_f * 10) + seed) % 9) / 100

    return Decimal(round(base_power * uuid_bias * level_band_bias))


def get_current_character_data(
    uuid: str,
    target_date: datetime.date | None = None,
) -> CharacterData:
    """
    최신 캐릭터 정보 가져오기
    오픈 이전에는 임의로 생성해서 반환
    target_date가 주어지면 해당 날짜 기준 데이터로 계산
    """

    # 호출자가 날짜를 넘기면 백필/재계산에도 같은 규칙을 재사용할 수 있음
    today: datetime.date = target_date if target_date is not None else get_today()

    # 2026년 2월 1일을 기준
    base_date: datetime.date = datetime.date(2026, 2, 1)

    delta_days: int = (today - base_date).days

    character_data = CharacterData(uuid=uuid, level=Decimal(1.0), date=today)

    character_data.level = _estimate_level(uuid=uuid, delta_days=delta_days)

    character_data.power = _estimate_power(uuid=uuid, level=character_data.level)

    logger.debug(
        "get_current_character_data complete: "
        f"uuid={uuid} "
        f"date={character_data.date} "
        f"level={character_data.level} "
        f"power={character_data.power}",
    )

    return character_data


def get_current_character_data_by_name(
    name: str, target_date: datetime.date | None = None
) -> PlayerSearchData:
    """
    플레이어 검색 기반 최신 캐릭터 정보 가져오기 (이름 기반)

    현재는 임시로 이름 -> UUID -> 임의 데이터 생성 방식
    이후에는 크롤링으로 실제 데이터를 가져오는 방식으로 변경
    """

    logger.info(
        "get_current_character_data_by_name start: "
        f"name={name} "
        f"target_date={target_date}"
    )

    # 이름 해석을 여기서 처리해 update.py가 프로필 조회 세부사항을 몰라도 되게 함
    real_name, uuid = get_profile_from_name(name)

    if not real_name or not uuid:
        logger.warning(
            "get_current_character_data_by_name failed to resolve: " f"name={name}"
        )
        raise ValueError(f"failed to resolve profile from name: {name}")

    data: CharacterData = get_current_character_data(uuid, target_date=target_date)

    result = PlayerSearchData(
        name=real_name,
        level=data.level,
        power=data.power,
    )

    logger.info(
        "get_current_character_data_by_name complete: "
        f"input={name} "
        f"resolved_name={result.name} "
        f"uuid={uuid} "
        f"target_date={target_date} "
        f"level={result.level} "
        f"power={result.power}"
    )

    return result
