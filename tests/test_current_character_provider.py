"""Tests for current character provider."""

from __future__ import annotations

import datetime
import unittest
from decimal import Decimal
from unittest import mock

from scripts.main.domain.models import CharacterData
from scripts.main.services import current_character_provider as ccp
from tests.support import bootstrap  # noqa: F401


class CurrentCharacterProviderTest(unittest.TestCase):
    def test_estimate_functions_are_deterministic(self) -> None:
        self.assertEqual(ccp._estimate_level("abcde-uuid", 0), Decimal("1.0000"))
        self.assertEqual(
            ccp._estimate_level("abcde-uuid", 5), ccp._estimate_level("abcde-uuid", 5)
        )
        level = ccp._estimate_level("abcde-uuid", 10)
        power = ccp._estimate_power("abcde-uuid", level)
        self.assertEqual(power, ccp._estimate_power("abcde-uuid", level))
        self.assertGreater(power, 0)

    def test_get_current_character_data_uses_target_date(self) -> None:
        base_date = datetime.date(2026, 2, 1)
        result = ccp.get_current_character_data("12345-uuid", target_date=base_date)
        self.assertEqual(result.date, base_date)
        self.assertEqual(result.level, Decimal("1.0000"))
        self.assertEqual(
            result.power, ccp._estimate_power("12345-uuid", Decimal("1.0000"))
        )

    def test_get_current_character_data_by_name(self) -> None:
        fake_data = CharacterData(
            uuid="uuid-1",
            level=Decimal("10"),
            power=Decimal("999"),
            date=datetime.date(2026, 2, 24),
        )
        with mock.patch(
            "scripts.main.services.current_character_provider.get_profile_from_name",
            return_value=("Alice", "uuid-1"),
        ):
            with mock.patch(
                "scripts.main.services.current_character_provider.get_current_character_data",
                return_value=fake_data,
            ):
                result = ccp.get_current_character_data_by_name("Alice")
        self.assertEqual(result.name, "Alice")
        self.assertEqual(result.level, Decimal("10"))
        self.assertEqual(result.power, Decimal("999"))

        with mock.patch(
            "scripts.main.services.current_character_provider.get_profile_from_name",
            return_value=(None, None),
        ):
            with self.assertRaises(ValueError):
                ccp.get_current_character_data_by_name("Unknown")


if __name__ == "__main__":
    unittest.main()
