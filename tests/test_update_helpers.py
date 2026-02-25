"""Tests for update job pure helper functions."""

from __future__ import annotations

import datetime
import enum
import importlib
import sys
import types
import unittest
from decimal import Decimal
from unittest import mock

from scripts.main.domain.models import RankRow
from tests.support import bootstrap  # noqa: F401


def _import_update_module():
    modules: dict[str, types.ModuleType] = {}

    modules["scripts.main.features.get_rank_info"] = types.ModuleType(
        "scripts.main.features.get_rank_info"
    )
    modules["scripts.main.features.get_rank_info"].get_current_level_rank_rows = (
        lambda target_date: []
    )
    modules["scripts.main.features.get_rank_info"].get_current_power_rank_rows = (
        lambda target_date: []
    )

    modules["scripts.main.features.register_player"] = types.ModuleType(
        "scripts.main.features.register_player"
    )
    modules["scripts.main.infrastructure.persistence.data_manager"] = types.ModuleType(
        "scripts.main.infrastructure.persistence.data_manager"
    )
    modules["scripts.main.infrastructure.persistence.data_manager"].manager = object()

    sm_module = types.ModuleType("scripts.main.integrations.discord.send_msg")

    class LogType(enum.IntEnum):
        UPDATE = 1
        UPDATE_ERROR = 2

    sm_module.LogType = LogType
    sm_module.send_log = lambda *args, **kwargs: None
    modules["scripts.main.integrations.discord.send_msg"] = sm_module

    modules["scripts.main.services.current_character_provider"] = types.ModuleType(
        "scripts.main.services.current_character_provider"
    )
    modules["scripts.main.integrations.minecraft.minecraft_profile_service"] = (
        types.ModuleType(
            "scripts.main.integrations.minecraft.minecraft_profile_service"
        )
    )
    modules[
        "scripts.main.integrations.minecraft.minecraft_profile_service"
    ].get_profiles_from_mc = lambda names: {}

    with mock.patch.dict(sys.modules, modules):
        sys.modules.pop("scripts.main.jobs.update", None)
        return importlib.import_module("scripts.main.jobs.update")


class UpdateHelpersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.update = _import_update_module()

    def test_phase_result_helpers(self) -> None:
        base = self.update._new_phase_result("rank", total=3)
        self.assertEqual(base["phase"], "rank")
        self.assertEqual(base["total"], 3)
        self.assertEqual(base["success"], 0)

        result = {}
        phase_result = self.update._mark_phase_error(result, "rank", "boom")
        self.assertEqual(result["rank_phase"]["phase_error"], "boom")
        self.assertEqual(phase_result["phase"], "rank")

    def test_update_status_from_result(self) -> None:
        result = {
            "rank_phase": {"success": 2, "failed": 0, "phase_error": None},
            "player_phase": {"success": 1, "failed": 0, "phase_error": None},
        }
        self.update._update_status_from_result(result)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["ok"])

        result2 = {
            "rank_phase": {"success": 1, "failed": 1, "phase_error": None},
            "player_phase": {"success": 0, "failed": 0, "phase_error": None},
        }
        self.update._update_status_from_result(result2)
        self.assertEqual(result2["status"], "partial_failure")
        self.assertFalse(result2["ok"])

        result3 = {
            "rank_phase": {"success": 0, "failed": 0, "phase_error": "x"},
            "player_phase": {"success": 0, "failed": 0, "phase_error": None},
        }
        self.update._update_status_from_result(result3)
        self.assertEqual(result3["status"], "failed")

    def test_build_update_result_message_and_snapshot_date(self) -> None:
        result = {
            "status": "partial_failure",
            "rank_phase": {
                "phase": "rank",
                "success": 1,
                "failed": 1,
                "total": 2,
                "phase_error": None,
                "failures": [{"item": "Steve", "error": "not_found"}],
            },
            "player_phase": {
                "phase": "player",
                "success": 0,
                "failed": 0,
                "total": 0,
                "phase_error": "timeout",
                "failures": [],
            },
        }
        message = self.update._build_update_result_message(result)
        self.assertIn("업데이트 상태: partial_failure", message)
        self.assertIn("rank 실패 항목:", message)
        self.assertIn("player 단계 오류: timeout", message)

        with mock.patch.object(
            self.update,
            "get_today",
            side_effect=lambda days_before=0: datetime.date(2026, 2, 24)
            - datetime.timedelta(days=days_before),
        ):
            self.assertEqual(
                self.update._get_operational_snapshot_date(),
                datetime.date(2026, 2, 23),
            )
            self.assertEqual(
                self.update._get_operational_snapshot_date(days_before=2),
                datetime.date(2026, 2, 21),
            )

    def test_merge_rank_rows(self) -> None:
        level_rows = [
            RankRow(name="Alice", rank=Decimal("1"), level=Decimal("10")),
            RankRow(name="Bob", rank=Decimal("2"), level=Decimal("9")),
        ]
        power_rows = [
            RankRow(name="alice", rank=Decimal("5"), power=Decimal("100")),
            RankRow(name="Chris", rank=Decimal("6"), power=Decimal("90")),
        ]
        ordered_keys, merged = self.update._merge_rank_rows(level_rows, power_rows)
        self.assertEqual(ordered_keys, ["alice", "bob", "chris"])
        self.assertEqual(merged["alice"]["level_rank"], Decimal("1"))
        self.assertEqual(merged["alice"]["power_rank"], Decimal("5"))
        self.assertEqual(merged["bob"]["power"], None)


if __name__ == "__main__":
    unittest.main()
