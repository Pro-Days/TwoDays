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
        rankdata = gri.get_current_rank_data()

        logger.info("update_1D rank phase start: " f"rank_count={len(rankdata)}")

        failed_list = []
        for rank, character in enumerate(rankdata, start=1):
            try:
                snapshot = dm.manager.get_user_snapshot(character.uuid, today)
                name = misc.get_name_from_uuid(character.uuid)

                if name is None:
                    name = (
                        snapshot.get("Name", character.uuid)
                        if snapshot
                        else character.uuid
                    )

                power = snapshot.get("Power", Decimal(0)) if snapshot else Decimal(0)

                dm.manager.put_daily_snapshot(
                    uuid=character.uuid,
                    snapshot_date=today,
                    name=name,
                    level=character.level,
                    power=power,
                    level_rank=Decimal(rank),
                )

            except Exception:
                logger.exception(
                    "update_1D rank write failed (first pass): "
                    f"rank={rank} "
                    f"uuid={getattr(character, 'uuid', None)}"
                )

                failed_list.append((rank, character))

        if failed_list:

            logger.warning(
                "update_1D retrying failed rank writes: " f"count={len(failed_list)}"
            )

            for rank, character in failed_list:
                try:
                    snapshot = dm.manager.get_user_snapshot(character.uuid, today)
                    name = misc.get_name_from_uuid(character.uuid)

                    if name is None:
                        name = (
                            snapshot.get("Name", character.uuid)
                            if snapshot
                            else character.uuid
                        )

                    power = (
                        snapshot.get("Power", Decimal(0)) if snapshot else Decimal(0)
                    )

                    dm.manager.put_daily_snapshot(
                        uuid=character.uuid,
                        snapshot_date=today,
                        name=name,
                        level=character.level,
                        power=power,
                        level_rank=Decimal(rank),
                    )

                except Exception:

                    logger.exception(
                        "update_1D rank write failed (retry): "
                        f"rank={rank} "
                        f"uuid={getattr(character, 'uuid', None)}"
                    )

                    sm.send_log(
                        5,
                        event,
                        f"랭킹 데이터 업데이트 실패: {character}"
                        + traceback.format_exc(),
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

        metadata = dm.manager.get_user_metadata(uuid)
        current_power = (
            metadata.get("CurrentPower", Decimal(0)) if metadata else Decimal(0)
        )

        dm.manager.put_daily_snapshot(
            uuid=uuid,
            snapshot_date=today,
            name=name,
            level=data.level,
            power=current_power,
        )

        dm.manager.put_user_metadata(
            uuid=uuid,
            name=name,
            current_level=data.level,
            current_power=current_power,
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

            metadata = dm.manager.get_user_metadata(uuid)

            current_power = (
                metadata.get("CurrentPower", Decimal(0)) if metadata else Decimal(0)
            )

            dm.manager.put_daily_snapshot(
                uuid=uuid,
                snapshot_date=today,
                name=name,
                level=data.level,
                power=current_power,
            )

            dm.manager.put_user_metadata(
                uuid=uuid,
                name=name,
                current_level=data.level,
                current_power=current_power,
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
