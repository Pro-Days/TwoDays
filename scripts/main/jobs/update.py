"""일일 업데이트 파이프라인과 단계별 실패 집계를 담당한다."""

from __future__ import annotations

import traceback
from datetime import date
from typing import TYPE_CHECKING, Any

import scripts.main.features.get_rank_info as gri
import scripts.main.features.register_player as rp
import scripts.main.infrastructure.persistence.data_manager as dm
import scripts.main.integrations.discord.send_msg as sm
import scripts.main.services.current_character_provider as ccp
from scripts.main.integrations.minecraft.minecraft_profile_service import (
    get_profiles_from_mc,
)
from scripts.main.shared.utils.log_utils import get_logger, truncate_text
from scripts.main.shared.utils.time_utils import get_today

if TYPE_CHECKING:
    from logging import Logger

    from scripts.main.domain.models import PlayerSearchData, RankRow

logger: Logger = get_logger(__name__)


def _safe_send_update_log(log_type: sm.LogType, event: dict[str, Any], message: str) -> None:
    try:
        sm.send_log(log_type, event, message)

    except Exception:
        logger.exception(
            "update log send failed: "
            f"log_type={log_type} "
            f"message={truncate_text(message, 300)}"
        )


def _new_phase_result(phase: str, total: int = 0) -> dict[str, Any]:
    """업데이트 단계 결과 초기화"""

    return {
        "phase": phase,
        "total": total,
        "success": 0,
        "failed": 0,
        "failures": [],
        "phase_error": None,
    }


def _mark_phase_error(
    result: dict[str, Any],
    phase: str,
    error: str,
) -> dict[str, Any]:
    """업데이트 단계 오류 표시"""

    phase_result: dict[str, Any] = _new_phase_result(phase=phase)
    phase_result["phase_error"] = error

    result[f"{phase}_phase"] = phase_result

    return phase_result


def _update_status_from_result(result: dict[str, Any]) -> None:
    """업데이트 결과에서 전체 상태 계산 및 업데이트"""

    rank_phase: dict[str, Any] = result["rank_phase"]
    player_phase: dict[str, Any] = result["player_phase"]

    # 각 단계의 결과를 종합하여 전체 업데이트 상태 결정
    phase_results: list[dict[str, Any]] = [rank_phase, player_phase]

    has_phase_error: bool = any(p.get("phase_error") for p in phase_results)

    item_failure_count: int = sum(int(p.get("failed", 0)) for p in phase_results)

    success_count: int = sum(int(p.get("success", 0)) for p in phase_results)

    result["item_failure_count"] = item_failure_count
    result["has_phase_error"] = has_phase_error

    # 단계 오류가 없고 실패 항목이 없는 경우
    if not has_phase_error and item_failure_count == 0:
        result["status"] = "success"
        result["ok"] = True

    # 단계 오류는 없지만 실패 항목이 있는 경우
    elif success_count > 0:
        result["status"] = "partial_failure"
        result["ok"] = False

    # 단계 오류가 있는 경우
    else:
        result["status"] = "failed"
        result["ok"] = False


def _build_update_result_message(result: dict[str, Any]) -> str:
    """업데이트 결과 메시지 생성"""

    rank_phase: dict[str, Any] = result["rank_phase"]
    player_phase: dict[str, Any] = result["player_phase"]

    lines: list[str] = [
        f"업데이트 상태: {result['status']}",
        (
            "랭킹 단계: "
            f"성공 {rank_phase['success']}, 실패 {rank_phase['failed']}, 총 {rank_phase['total']}"
        ),
        (
            "플레이어 단계: "
            f"성공 {player_phase['success']}, 실패 {player_phase['failed']}, 총 {player_phase['total']}"
        ),
    ]

    for phase_result in (rank_phase, player_phase):

        # 단계 오류가 있는 경우 오류 메시지 추가
        phase_error: str | None = phase_result.get("phase_error")
        if phase_error:
            lines.append(f"{phase_result['phase']} 단계 오류: {phase_error}")

        # 실패 항목이 있는 경우 실패 항목 메시지 추가
        failures: list[dict[str, str]] = phase_result.get("failures", [])
        if failures:
            sample: str = ", ".join(
                f"{item.get('item', '?')} ({item.get('error', 'unknown')})"
                for item in failures
            )
            lines.append(
                f"{phase_result['phase']} 실패 항목: {sample} (총 {len(failures)}개)"
            )

    return "\n".join(lines)


def _get_operational_snapshot_date(days_before: int = 0) -> date:
    """
    업데이트 스냅샷 날짜
    KST 기준 현재 수집 데이터는 항상 어제 데이터로 저장
    """

    # KST 어제
    return get_today(days_before + 1)


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


