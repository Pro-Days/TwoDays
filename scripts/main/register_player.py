from __future__ import annotations

from typing import TYPE_CHECKING

import data_manager
from log_utils import get_logger
from misc import get_profiles_from_mc

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)


def register_player(uuid: str, name: str) -> None:
    """
    플레이어를 등록하는 함수
    """

    logger.info("register_player start: " f"uuid={uuid} " f"name={name}")

    prev = data_manager.manager.get_user_metadata(uuid)

    data_manager.manager.put_user_metadata(
        uuid=uuid,
        name=name,
    )
    logger.info(
        "register_player saved metadata: "
        f"uuid={uuid} "
        f"name={name} "
        f"existed={prev is not None}"
    )


def get_registered_players() -> list[dict]:
    logger.debug("get_registered_players start")

    items: list[dict] = data_manager.manager.query_all_user_metadata()

    players: list[dict[str, str]] = [
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
    for i in range(10):
        names: list[str] = [f"steve{j:02d}" for j in range(i * 10, (i + 1) * 10)]
        profiles: dict[str, dict[str, str]] = get_profiles_from_mc(names=names)
        for name, profile in profiles.items():
            print(register_player(profile["uuid"], profile["name"]))

    # print(get_registered_players())
    # print(is_registered("prodays123"))
    pass
