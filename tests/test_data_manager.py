"""Tests for persistence data manager helpers."""

from __future__ import annotations

import datetime
import unittest
from decimal import Decimal
from unittest import mock

from scripts.main.infrastructure.persistence import data_manager as dm
from tests.support import bootstrap


class _FakeTable:
    def __init__(self, query_result=None, scan_result=None) -> None:
        self.query_result = query_result or {"Items": []}
        self.scan_result = scan_result or {"Items": []}
        self.query_calls: list[dict] = []
        self.scan_calls: list[dict] = []

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return self.query_result

    def scan(self, **kwargs):
        self.scan_calls.append(kwargs)
        return self.scan_result

    def put_item(self, Item):
        self.last_item = Item


class DataManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = dm.SingleTableDataManager.__new__(dm.SingleTableDataManager)
        self.manager.table = _FakeTable()

    def test_build_session_uses_module_constants(self) -> None:
        with mock.patch.object(dm, "AWS_REGION", "ap-test-1"):
            with mock.patch.object(dm, "AWS_ACCESS_KEY", "ak"):
                with mock.patch.object(dm, "AWS_SECRET_ACCESS_KEY", "sk"):
                    with mock.patch.object(
                        dm.boto3, "Session", side_effect=bootstrap.FakeBoto3Session
                    ) as session_mock:
                        session = dm._build_session()
        self.assertIsInstance(session, bootstrap.FakeBoto3Session)
        session_mock.assert_called_once_with(
            region_name="ap-test-1",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
        )

    def test_static_helpers(self) -> None:
        self.assertEqual(dm.SingleTableDataManager.user_pk("u1"), "USER#u1")
        self.assertEqual(
            dm.SingleTableDataManager.snapshot_sk("2026-02-24"), "SNAP#2026-02-24"
        )
        self.assertEqual(
            dm.SingleTableDataManager.snapshot_sk(datetime.date(2026, 2, 24)),
            "SNAP#2026-02-24",
        )
        self.assertEqual(dm.SingleTableDataManager.uuid_from_user_pk("USER#abc"), "abc")
        self.assertEqual(
            dm.SingleTableDataManager.date_from_snapshot_sk("SNAP#2026-02-24"),
            datetime.date(2026, 2, 24),
        )

    def test_query_builds_params_and_returns_items_and_lek(self) -> None:
        table = _FakeTable(
            query_result={"Items": [{"x": 1}], "LastEvaluatedKey": {"k": 1}}
        )
        self.manager.table = table
        items, lek = self.manager._query(
            key_condition=dm.Key("PK").eq("USER#u1"),
            index_name=dm.GSIName.ALL_METADATA,
            projection_expression="PK,SK",
            scan_index_forward=False,
            limit=5,
            exclusive_start_key={"k": 0},
        )
        self.assertEqual(items, [{"x": 1}])
        self.assertEqual(lek, {"k": 1})
        self.assertEqual(
            table.query_calls[0]["IndexName"], dm.GSIName.ALL_METADATA.value
        )
        self.assertEqual(table.query_calls[0]["Limit"], 5)
        self.assertFalse(table.query_calls[0]["ScanIndexForward"])

    def test_query_all_paginates(self) -> None:
        calls = [
            ([{"a": 1}], {"next": 1}),
            ([{"a": 2}], None),
        ]

        def fake_query(**kwargs):
            return calls.pop(0)

        self.manager._query = fake_query  # type: ignore[method-assign]
        items = self.manager._query_all(key_condition=dm.Key("SK").eq("METADATA"))
        self.assertEqual(items, [{"a": 1}, {"a": 2}])

    def test_put_user_metadata_and_put_daily_snapshot(self) -> None:
        captured = []
        self.manager._put_item = lambda item: captured.append(item)  # type: ignore[method-assign]

        self.manager.put_user_metadata("u1", "Alice", extra={"Role": "admin"})
        self.manager.put_daily_snapshot(
            uuid="u1",
            snapshot_date="2026-02-24",
            name="Alice",
            level=Decimal("10"),
            power=Decimal("20"),
            level_rank=Decimal("1"),
        )

        self.assertEqual(captured[0]["PK"], "USER#u1")
        self.assertEqual(captured[0]["Name_Lower"], "alice")
        self.assertEqual(captured[0]["Role"], "admin")
        self.assertEqual(captured[1]["SK"], "SNAP#2026-02-24")
        self.assertEqual(captured[1]["Level"], Decimal("10"))
        self.assertNotIn("Power_Rank", captured[1])

    def test_get_user_snapshot_history_builds_expected_conditions(self) -> None:
        recorded = {}

        def fake_query(**kwargs):
            recorded.update(kwargs)
            return [], None

        self.manager._query = fake_query  # type: ignore[method-assign]

        with mock.patch.object(dm, "Key", bootstrap._StubKey):
            self.manager.get_user_snapshot_history("u1")
            self.assertIn("BEGINS_WITH 'SNAP#'", str(recorded["key_condition"]))
            self.assertFalse(recorded["scan_index_forward"])

            self.manager.get_user_snapshot_history(
                "u1", start_date="2026-02-01", end_date="2026-02-10", limit=3
            )
            self.assertIn(
                "BETWEEN 'SNAP#2026-02-01' AND 'SNAP#2026-02-10'",
                str(recorded["key_condition"]),
            )
            self.assertEqual(recorded["limit"], 3)

    def test_rank_query_wrappers_delegate_to_query(self) -> None:
        calls = []

        def fake_query(**kwargs):
            calls.append(kwargs)
            return [], None

        self.manager._query = fake_query  # type: ignore[method-assign]

        self.manager.get_internal_power_page(
            "2026-02-24", page_size=7, exclusive_start_key={"k": 1}
        )
        self.manager.get_official_level_top("2026-02-24", limit=9)
        self.assertEqual(calls[0]["index_name"], dm.GSIName.INTERNAL_POWER)
        self.assertEqual(calls[0]["limit"], 7)
        self.assertFalse(calls[0]["scan_index_forward"])
        self.assertEqual(calls[1]["index_name"], dm.GSIName.OFFICIAL_LEVEL_RANK)
        self.assertTrue(calls[1]["scan_index_forward"])


if __name__ == "__main__":
    unittest.main()