def _update_rank_phase(snapshot_date: date) -> dict[str, Any]:
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
    phase_result: dict[str, Any] = _new_phase_result("rank", total=len(ordered_keys))

    names: list[str] = [str(merged_rows[key]["name"]) for key in ordered_keys]

    resolved_profiles: dict[str, dict[str, str]] = {}
    unresolved_names: list[str] = []

    # 랭킹 이름을 PK-UUID 매핑으로 우선 조회
    for raw_name in names:
        try:
            metadata: dict[str, str] | None = dm.manager.find_user_metadata_by_name(
                raw_name
            )

        except Exception:
            logger.exception(
                "rank metadata lookup failed, fallback to Mojang: " f"name={raw_name}"
            )
            unresolved_names.append(raw_name)

            continue

        if not metadata:
            unresolved_names.append(raw_name)
            continue

        real_name: str = metadata["Name"]
        pk: str = metadata["PK"]
        uuid: str = dm.manager.uuid_from_user_pk(pk)

        if not real_name or not uuid:
            unresolved_names.append(raw_name)
            continue

        resolved_profiles[raw_name] = {"uuid": uuid, "name": real_name}

    # PK-UUID 매핑에도 없는 이름은 Mojang API로 조회 시도
    if unresolved_names:
        try:
            resolved_profiles.update(get_profiles_from_mc(unresolved_names))

        except Exception:
            logger.exception("bulk profile lookup failed for unresolved rank names")

    # 병합된 랭킹 데이터를 순회하며 스냅샷 저장
    for key in ordered_keys:
        entry: dict[str, Any] = merged_rows[key]
        raw_name = str(entry["name"])

        try:
            profile: dict[str, str] | None = resolved_profiles.get(raw_name)

            real_name = profile["name"] if profile else raw_name
            uuid: str = profile["uuid"] if profile else ""

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
            phase_result["success"] += 1

        except Exception as exc:
            logger.exception(
                "update_1D rank item failed: "
                f"target_date={snapshot_date} "
                f"name={raw_name}"
            )

            phase_result["failed"] += 1
            phase_result["failures"].append({"item": raw_name, "error": str(exc)})

            continue

    logger.info(
        "update_1D rank phase complete: "
        f"target_date={snapshot_date} "
        f"merged_rows={len(ordered_keys)} "
        f"success={phase_result['success']} "
        f"failed={phase_result['failed']}"
    )

    return phase_result


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

    data: PlayerSearchData = ccp.get_current_character_data_by_name(
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


def _update_player_phase(snapshot_date: date) -> dict[str, Any]:
    players: list[dict[str, str]] = rp.get_registered_players()

    phase_result: dict[str, Any] = _new_phase_result("player", total=len(players))

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

        try:
            update_player(uuid, name, snapshot_date=snapshot_date)
            phase_result["success"] += 1

        except Exception as exc:
            logger.exception(
                "update_1D player item failed: "
                f"target_date={snapshot_date} "
                f"uuid={uuid} "
                f"name={name}"
            )

            phase_result["failed"] += 1
            phase_result["failures"].append(
                {"item": f"{name} ({uuid})", "error": str(exc)}
            )

            continue

    logger.info(
        "update_1D player phase complete: "
        f"success={phase_result['success']} "
        f"failed={phase_result['failed']}"
    )

    return phase_result


def _run_update_pipeline(
    event: dict[str, Any],
    snapshot_date: date,
    send_discord_log: bool = True,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "snapshot_date": str(snapshot_date),
        "rank_phase": _new_phase_result("rank"),
        "player_phase": _new_phase_result("player"),
        "status": "failed",
        "ok": False,
        "item_failure_count": 0,
        "has_phase_error": False,
    }

    logger.info(
        "update_1D start: "
        f"action={event.get('action')} "
        f"target_date={snapshot_date}"
    )

    # 랭킹 업데이트
    try:
        result["rank_phase"] = _update_rank_phase(snapshot_date)

    except Exception:
        logger.exception("update_1D rank phase failed")

        phase_error: str = traceback.format_exc()
        _mark_phase_error(
            result,
            "rank",
            truncate_text(phase_error.replace("\n", "\\n"), max_length=500),
        )

        if send_discord_log:
            _safe_send_update_log(
                sm.LogType.UPDATE_ERROR,
                event,
                "랭킹 데이터 업데이트 실패\n" + phase_error,
            )

    # 랭킹 단계에서 신규 등록된 플레이어가 포함되도록 재조회 후 플레이어 업데이트
    try:
        result["player_phase"] = _update_player_phase(snapshot_date)

    except Exception:
        logger.exception("update_1D player phase failed")

        phase_error = traceback.format_exc()
        _mark_phase_error(
            result,
            "player",
            truncate_text(phase_error.replace("\n", "\\n"), max_length=500),
        )

        if send_discord_log:
            _safe_send_update_log(
                sm.LogType.UPDATE_ERROR,
                event,
                "플레이어 데이터 업데이트 실패\n" + phase_error,
            )

    # 전체 업데이트 상태 계산 및 업데이트
    _update_status_from_result(result)
    result_message: str = _build_update_result_message(result)

    logger.info(
        "update_1D complete: "
        f"action={event.get('action')} "
        f"target_date={snapshot_date} "
        f"status={result['status']} "
        f"rank_failed={result['rank_phase']['failed']} "
        f"player_failed={result['player_phase']['failed']}"
    )

    if send_discord_log:
        if result["ok"]:
            _safe_send_update_log(sm.LogType.UPDATE, event, "데이터 업데이트 완료")
        else:
            _safe_send_update_log(sm.LogType.UPDATE_ERROR, event, result_message)

    return result


def update_1D(event: dict[str, Any]) -> dict[str, Any]:
    """
    정기 업데이트
    항상 KST 기준 어제 날짜 스냅샷으로 저장
    """

    event_copy: dict[str, Any] = dict(event)

    snapshot_date: date = _get_operational_snapshot_date()

    return _run_update_pipeline(event_copy, snapshot_date)


def update_1D_backfill(event: dict[str, Any], snapshot_date: date) -> dict[str, Any]:
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

    return _run_update_pipeline(event_copy, snapshot_date, send_discord_log=False)


if __name__ == "__main__":

    for i in range(1, 23):
        update_1D_backfill({"action": "update_1D"}, snapshot_date=date(2026, 2, i))

        print(f"Backfill complete for date: {date(2026, 2, i)}")
