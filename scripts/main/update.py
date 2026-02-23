from __future__ import annotations

import traceback
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import data_manager as dm
import get_character_info as gci
import get_rank_info as gri
import misc
import register_player as rp
import send_msg as sm
from log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

    from models import PlayerSearchData, RankRow

logger: Logger = get_logger(__name__)


def _get_operational_snapshot_date() -> date:
    """
    업데이트 스냅샷 날짜
    KST 기준 현재 수집 데이터는 항상 어제 데이터로 저장
    """

    return misc.get_today(1)


def _merge_rank_rows(
    level_rows: list[RankRow], power_rows: list[RankRow]
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """레벨 랭킹과 전투력 랭킹 데이터를 이름 기준으로 병합"""

    merged: dict[str, dict[str, Any]] = {}
    ordered_keys: list[str] = []

    def merge(row: RankRow, metric: str) -> None:
        key: str = row.name.lower()

        if key not in merged:
            merged[key] = {
                "name": row.name,
                "level": None,
                "power": None,
                "level_rank": None,
                "power_rank": None,
            }
            ordered_keys.append(key)

        entry: dict = merged[key]

        entry["name"] = row.name

        if metric == "level":
            entry["level"] = row.level
            entry["level_rank"] = row.rank

        elif metric == "power":
            entry["power"] = row.power
            entry["power_rank"] = row.rank

    for row in level_rows:
        merge(row, "level")

    for row in power_rows:
        merge(row, "power")

    return ordered_keys, merged


def _update_rank_phase(snapshot_date: date) -> None:
    level_rows: list[RankRow] = gri.get_current_level_rank_rows(
        target_date=snapshot_date
    )
    power_rows: list[RankRow] = gri.get_current_power_rank_rows(
        target_date=snapshot_date
    )

    logger.info(
        "update_1D rank phase start: "
        f"target_date={snapshot_date} "
        f"level_rank_count={len(level_rows)} "
        f"power_rank_count={len(power_rows)}"
    )

    # 레벨 랭킹과 전투력 랭킹 데이터를 이름 기준으로 병합
    ordered_keys, merged_rows = _merge_rank_rows(level_rows, power_rows)

    names: list[str] = [str(merged_rows[key]["name"]) for key in ordered_keys]

    # TODO: 이름으로 프로필 조회하는 부분 개선 - METADATA 조회를 우선

    resolved_profiles: dict[str, dict[str, str]] = misc.get_profiles_from_mc(names)

    for key in ordered_keys:
        entry: dict[str, Any] = merged_rows[key]
        raw_name = str(entry["name"])

        profile: dict[str, str] | None = resolved_profiles.get(raw_name)
        real_name: str = profile["name"] if profile else raw_name
        uuid: str | None = profile.get("uuid") if profile else None

        if not uuid or not real_name:
            raise ValueError(f"failed to resolve uuid from rank name: {raw_name}")

        if dm.manager.get_user_metadata(uuid) is None:
            rp.register_player(uuid, real_name)

        dm.manager.put_daily_snapshot(
            uuid=uuid,
            snapshot_date=snapshot_date,
            name=real_name,
            level=entry.get("level"),
            power=entry.get("power"),
            level_rank=entry.get("level_rank"),
            power_rank=entry.get("power_rank"),
        )

    logger.info(
        "update_1D rank phase complete: "
        f"target_date={snapshot_date} "
        f"merged_rows={len(ordered_keys)}"
    )


def update_player(
    uuid: str,
    name: str,
    snapshot_date: date | None = None,
) -> None:

    target_date: date = snapshot_date or _get_operational_snapshot_date()

    logger.debug(
        "update_player start: "
        f"uuid={uuid} "
        f"name={name} "
        f"target_date={target_date}"
    )

    data: PlayerSearchData = gci.get_current_character_data_by_name(
        name, target_date=target_date
    )
    snapshot: dict[str, Any] | None = dm.manager.get_user_snapshot(uuid, target_date)

    dm.manager.put_daily_snapshot(
        uuid=uuid,
        snapshot_date=target_date,
        name=data.name,
        level=data.level,
        power=data.power,
        level_rank=snapshot.get("Level_Rank") if snapshot else None,
        power_rank=snapshot.get("Power_Rank") if snapshot else None,
    )

    logger.debug("update_player success: " f"uuid={uuid} " f"name={name}")


def _update_player_phase(snapshot_date: date) -> None:
    players: list[dict[str, str]] = rp.get_registered_players()

    logger.info(
        "update_1D player phase start: "
        f"target_date={snapshot_date} "
        f"count={len(players)}"
    )

    for idx, player in enumerate(players, start=1):
        uuid: str = player["uuid"]
        name: str = player["name"]

        logger.debug(
            "update_1D player update progress: "
            f"{idx}/{len(players)} "
            f"uuid={uuid} "
            f"name={name}"
        )

        update_player(uuid, name, snapshot_date=snapshot_date)

    logger.info("update_1D player phase complete")


def _run_update_pipeline(event: dict[str, Any], snapshot_date: date) -> None:
    logger.info(
        "update_1D start: "
        f"action={event.get('action')} "
        f"target_date={snapshot_date}"
    )

    # 랭킹 업데이트
    try:
        _update_rank_phase(snapshot_date)

    except Exception:
        logger.exception("update_1D rank phase failed")
        sm.send_log(5, event, "랭킹 데이터 업데이트 실패" + traceback.format_exc())

    # 랭킹 단계에서 신규 등록된 플레이어가 포함되도록 재조회 후 플레이어 업데이트
    try:
        _update_player_phase(snapshot_date)

    except Exception:
        logger.exception("update_1D player phase failed")
        sm.send_log(5, event, "플레이어 데이터 업데이트 실패" + traceback.format_exc())

    logger.info(
        "update_1D complete: "
        f"action={event.get('action')} "
        f"target_date={snapshot_date}"
    )

    sm.send_log(4, event, "데이터 업데이트 완료")


def update_1D(event: dict[str, Any]) -> None:
    """
    정기 업데이트
    항상 KST 기준 어제 날짜 스냅샷으로 저장
    """

    event_copy: dict[str, Any] = dict(event)

    snapshot_date: date = _get_operational_snapshot_date()

    _run_update_pipeline(event_copy, snapshot_date)


def update_1D_backfill(event: dict[str, Any], snapshot_date: date) -> None:
    """
    개발용 과거 날짜 저장
    특정 날짜의 스냅샷을 저장하려는 경우 사용
    """

    event_copy: dict[str, Any] = dict(event)
    event_copy.setdefault("action", "update_1D_backfill")

    logger.info(
        "update_1D_backfill start: "
        f"target_date={snapshot_date} "
        f"source=current_crawled_data"
    )

    _run_update_pipeline(event_copy, snapshot_date)


if __name__ == "__main__":
    update_1D_backfill(
        {"action": "update_1D"}, snapshot_date=_get_operational_snapshot_date()
    )
