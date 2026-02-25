"""Tests for Minecraft profile service helpers."""

from __future__ import annotations

import unittest
from unittest import mock

from scripts.main.integrations.minecraft import minecraft_profile_service as mps
from tests.support import bootstrap  # noqa: F401


class _FakeManager:
    def __init__(self) -> None:
        self.by_name: dict[str, dict] = {}
        self.by_uuid: dict[str, dict] = {}

    def find_user_metadata_by_name(self, name: str):
        return self.by_name.get(name)

    def get_user_metadata(self, uuid: str):
        return self.by_uuid.get(uuid)

    def uuid_from_user_pk(self, pk: str) -> str:
        return pk.removeprefix("USER#")


class _FakeApi:
    def __init__(self, *args, **kwargs) -> None:
        self.uuid_map: dict[str, str] = {}
        self.name_map: dict[str, str] = {}
        self.uuids_map: dict[tuple[str, ...], dict[str, str]] = {}

    def get_uuid(self, name: str):
        return self.uuid_map.get(name)

    def get_username(self, uuid: str | None):
        if uuid is None:
            return None
        return self.name_map.get(uuid)

    def get_uuids(self, names: list[str]):
        key = tuple(names)
        value = self.uuids_map.get(key)
        if isinstance(value, Exception):
            raise value
        return value or {}


class MinecraftProfileServiceTest(unittest.TestCase):
    def test_get_profile_from_name_uses_metadata_cache(self) -> None:
        fake_manager = _FakeManager()
        fake_manager.by_name["Alice"] = {"Name": "AliceReal", "PK": "USER#uuid-1"}
        with mock.patch.object(mps.data_manager, "manager", fake_manager):
            with mock.patch(
                "scripts.main.integrations.minecraft.minecraft_profile_service.mojang.API"
            ) as api_cls:
                self.assertEqual(
                    mps.get_profile_from_name("Alice"), ("AliceReal", "uuid-1")
                )
        api_cls.assert_not_called()

    def test_get_profile_from_name_falls_back_to_api(self) -> None:
        fake_manager = _FakeManager()
        fake_api = _FakeApi()
        fake_api.uuid_map["Bob"] = "uuid-2"
        fake_api.name_map["uuid-2"] = "BobReal"
        with mock.patch.object(mps.data_manager, "manager", fake_manager):
            with mock.patch(
                "scripts.main.integrations.minecraft.minecraft_profile_service.mojang.API",
                return_value=fake_api,
            ):
                self.assertEqual(
                    mps.get_profile_from_name("Bob"), ("BobReal", "uuid-2")
                )
                self.assertEqual(mps.get_profile_from_name("Unknown"), (None, None))

    def test_get_name_from_uuid_cache_and_api(self) -> None:
        fake_manager = _FakeManager()
        fake_manager.by_uuid["uuid-1"] = {"Name": "Alice"}
        fake_api = _FakeApi()
        fake_api.name_map["uuid-2"] = "Bob"
        with mock.patch.object(mps.data_manager, "manager", fake_manager):
            with mock.patch(
                "scripts.main.integrations.minecraft.minecraft_profile_service.mojang.API",
                return_value=fake_api,
            ):
                self.assertEqual(mps.get_name_from_uuid("uuid-1"), "Alice")
                self.assertEqual(mps.get_name_from_uuid("uuid-2"), "Bob")
                self.assertIsNone(mps.get_name_from_uuid("uuid-3"))

    def test_get_profiles_from_mc_chunks_and_skips_failed_chunk(self) -> None:
        fake_api = _FakeApi()
        first_chunk = tuple([f"name{i}" for i in range(10)])
        second_chunk = ("name10", "name11")
        fake_api.uuids_map[first_chunk] = {
            "Name0": "uuid0",
            "name5": "uuid5",
        }
        fake_api.uuids_map[second_chunk] = RuntimeError("rate limit")

        names = [f"name{i}" for i in range(12)]
        with mock.patch(
            "scripts.main.integrations.minecraft.minecraft_profile_service.mojang.API",
            return_value=fake_api,
        ):
            result = mps.get_profiles_from_mc(names)

        self.assertEqual(result["name0"], {"uuid": "uuid0", "name": "Name0"})
        self.assertEqual(result["name5"], {"uuid": "uuid5", "name": "name5"})
        self.assertNotIn("name10", result)


if __name__ == "__main__":
    unittest.main()
