from decimal import Decimal

import data_manager


def register_player(uuid: str, name: str) -> None:
    """
    플레이어를 등록하는 함수
    """

    prev = data_manager.manager.get_user_metadata(uuid)
    current_power = prev.get("CurrentPower", Decimal(0)) if prev else Decimal(0)
    current_level = prev.get("CurrentLevel", Decimal(1)) if prev else Decimal(1)

    data_manager.manager.put_user_metadata(
        uuid=uuid,
        name=name,
        current_level=current_level,
        current_power=current_power,
    )


def get_registered_players() -> list[dict]:
    items: list[dict] = data_manager.manager.scan_all_user_metadata()

    if not items:
        return []

    players = [
        {
            "uuid": data_manager.manager.uuid_from_user_pk(item["PK"]),
            "name": item["Name"],
        }
        for item in items
    ]
    players.sort(key=lambda item: item["name"].lower())
    return players


def is_registered(uuid: str) -> bool:
    return data_manager.manager.get_user_metadata(uuid) is not None


if __name__ == "__main__":
    # print(register_player("asdf123", 1))
    # print(get_registered_players())
    # print(is_registered("prodays123"))
    pass
