from decimal import Decimal

import data_manager
from log_utils import get_logger

logger = get_logger(__name__)


def register_player(uuid: str, name: str) -> None:
    """
    플레이어를 등록하는 함수
    """

    logger.info("register_player start: " f"uuid={uuid} " f"name={name}")

    prev = data_manager.manager.get_user_metadata(uuid)
    current_power = prev.get("CurrentPower", Decimal(0)) if prev else Decimal(0)
    current_level = prev.get("CurrentLevel", Decimal(1)) if prev else Decimal(1)

    data_manager.manager.put_user_metadata(
        uuid=uuid,
        name=name,
        current_level=current_level,
        current_power=current_power,
    )
    logger.info(
        "register_player saved metadata: "
        f"uuid={uuid} "
        f"name={name} "
        f"level={current_level} "
        f"power={current_power} "
        f"existed={prev is not None}"
    )


def get_registered_players() -> list[dict]:
    logger.debug("get_registered_players start")

    items: list[dict] = data_manager.manager.scan_all_user_metadata()

    if not items:
        logger.info("get_registered_players: no users found")

        return []

    players = [
        {
            "uuid": data_manager.manager.uuid_from_user_pk(item["PK"]),
            "name": item["Name"],
        }
        for item in items
    ]
    players.sort(key=lambda item: item["name"].lower())

    logger.info("get_registered_players: " f"count={len(players)}")

    return players


def is_registered(uuid: str) -> bool:
    registered = data_manager.manager.get_user_metadata(uuid) is not None

    logger.debug("is_registered: " f"uuid={uuid} " f"registered={registered}")

    return registered


if __name__ == "__main__":
    # print(register_player("asdf123", 1))
    # print(get_registered_players())
    # print(is_registered("prodays123"))
    pass
