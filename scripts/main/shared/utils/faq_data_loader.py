"""FAQ 데이터 인덱스 로더."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from scripts.main.shared.utils.path_utils import convert_path


@dataclass(frozen=True)
class FaqCategorySpec:
    category_id: str
    label: str
    path: str


def _load_raw_json(path: str) -> Any:
    # JSON 파일 로드
    with open(path, "r", encoding="utf-8") as file_obj:
        payload: Any = json.load(file_obj)

    return payload


def _parse_category_spec(item: dict[str, Any]) -> FaqCategorySpec:
    # 카테고리 메타데이터 필수 필드 검증
    category_id: str = str(item.get("id", "")).strip()
    label: str = str(item.get("label", "")).strip()
    path: str = str(item.get("path", "")).strip()

    if not category_id or not label or not path:
        raise ValueError("FAQ category requires id/label/path fields.")

    return FaqCategorySpec(
        category_id=category_id,
        label=label,
        path=path,
    )


def _resolve_category_path(manifest_path: str, raw_path: str) -> str:
    # 카테고리 경로 정규화
    if os.path.isabs(raw_path):
        normalized_path: str = os.path.normpath(raw_path)

    else:
        base_dir: str = os.path.dirname(manifest_path)
        normalized_path = os.path.normpath(os.path.join(base_dir, raw_path))

    return convert_path(normalized_path)


def _normalize_items(raw_items: list[Any]) -> list[dict[str, Any]]:
    # FAQ 항목 타입 정규화
    items: list[dict[str, Any]] = []

    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("FAQ entry must be an object.")

        items.append(item)

    return items


def _load_items_from_manifest(
    manifest_path: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    # 카테고리 순회
    raw_categories: Any = payload.get("categories")

    # 카테고리 목록 타입 검증
    if not isinstance(raw_categories, list):
        raise ValueError("FAQ index must contain categories list.")

    # 카테고리 목록 비어 있음 방지
    if not raw_categories:
        raise ValueError("FAQ index categories must not be empty.")

    items: list[dict[str, Any]] = []

    # 카테고리별 항목 병합
    for raw_category in raw_categories:
        # 카테고리 객체 타입 검증
        if not isinstance(raw_category, dict):
            raise ValueError("FAQ category must be an object.")

        # 경로 해석 및 카테고리 데이터 로드
        spec: FaqCategorySpec = _parse_category_spec(raw_category)
        category_path: str = _resolve_category_path(manifest_path, spec.path)
        category_payload: Any = _load_raw_json(category_path)

        # 카테고리 JSON 리스트 타입 검증
        if not isinstance(category_payload, list):
            raise ValueError("FAQ category data must be a list.")

        # 카테고리 항목 누적
        category_items: list[dict[str, Any]] = _normalize_items(category_payload)

        # 카테고리 접두어 부여
        for entry in category_items:
            raw_id_value: Any = entry.get("id")

            if isinstance(raw_id_value, bool) or not isinstance(raw_id_value, int):
                raise ValueError("FAQ entry id must be an integer.")

            if raw_id_value < 0:
                raise ValueError("FAQ entry id must be non-negative.")

            padded_id: str = f"{raw_id_value:03d}"
            full_id: str = f"{spec.label}-{padded_id}"
            normalized_entry: dict[str, Any] = {**entry, "id": full_id}
            items.append(normalized_entry)

    return items


def load_faq_items(path: str) -> list[dict[str, Any]]:
    # FAQ 데이터 로드
    payload: Any = _load_raw_json(path)

    if isinstance(payload, dict):
        # 인덱스 기반 카테고리 병합 처리
        return _load_items_from_manifest(path, payload)

    raise ValueError("FAQ data must be an index object.")
