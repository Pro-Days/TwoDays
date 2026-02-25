"""Tests for command parser helpers."""

from __future__ import annotations

import datetime
import unittest
from unittest import mock

from scripts.main.interface.command_parsers import (
    OptionParseError,
    parse_date_expression,
    parse_positive_int_option,
    parse_rank_range,
)
from tests.support import bootstrap  # noqa: F401


class CommandParsersTest(unittest.TestCase):
    def test_option_parse_error_string_returns_code(self) -> None:
        self.assertEqual(str(OptionParseError("invalid_number")), "invalid_number")

    def test_parse_date_expression_none_uses_today(self) -> None:
        with mock.patch(
            "scripts.main.interface.command_parsers.get_today",
            return_value=datetime.date(2026, 2, 24),
        ):
            self.assertEqual(parse_date_expression(None), datetime.date(2026, 2, 24))

    def test_parse_date_expression_supports_relative_and_short_formats(self) -> None:
        with mock.patch(
            "scripts.main.interface.command_parsers.get_today",
            return_value=datetime.date(2026, 2, 24),
        ):
            self.assertEqual(parse_date_expression("-3"), datetime.date(2026, 2, 21))
            self.assertEqual(parse_date_expression("05"), datetime.date(2026, 2, 5))
            self.assertEqual(
                parse_date_expression("01-31"),
                datetime.date(2026, 1, 31),
            )
            self.assertEqual(
                parse_date_expression("2025-12-31"),
                datetime.date(2025, 12, 31),
            )

    def test_parse_date_expression_invalid_returns_none(self) -> None:
        with mock.patch(
            "scripts.main.interface.command_parsers.get_today",
            return_value=datetime.date(2026, 2, 24),
        ):
            self.assertIsNone(parse_date_expression("bad-input"))
            self.assertIsNone(parse_date_expression("2026-02-31"))

    def test_parse_positive_int_option(self) -> None:
        self.assertEqual(parse_positive_int_option(None, default=10), 10)
        self.assertEqual(parse_positive_int_option(3, default=10), 3)

        with self.assertRaises(OptionParseError) as invalid_exc:
            parse_positive_int_option("3", default=1)  # type: ignore[arg-type]
        self.assertEqual(str(invalid_exc.exception), "invalid_number")

        with self.assertRaises(OptionParseError) as too_small_exc:
            parse_positive_int_option(0, default=1, min_value=1)
        self.assertEqual(str(too_small_exc.exception), "too_small")

    def test_parse_rank_range(self) -> None:
        self.assertEqual(parse_rank_range("1..10"), (1, 10))
        self.assertEqual(parse_rank_range(" 5..7 "), (5, 7))

        with self.assertRaises(OptionParseError) as exc1:
            parse_rank_range("1-10")
        self.assertEqual(str(exc1.exception), "invalid_format")

        with self.assertRaises(OptionParseError) as exc2:
            parse_rank_range("a..10")
        self.assertEqual(str(exc2.exception), "invalid_number")

        with self.assertRaises(OptionParseError) as exc3:
            parse_rank_range("0..10")
        self.assertEqual(str(exc3.exception), "out_of_bounds")

        with self.assertRaises(OptionParseError) as exc4:
            parse_rank_range("10..1")
        self.assertEqual(str(exc4.exception), "invalid_order")


if __name__ == "__main__":
    unittest.main()
