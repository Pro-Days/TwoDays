"""Tests for Discord log payload formatter."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from scripts.main.integrations.discord import discord_log_formatter as dlf
from tests.support import bootstrap  # noqa: F401


class DiscordLogFormatterTest(unittest.TestCase):
    def test_build_fields_and_command_text(self) -> None:
        fields = dlf._build_fields({"a": "1", "b": None})
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0]["name"], "a")

        self.assertIsNone(dlf._command_text({}))
        self.assertEqual(dlf._command_text({"data": {"name": "랭킹"}}), "랭킹")
        self.assertIn(
            "기간", dlf._command_text({"data": {"name": "랭킹", "options": ["기간"]}})
        )

    def test_build_log_payload_command_server(self) -> None:
        event_body = {
            "authorizing_integration_owners": {"0": "guild-owner"},
            "guild_id": "guild-1",
            "channel": {"id": "ch-1", "name": "general"},
            "member": {
                "user": {"id": "u1", "username": "user1", "global_name": "User One"}
            },
            "data": {"name": "랭킹", "options": [{"name": "기간", "value": 7}]},
        }
        event = {"body": json.dumps(event_body, ensure_ascii=False)}

        with mock.patch(
            "scripts.main.integrations.discord.discord_log_formatter.time.time",
            return_value=1700000000,
        ):
            with mock.patch(
                "scripts.main.integrations.discord.discord_log_formatter.daa.get_guild_name",
                return_value="My Guild",
            ) as guild_mock:
                payload = dlf.build_log_payload(
                    dlf.LogType.COMMAND, event, "ok", admin_id="admin"
                )

        guild_mock.assert_called_once_with("guild-1")
        self.assertEqual(payload["content"], "")
        embed = payload["embeds"][0]
        self.assertEqual(embed["title"], "투데이즈 명령어 로그")
        names = [field["name"] for field in embed["fields"]]
        self.assertIn("server", names)
        self.assertIn("cmd", names)

    def test_build_log_payload_error_and_invalid_json(self) -> None:
        invalid_event = {"body": "{invalid"}
        with mock.patch(
            "scripts.main.integrations.discord.discord_log_formatter.time.time",
            return_value=1700000000,
        ):
            payload = dlf.build_log_payload(
                dlf.LogType.COMMAND_ERROR,
                invalid_event,
                "boom",
                admin_id="admin-1",
            )
        self.assertEqual(payload["content"], "<@admin-1>")
        fields = payload["embeds"][0]["fields"]
        field_map = {f["name"]: f["value"] for f in fields}
        self.assertEqual(field_map["error"], "boom")

    def test_build_log_payload_update_types(self) -> None:
        event = {"action": "update_1D"}
        payload = dlf.build_log_payload(
            dlf.LogType.UPDATE_ERROR, event, "failed", admin_id="adm"
        )
        self.assertEqual(payload["content"], "<@adm>")
        self.assertEqual(
            payload["embeds"][0]["title"], "투데이즈 데이터 업데이트 에러 로그"
        )


if __name__ == "__main__":
    unittest.main()
