"""Tests for command validation helpers."""

from __future__ import annotations

import datetime
import unittest
from unittest import mock

from scripts.main.interface import command_validation as cv
from tests.support import bootstrap  # noqa: F401


class CommandValidationTest(unittest.TestCase):
    def test_validate_target_date_none(self) -> None:
        self.assertEqual(
            cv.validate_target_date(None),
            cv.DATE_INPUT_INVALID_MESSAGE,
        )

    def test_validate_target_date_future_and_today_policy(self) -> None:
        with mock.patch(
            "scripts.main.interface.command_validation.get_today",
            return_value=datetime.date(2026, 2, 24),
        ):
            self.assertEqual(
                cv.validate_target_date(datetime.date(2026, 2, 25)),
                cv.FUTURE_DATE_NOT_ALLOWED_MESSAGE,
            )
            self.assertEqual(
                cv.validate_target_date(
                    datetime.date(2026, 2, 24),
                    allow_today=False,
                ),
                cv.TODAY_DATE_NOT_ALLOWED_MESSAGE,
            )
            self.assertIsNone(cv.validate_target_date(datetime.date(2026, 2, 23)))


if __name__ == "__main__":
    unittest.main()
