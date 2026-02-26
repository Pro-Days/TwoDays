"""Tests for interaction parser helpers."""

from __future__ import annotations

import unittest

from scripts.main.interface import interaction_parsers as ip
from tests.support import bootstrap  # noqa: F401


class InteractionParsersTest(unittest.TestCase):
    def test_resolve_requester_id(self) -> None:
        body = {"member": {"user": {"id": "u1"}}}
        self.assertEqual(ip.resolve_requester_id(body), "u1")

        body2 = {"user": {"id": "u2"}}
        self.assertEqual(ip.resolve_requester_id(body2), "u2")

    def test_resolve_message_target(self) -> None:
        body = {
            "channel_id": "c1",
            "member": {"user": {"id": "u1"}},
            "data": {
                "type": 3,
                "name": "메시지 삭제",
                "target_id": "m1",
                "resolved": {
                    "messages": {
                        "m1": {
                            "id": "m1",
                            "channel_id": "c1",
                            "author": {"id": "app"},
                            "application_id": "app",
                            "interaction": {"user": {"id": "u1"}},
                        }
                    }
                },
            },
        }

        target = ip.resolve_message_target(body)
        self.assertIsNotNone(target)
        self.assertEqual(target.message_id, "m1")
        self.assertEqual(target.channel_id, "c1")
        self.assertEqual(target.author_id, "app")
        self.assertEqual(target.application_id, "app")
        self.assertEqual(target.interaction_user_id, "u1")

    def test_resolve_message_target_missing(self) -> None:
        body = {"data": {"type": 3}}
        self.assertIsNone(ip.resolve_message_target(body))

    def test_can_delete_message(self) -> None:
        target = ip.MessageContextTarget(
            message_id="m1",
            channel_id="c1",
            author_id="app",
            application_id="app",
            interaction_user_id="u1",
        )

        self.assertTrue(ip.can_delete_message("admin", "admin", "app", target))
        self.assertTrue(ip.can_delete_message("u1", "admin", "app", target))
        self.assertFalse(ip.can_delete_message("u2", "admin", "app", target))
        self.assertFalse(ip.can_delete_message(None, "admin", "app", target))
        self.assertFalse(ip.can_delete_message("u1", "admin", None, target))


if __name__ == "__main__":
    unittest.main()
