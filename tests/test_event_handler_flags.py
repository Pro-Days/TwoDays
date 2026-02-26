"""Tests for discord event handler flags."""

from __future__ import annotations

import unittest

from tests.support import bootstrap  # noqa: F401
from scripts.discord_event_handler import lambda_function as lf


class EventHandlerFlagsTest(unittest.TestCase):
    def test_message_context_menu_flag(self) -> None:
        body = {"data": {"type": 3}}
        self.assertEqual(lf._resolve_interaction_flags(body), 192)

    def test_ephemeral_option_flag(self) -> None:
        body = {
            "data": {
                "type": 1,
                "options": [
                    {
                        "name": "레벨",
                        "options": [
                            {"name": "나만보기", "value": True},
                        ],
                    }
                ],
            }
        }

        self.assertEqual(lf._resolve_interaction_flags(body), 192)


if __name__ == "__main__":
    unittest.main()
