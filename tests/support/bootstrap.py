"""Bootstrap helpers for tests."""

from __future__ import annotations

import sys
import types
from typing import Any


class _StubCondition:
    def __init__(self, expr: str) -> None:
        self.expr = expr

    def __and__(self, other: "_StubCondition") -> "_StubCondition":
        return _StubCondition(f"({self.expr}) AND ({other.expr})")

    def __repr__(self) -> str:
        return self.expr

    __str__ = __repr__


class _StubKey:
    def __init__(self, name: str) -> None:
        self.name = name

    def eq(self, value: Any) -> _StubCondition:
        return _StubCondition(f"{self.name} == {value!r}")

    def between(self, start: Any, end: Any) -> _StubCondition:
        return _StubCondition(f"{self.name} BETWEEN {start!r} AND {end!r}")

    def gte(self, value: Any) -> _StubCondition:
        return _StubCondition(f"{self.name} >= {value!r}")

    def lte(self, value: Any) -> _StubCondition:
        return _StubCondition(f"{self.name} <= {value!r}")

    def begins_with(self, value: Any) -> _StubCondition:
        return _StubCondition(f"{self.name} BEGINS_WITH {value!r}")


class _FakeTable:
    def __init__(self) -> None:
        self.last_put_item: dict[str, Any] | None = None
        self.last_query_kwargs: dict[str, Any] | None = None
        self.last_scan_kwargs: dict[str, Any] | None = None

    def put_item(self, Item: dict[str, Any]) -> dict[str, Any]:
        self.last_put_item = Item
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.last_query_kwargs = kwargs
        return {"Items": []}

    def scan(self, **kwargs: Any) -> dict[str, Any]:
        self.last_scan_kwargs = kwargs
        return {"Items": []}


class _FakeDynamoResource:
    def __init__(self) -> None:
        self.tables: dict[str, _FakeTable] = {}

    def Table(self, name: str) -> _FakeTable:
        if name not in self.tables:
            self.tables[name] = _FakeTable()
        return self.tables[name]


class FakeBoto3Session:
    last_init_kwargs: dict[str, Any] | None = None

    def __init__(self, **kwargs: Any) -> None:
        type(self).last_init_kwargs = kwargs
        self._resource = _FakeDynamoResource()

    def resource(self, name: str) -> _FakeDynamoResource:
        if name != "dynamodb":
            raise ValueError(name)
        return self._resource


class FakeMojangAPI:
    def __init__(
        self,
        retry_on_ratelimit: bool = True,
        ratelimit_sleep_time: int = 1,
    ) -> None:
        self.retry_on_ratelimit = retry_on_ratelimit
        self.ratelimit_sleep_time = ratelimit_sleep_time

    def get_uuid(self, name: str) -> str | None:
        return None

    def get_username(self, uuid: str | None) -> str | None:
        return None

    def get_uuids(self, names: list[str]) -> dict[str, str]:
        return {}


def _install_boto3_stub() -> None:
    boto3_module = types.ModuleType("boto3")
    boto3_module.Session = FakeBoto3Session

    dynamodb_module = types.ModuleType("boto3.dynamodb")
    conditions_module = types.ModuleType("boto3.dynamodb.conditions")
    conditions_module.ConditionBase = _StubCondition
    conditions_module.Key = _StubKey
    conditions_module.Attr = _StubKey

    dynamodb_module.conditions = conditions_module
    boto3_module.dynamodb = dynamodb_module

    sys.modules.setdefault("boto3", boto3_module)
    sys.modules.setdefault("boto3.dynamodb", dynamodb_module)
    sys.modules.setdefault("boto3.dynamodb.conditions", conditions_module)


def _install_mojang_stub() -> None:
    mojang_module = types.ModuleType("mojang")
    mojang_module.API = FakeMojangAPI
    sys.modules.setdefault("mojang", mojang_module)


def install_external_stubs() -> None:
    try:
        import boto3  # noqa: F401
    except Exception:
        _install_boto3_stub()

    try:
        import mojang  # noqa: F401
    except Exception:
        _install_mojang_stub()


install_external_stubs()
