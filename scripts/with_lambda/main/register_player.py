import misc
import data_manager


def register_player(name, slot):
    """
    등록 안된 플레이어 등록
    등록 된 플레이어 mainSlot 변경
    등록 된 닉네임 변경한 플레이어 닉네임 변경
    """

    profile = misc.get_profile_from_mc(name=name)

    if profile is None:
        return -1

    uuid = profile[name]["uuid"]
    name = profile[name]["name"]

    item = data_manager.read_data("Users", "uuid-index", {"uuid": uuid})

    if item is None:  # 등록되지 않은 플레이어
        data_manager.write_data(
            "Users",
            {
                "id": misc.get_max_id() + 1,
                "name": name,
                "mainSlot": slot,
                "uuid": uuid,
                "lower_name": name.lower(),
            },
        )

        return 1

    else:  # 등록된 플레이어 (mainSlot만 변경 or 닉네임 변경)
        data_manager.write_data(
            "Users",
            {
                "id": item[0]["id"],
                "name": name,
                "mainSlot": slot,
                "uuid": uuid,
                "lower_name": name.lower(),
            },
        )

        return 2


def get_registered_players():
    items = data_manager.scan_data("Users")

    if items is None:
        return list()

    for item in items:
        del item["lower_name"]

    return items


def is_registered(name):
    items = data_manager.read_data(
        "Users", "lower_name-index", {"lower_name": name.lower()}
    )

    return items is not None


if __name__ == "__main__":
    # print(register_player("asdf123", 1))
    # print(get_registered_players())
    # print(is_registered("prodays123"))
    pass
