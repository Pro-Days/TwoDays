import misc
import data_manager


def register_player(name, slot):

    profile = misc.get_profile_from_mc(name)

    if profile is None:
        return False

    uuid = profile["id"]
    name = profile["name"]

    item = data_manager.read_data("TA_DEV-Users", "uuid-index", {"uuid": uuid})

    if item is None:  # 등록되지 않은 플레이어
        data_manager.write_data(
            "TA_DEV-Users",
            {
                "id": misc.get_max_id() + 1,
                "name": name,
                "mainSlot": slot,
                "uuid": uuid,
                "lower_name": name.lower(),
            },
        )
    else:  # 등록된 플레이어 (mainSlot만 변경 or 닉네임 변경)
        data_manager.write_data(
            "TA_DEV-Users",
            {
                "id": item[0]["id"],
                "name": name,
                "mainSlot": slot,
                "uuid": uuid,
                "lower_name": name.lower(),
            },
        )

    return True


def get_registered_players():
    items = data_manager.scan_data("TA_DEV-Users")

    for item in items:
        del item["lower_name"]

    return items


def is_registered(name):
    items = data_manager.read_data("TA_DEV-Users", "lower_name-index", {"lower_name": name.lower()})

    return items is not None


if __name__ == "__main__":
    # register_player("asdf123", 1)
    # print(get_registered_players())
    pass
