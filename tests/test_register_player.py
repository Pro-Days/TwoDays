"""Tests for player registration feature."""

from __future__ import annotations

import unittest
from unittest import mock

from scripts.main.features import register_player as rp
from tests.support import bootstrap  # noqa: F401


class _FakeManager:
    def __init__(self) -> None:
        self.saved: list[dict[str, str]] = []
        self.metadata_map: dict[str, dict] = {}
        self.items: list[dict] = []

    def get_user_metadata(self, uuid: str):
        return self.metadata_map.get(uuid)

    def put_user_metadata(self, uuid: str, name: str) -> None:
        self.saved.append({"uuid": uuid, "name": name})
        self.metadata_map[uuid] = {"PK": f"USER#{uuid}", "Name": name}

    def query_all_user_metadata(self):
        return self.items

    def uuid_from_user_pk(self, pk: str) -> str:
        return pk.removeprefix("USER#")


class RegisterPlayerTest(unittest.TestCase):
    def test_register_player_saves_metadata(self) -> None:
        fake_manager = _FakeManager()
        with mock.patch.object(rp.data_manager, "manager", fake_manager):
            rp.register_player("uuid-1", "Alice")
        self.assertEqual(fake_manager.saved, [{"uuid": "uuid-1", "name": "Alice"}])

    def test_get_registered_players_sorts_and_maps(self) -> None:
        fake_manager = _FakeManager()
        fake_manager.items = [
            {"PK": "USER#u2", "Name": "bravo"},
            {"PK": "USER#u1", "Name": "Alpha"},
        ]
        with mock.patch.object(rp.data_manager, "manager", fake_manager):
            result = rp.get_registered_players()
        self.assertEqual(
            result,
            [{"uuid": "u1", "name": "Alpha"}, {"uuid": "u2", "name": "bravo"}],
        )

    def test_is_registered(self) -> None:
        fake_manager = _FakeManager()
        fake_manager.metadata_map["u1"] = {"PK": "USER#u1", "Name": "A"}
        with mock.patch.object(rp.data_manager, "manager", fake_manager):
            self.assertTrue(rp.is_registered("u1"))
            self.assertFalse(rp.is_registered("u2"))


if __name__ == "__main__":
    unittest.main()
