from __future__ import annotations

import os
from pprint import pprint
from typing import Any

import requests

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass


# Discord API에 따른 옵션 타입 상수
SUB_COMMAND = 1
STRING = 3
INTEGER = 4
BOOLEAN = 5

# 0: guild install, 1: user install
INTEGRATION_TYPES: list[int] = [0, 1]


def _string_option(
    name: str,
    description: str,
    required: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "type": STRING,
        "required": required,
    }


def _integer_option(
    name: str,
    description: str,
    required: bool = False,
    min_value: int | None = None,
    max_value: int | None = None,
) -> dict[str, Any]:

    option: dict[str, Any] = {
        "name": name,
        "description": description,
        "type": INTEGER,
        "required": required,
    }

    if min_value is not None:
        option["min_value"] = min_value
    if max_value is not None:
        option["max_value"] = max_value

    return option


def _boolean_option(
    name: str,
    description: str,
    required: bool = False,
) -> dict[str, Any]:

    return {
        "name": name,
        "description": description,
        "type": BOOLEAN,
        "required": required,
    }


def _sub_command(
    name: str,
    description: str,
    options: list[dict[str, Any]],
) -> dict[str, Any]:

    return {
        "name": name,
        "description": description,
        "type": SUB_COMMAND,
        "options": options,
    }


def _date_option(description_prefix: str) -> dict[str, Any]:
    return _string_option(
        "날짜",
        (
            f"{description_prefix}: YYYY-MM-DD, MM-DD, DD, -n "
            "(예시: 2025-12-31, 12-01, 05, -1, -20)"
        ),
    )


def _period_option(description_prefix: str) -> dict[str, Any]:
    return _integer_option(
        "기간",
        f"{description_prefix}: 2~ (예시: 2, 10, 123)",
        min_value=2,
    )


def _ephemeral_option() -> dict[str, Any]:
    return _boolean_option(
        "나만보기",
        "답변 메시지가 다른사람에게 보이지 않도록 합니다.",
    )


def _search_subcommand(name: str, description: str) -> dict[str, Any]:
    return _sub_command(
        name,
        description,
        [
            _string_option(
                "닉네임",
                "캐릭터 닉네임",
                required=True,
            ),
            _period_option(f"{description}를 조회할 기간"),
            _date_option(f"{description}를 조회할 기준 날짜"),
            _ephemeral_option(),
        ],
    )


def _ranking_subcommand(name: str, description: str) -> dict[str, Any]:
    return _sub_command(
        name,
        description,
        [
            _string_option(
                "랭킹범위",
                "랭킹 범위: (a)..(b) (예시: 1..10, 70..100)",
            ),
            _period_option(f"{description}를 조회할 기간"),
            _date_option(f"{description}를 조회할 기준 날짜"),
            _ephemeral_option(),
        ],
    )


def build_global_commands() -> list[dict[str, Any]]:
    return [
        {
            "name": "랭킹",
            "type": 1,
            "integration_types": INTEGRATION_TYPES,
            "description": "캐릭터 랭킹을 보여줍니다.",
            "options": [
                _ranking_subcommand("레벨", "레벨 랭킹"),
                _ranking_subcommand("전투력", "전투력 랭킹"),
            ],
        },
        {
            "name": "검색",
            "type": 1,
            "integration_types": INTEGRATION_TYPES,
            "description": "캐릭터 정보를 검색합니다.",
            "options": [
                _search_subcommand("레벨", "레벨 히스토리"),
                _search_subcommand("전투력", "전투력 히스토리"),
                _search_subcommand("레벨랭킹", "레벨 랭킹 히스토리"),
                _search_subcommand("전투력랭킹", "전투력 랭킹 히스토리"),
            ],
        },
        {
            "name": "유저분포",
            "type": 1,
            "integration_types": INTEGRATION_TYPES,
            "description": "유저 레벨 분포를 보여줍니다.",
            "options": [
                _date_option("유저 레벨 분포를 조회할 기준 날짜"),
                _ephemeral_option(),
            ],
        },
        {
            "name": "등록",
            "type": 1,
            "integration_types": INTEGRATION_TYPES,
            "description": "일일 정보를 저장하는 캐릭터 목록에 캐릭터를 추가합니다.",
            "options": [
                _string_option("닉네임", "캐릭터 닉네임", required=True),
                _ephemeral_option(),
            ],
        },
    ]


def main() -> None:
    app_id: str | None = os.getenv("DISCORD_APP_ID")
    token: str | None = os.getenv("DISCORD_TOKEN")

    if not app_id or not token:
        raise ValueError("DISCORD_APP_ID and DISCORD_TOKEN must be set")

    url: str = f"https://discord.com/api/v10/applications/{app_id}/commands"
    headers: dict[str, str] = {"Authorization": f"Bot {token}"}
    commands: list[dict[str, Any]] = build_global_commands()

    # 글로벌 명령어 등록: 기존 명령어는 모두 삭제 후 새로 등록
    response: requests.Response = requests.put(
        url, headers=headers, json=commands, timeout=15
    )

    try:
        body: dict | str = response.json()
    except Exception:
        body = response.text

    print(f"status={response.status_code}")
    pprint(body)

    if response.status_code >= 400:
        response.raise_for_status()


if __name__ == "__main__":
    main()
