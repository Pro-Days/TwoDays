"""Tests for shared utils and domain models."""

from __future__ import annotations

import datetime
import logging
import unittest
from decimal import Decimal
from unittest import mock

from scripts.main.domain.game_progression import get_exp_data
from scripts.main.domain.models import (
    CharacterData,
    MetricRankEntry,
    PlayerSearchData,
    RankRow,
)
from scripts.main.shared.utils import log_utils, path_utils, time_utils
from tests.support import bootstrap  # noqa: F401


class _FixedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz: datetime.tzinfo | None = None) -> "_FixedDateTime":
        base = datetime.datetime(2026, 2, 24, 0, 30, tzinfo=datetime.timezone.utc)
        if tz is None:
            return cls.fromtimestamp(base.timestamp())
        return cls.fromtimestamp(base.timestamp(), tz=tz)


class SharedUtilsAndDomainTest(unittest.TestCase):
    def test_get_today_uses_kst_and_days_before(self) -> None:
        with mock.patch(
            "scripts.main.shared.utils.time_utils.datetime.datetime",
            _FixedDateTime,
        ):
            self.assertEqual(time_utils.get_today(), datetime.date(2026, 2, 24))
            self.assertEqual(
                time_utils.get_today(days_before=1), datetime.date(2026, 2, 23)
            )

    def test_convert_path_by_platform(self) -> None:
        with mock.patch(
            "scripts.main.shared.utils.path_utils.platform.system",
            return_value="Windows",
        ):
            with mock.patch(
                "scripts.main.shared.utils.path_utils.os.path.normpath",
                side_effect=lambda value: value,
            ):
                self.assertEqual(path_utils.convert_path("a/b/c"), "a\\b\\c")

        with mock.patch(
            "scripts.main.shared.utils.path_utils.platform.system", return_value="Linux"
        ):
            with mock.patch(
                "scripts.main.shared.utils.path_utils.os.path.normpath",
                side_effect=lambda value: value,
            ):
                self.assertEqual(path_utils.convert_path("a\\b\\c"), "a/b/c")

    def test_log_utils_helpers(self) -> None:
        with mock.patch.dict("os.environ", {"TWODAYS_LOG_LEVEL": "debug"}, clear=False):
            self.assertEqual(log_utils._resolve_level(None), logging.DEBUG)

        self.assertEqual(log_utils._resolve_level(logging.WARNING), logging.WARNING)
        self.assertEqual(log_utils.truncate_text("abc", 5), "abc")

        truncated = log_utils.truncate_text("abcdef", 3)
        self.assertIn("... (truncated 3 chars)", truncated)

        self.assertIn('"a": 1', log_utils.to_json({"a": 1}))

        class BadStr:
            def __str__(self) -> str:
                return "bad"

        with mock.patch(
            "scripts.main.shared.utils.log_utils.json.dumps", side_effect=TypeError
        ):
            self.assertEqual(log_utils.to_json(BadStr()), "bad")

        event = {
            "action": "x",
            "body": '{"data":{"name":"랭킹","options":[1]},"member":{"user":{"id":"1","username":"u"}},"channel":{"id":"2"},"guild_id":"3"}',
        }
        summary = log_utils.summarize_event(event)
        self.assertEqual(summary["action"], "x")
        self.assertEqual(summary["command"], "랭킹")
        self.assertEqual(summary["option_count"], 1)
        self.assertEqual(summary["member_id"], "1")

        invalid_body_summary = log_utils.summarize_event({"body": "not-json"})
        self.assertIn("body", invalid_body_summary)

    def test_game_progression_and_models(self) -> None:
        exp = get_exp_data()
        self.assertEqual(exp[0], 0)
        self.assertEqual(len(exp), 201)
        self.assertTrue(all(exp[i] <= exp[i + 1] for i in range(len(exp) - 1)))

        c = CharacterData(
            uuid="u", level=Decimal("10"), date=datetime.date(2026, 2, 24)
        )
        self.assertEqual(c.power, Decimal(0))
        r = MetricRankEntry(uuid="u", metric="level", value=Decimal("10"))
        self.assertEqual(r.metric, "level")
        p = PlayerSearchData(name="n", level=Decimal("1"), power=Decimal("2"))
        self.assertEqual(p.name, "n")
        row = RankRow(name="n", rank=Decimal("1"))
        self.assertIsNone(row.level)


if __name__ == "__main__":
    unittest.main()
