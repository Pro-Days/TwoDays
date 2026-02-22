from __future__ import annotations

import traceback
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import data_manager as dm
import get_character_info as gci
import get_rank_info as gri
import misc
import register_player as rp
import send_msg as sm
from log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

    from models import CharacterData

logger: Logger = get_logger(__name__)


def update_1D(event, days_before: int = 0):
    """
    플레이어, 랭킹 업데이트
    """

    today: date = misc.get_today(days_before + 1)

    logger.info(
        "update_1D start: " f"action={event.get('action')} " f"target_date={today}"
    )

    # 플레이어 업데이트
    try:
        players = rp.get_registered_players()

        logger.info("update_1D player phase start: " f"count={len(players)}")

        for idx, player in enumerate(players, start=1):
            logger.debug(
                "update_1D player update progress: "
                f"{idx}/{len(players)} "
                f"uuid={player.get('uuid')} "
                f"name={player.get('name')}"
            )

            update_player(event, player["uuid"], player["name"])

            # 쓰레드로 업데이트
            # t = threading.Thread(target=update_player, args=(event, player["name"], player["id"]))
            # t.start()
            # t.join()

            # 10 players/sec: 1000 players -> 100 sec
            # time.sleep(0.1)

        logger.info("update_1D player phase complete")

    except Exception:
        logger.exception("update_1D player phase failed")

        sm.send_log(5, event, "플레이어 데이터 업데이트 실패" + traceback.format_exc())

    # 랭커 등록, 업데이트
    try:
        level_rank_data: list[CharacterData] = gri.get_current_rank_data(metric="level")
        power_rank_data: list[CharacterData] = gri.get_current_rank_data(metric="power")

        logger.info(
            "update_1D rank phase start: "
            f"level_rank_count={len(level_rank_data)} "
            f"power_rank_count={len(power_rank_data)}"
        )

        level_rank_map: dict[str, Decimal] = {
            character.uuid: Decimal(rank)
            for rank, character in enumerate(level_rank_data, start=1)
        }
        power_rank_map: dict[str, Decimal] = {
            character.uuid: Decimal(rank)
            for rank, character in enumerate(power_rank_data, start=1)
        }

        character_map: dict[str, CharacterData] = {}
        ordered_uuids: list[str] = []

        for character in level_rank_data + power_rank_data:
            if character.uuid in character_map:
                continue

            character_map[character.uuid] = character
            ordered_uuids.append(character.uuid)

        failed_list: list[str] = []
        for uuid in ordered_uuids:
            try:
                character: CharacterData = character_map[uuid]
                snapshot = dm.manager.get_user_snapshot(uuid, today)
                name = misc.get_name_from_uuid(uuid)

                if name is None:
                    name = snapshot.get("Name", uuid) if snapshot else uuid

                snapshot_level = (
                    snapshot.get("Level") if snapshot and "Level" in snapshot else None
                )
                snapshot_power = (
                    snapshot.get("Power") if snapshot and "Power" in snapshot else None
                )

                level = (
                    snapshot_level
                    if snapshot_level is not None
                    else getattr(character, "level", Decimal(0))
                )
                power = (
                    snapshot_power
                    if snapshot_power is not None
                    else getattr(character, "power", Decimal(0))
                )

                dm.manager.put_daily_snapshot(
                    uuid=uuid,
                    snapshot_date=today,
                    name=name,
                    level=level,
                    power=power,
                    level_rank=level_rank_map.get(uuid),
                    power_rank=power_rank_map.get(uuid),
                )

            except Exception:
                logger.exception(
                    "update_1D rank write failed (first pass): "
                    f"uuid={uuid} "
                    f"level_rank={level_rank_map.get(uuid)} "
                    f"power_rank={power_rank_map.get(uuid)}"
                )

                failed_list.append(uuid)

        if failed_list:

            logger.warning(
                "update_1D retrying failed rank writes: " f"count={len(failed_list)}"
            )

            for uuid in failed_list:
                try:
                    character = character_map[uuid]
                    snapshot = dm.manager.get_user_snapshot(uuid, today)
                    name = misc.get_name_from_uuid(uuid)

                    if name is None:
                        name = snapshot.get("Name", uuid) if snapshot else uuid

                    snapshot_level = (
                        snapshot.get("Level")
                        if snapshot and "Level" in snapshot
                        else None
                    )
                    snapshot_power = (
                        snapshot.get("Power")
                        if snapshot and "Power" in snapshot
                        else None
                    )

                    level = (
                        snapshot_level
                        if snapshot_level is not None
                        else getattr(character, "level", Decimal(0))
                    )
                    power = (
                        snapshot_power
                        if snapshot_power is not None
                        else getattr(character, "power", Decimal(0))
                    )

                    dm.manager.put_daily_snapshot(
                        uuid=uuid,
                        snapshot_date=today,
                        name=name,
                        level=level,
                        power=power,
                        level_rank=level_rank_map.get(uuid),
                        power_rank=power_rank_map.get(uuid),
                    )

                except Exception:

                    logger.exception(
                        "update_1D rank write failed (retry): "
                        f"uuid={uuid} "
                        f"level_rank={level_rank_map.get(uuid)} "
                        f"power_rank={power_rank_map.get(uuid)}"
                    )

                    sm.send_log(
                        5,
                        event,
                        f"랭킹 데이터 업데이트 실패: {uuid}" + traceback.format_exc(),
                    )

        logger.info("update_1D rank phase complete")

    except Exception:
        logger.exception("update_1D rank phase failed")

        sm.send_log(5, event, "랭킹 데이터 업데이트 실패" + traceback.format_exc())

    logger.info("update_1D complete")

    sm.send_log(4, event, "데이터 업데이트 완료")


def update_player(event, uuid, name):
    days_before = event.get("days_before", 0)

    failed_list = []
    today = misc.get_today(days_before + 1)

    logger.debug(
        "update_player start: "
        f"uuid={uuid} "
        f"name={name} "
        f"days_before={days_before} "
        f"target_date={today}"
    )

    try:
        data = gci.get_current_character_data(uuid, days_before + 1)

        dm.manager.put_daily_snapshot(
            uuid=uuid,
            snapshot_date=today,
            name=name,
            level=data.level,
            power=data.power,
        )

        dm.manager.put_user_metadata(
            uuid=uuid,
            name=name,
        )

        logger.debug("update_player success: " f"uuid={uuid} " f"level={data.level}")

    except Exception:

        logger.exception(
            "update_player failed (first pass): " f"uuid={uuid} " f"name={name}"
        )

        failed_list.append(name)

    if failed_list:
        try:
            data = gci.get_current_character_data(uuid, days_before + 1)

            dm.manager.put_daily_snapshot(
                uuid=uuid,
                snapshot_date=today,
                name=name,
                level=data.level,
                power=data.power,
            )

            dm.manager.put_user_metadata(
                uuid=uuid,
                name=name,
            )

            logger.info("update_player retry success: " f"uuid={uuid} " f"name={name}")

        except Exception:

            logger.exception(
                "update_player failed (retry): " f"uuid={uuid} " f"name={name}"
            )

            sm.send_log(
                5, event, f"{name} 데이터 업데이트 실패" + traceback.format_exc()
            )


if __name__ == "__main__":
    update_1D({"action": "update_1D"})
    pass
