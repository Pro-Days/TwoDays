"""Tests for Discord HTTP wrappers and admin API helpers."""

from __future__ import annotations

import unittest
from unittest import mock

from scripts.main.integrations.discord import discord_admin_api as daa
from scripts.main.integrations.discord import discord_client as dc
from tests.support import bootstrap  # noqa: F401


class _FakeResponse:
    def __init__(self, json_value=None, text: str = "", status_code: int = 200) -> None:
        self._json_value = json_value
        self.text = text
        self.status_code = status_code
        self.raise_for_status_called = False

    def json(self):
        if isinstance(self._json_value, Exception):
            raise self._json_value
        return self._json_value

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True


class DiscordHttpAndAdminTest(unittest.TestCase):
    def test_safe_response_body(self) -> None:
        self.assertEqual(
            dc.safe_response_body(_FakeResponse(json_value={"a": 1})), {"a": 1}
        )
        self.assertEqual(
            dc.safe_response_body(
                _FakeResponse(json_value=ValueError("x"), text="raw")
            ),
            "raw",
        )

    def test_patch_json_and_post_json_and_post_multipart(self) -> None:
        patch_resp = _FakeResponse(json_value={"ok": True})
        post_resp = _FakeResponse(json_value={"id": 1})
        multipart_resp = _FakeResponse(json_value=ValueError("bad"), text="fallback")
        delete_resp = _FakeResponse(json_value={"deleted": True})

        with mock.patch(
            "scripts.main.integrations.discord.discord_client.requests.patch",
            return_value=patch_resp,
        ) as patch_mock:
            result = dc.patch_json("u", headers={"A": "B"}, payload={"x": 1})

        self.assertEqual(result.body, {"ok": True})
        patch_mock.assert_called_once()

        with mock.patch(
            "scripts.main.integrations.discord.discord_client.requests.post",
            return_value=post_resp,
        ) as post_mock:
            result2 = dc.post_json("u", headers={"A": "B"}, payload={"x": 1})

        self.assertEqual(result2.body, {"id": 1})
        self.assertEqual(post_mock.call_args.kwargs["headers"], {"A": "B"})

        with mock.patch(
            "scripts.main.integrations.discord.discord_client.requests.post",
            return_value=multipart_resp,
        ) as post_multi_mock:
            result3 = dc.post_multipart("u", multipart_data={"file": b"x"})

        self.assertEqual(result3.body, "fallback")
        self.assertEqual(post_multi_mock.call_args.kwargs["files"], {"file": b"x"})

        with mock.patch(
            "scripts.main.integrations.discord.discord_client.requests.delete",
            return_value=delete_resp,
        ) as delete_mock:
            result4 = dc.delete_json("u", headers={"A": "B"})

        self.assertEqual(result4.body, {"deleted": True})
        delete_mock.assert_called_once()

    def test_discord_admin_api_helpers(self) -> None:
        ip_resp = _FakeResponse(json_value={"ip": "1.2.3.4"})
        guild_name_resp = _FakeResponse(json_value={"name": "Guild"})
        guild_list_resp = _FakeResponse(json_value=[{"id": "1", "name": "G"}])

        with mock.patch(
            "scripts.main.integrations.discord.discord_admin_api.requests.get",
            return_value=ip_resp,
        ) as get_mock:
            self.assertEqual(daa.get_ip(), "1.2.3.4")

        get_mock.assert_called_once()

        with mock.patch.dict("os.environ", {"DISCORD_TOKEN": "token"}, clear=False):
            with mock.patch(
                "scripts.main.integrations.discord.discord_admin_api.requests.get",
                return_value=guild_name_resp,
            ) as get_mock2:
                self.assertEqual(daa.get_guild_name("123"), "Guild")

            self.assertIn("Authorization", get_mock2.call_args.kwargs["headers"])

            with mock.patch(
                "scripts.main.integrations.discord.discord_admin_api.requests.get",
                return_value=guild_list_resp,
            ) as get_mock3:
                self.assertEqual(daa.get_guild_list(), [{"id": "1", "name": "G"}])

            self.assertEqual(get_mock3.call_args.kwargs["timeout"], daa.HTTP_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
