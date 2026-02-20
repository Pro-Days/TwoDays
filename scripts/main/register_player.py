from typing import Literal

import data_manager
import misc


def register_player(uuid: str, name: str) -> None:
    """
    플레이어를 등록하는 함수
    """

    data_manager.write_data(
        "Users",
        {
            "name": name,
            "uuid": uuid,
            "lower_name": name.lower(),
        },
    )


def get_registered_players() -> list[dict]:
    items: list[dict] = data_manager.scan_data("Users")

    if not items:
        return []

    for item in items:
        del item["lower_name"]

    return items


def is_registered(uuid: str) -> bool:
    items: list[dict] = data_manager.read_data("Users", "uuid-index", {"uuid": uuid})

    return bool(items)


if __name__ == "__main__":
    # print(register_player("asdf123", 1))
    # print(get_registered_players())
    # print(is_registered("prodays123"))
    pass
