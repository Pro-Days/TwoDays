"""실데이터 기반 Lambda 명령 통합 실행 러너."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

from scripts.main.shared.utils.time_utils import get_today

ENV_PLAYER_NAME: str = "REAL_DATA_PLAYER_NAME"

REQUIRED_ENV_VARS: tuple[str, ...] = (
    "DISCORD_LOG_CHANNEL_ID",
    "DISCORD_ADMIN_ID",
    "DISCORD_TOKEN",
    "DISCORD_APP_ID",
    "SINGLE_TABLE_NAME",
    "AWS_REGION",
    "AWS_ACCESS_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "FONT_PATH",
    ENV_PLAYER_NAME,
)


class CommandName(str, Enum):
    RANKING = "랭킹"
    SEARCH = "검색"
    USER_DISTRIBUTION = "유저분포"
    REGISTER = "등록"


class SearchType(str, Enum):
    LEVEL = "레벨"
    POWER = "전투력"
    LEVEL_RANK = "레벨랭킹"
    POWER_RANK = "전투력랭킹"


@dataclass(frozen=True)
class CommandSpec:
    label: str
    artifact_prefix: str
    event_body: dict[str, Any]
    expect_image: bool


@dataclass(frozen=True)
class CommandRunResult:
    label: str
    artifact_prefix: str
    status_code: int | None
    message: str | None
    image_path: str | None
    copied_image_path: str | None
    expect_image: bool


@dataclass(frozen=True)
class RunConfig:
    output_dir: Path
    lookback_days: int
    rank_range: str
    period: int


class _SendRecorder:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir: Path = output_dir
        self.current_prefix: str | None = None

    def set_prefix(self, prefix: str) -> None:
        self.current_prefix = prefix

    def __call__(
        self,
        event: dict,
        msg: str,
        image: str | None = None,
        log_type: object | None = None,
        error: str | None = None,
    ) -> dict:
        copied_image: str | None = None

        if image:
            copied_image = self._copy_image(image)

        body: dict[str, Any] = {
            "message": "stubbed",
            "msg": msg,
            "image": image,
            "copied_image": copied_image,
        }

        return {
            "statusCode": 200,
            "body": json.dumps(body, ensure_ascii=False),
        }

    def _copy_image(self, image: str) -> str:
        source = Path(image)
        if not source.exists():
            raise RuntimeError(f"이미지 파일을 찾을 수 없습니다: {image}")

        prefix: str = self.current_prefix or "artifact"
        destination: Path = self._unique_path(
            self.output_dir / f"{prefix}_{source.name}"
        )
        shutil.copy2(source, destination)

        return str(destination)

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path

        stem: str = path.stem
        suffix: str = path.suffix
        parent: Path = path.parent

        for idx in range(1, 1000):
            candidate = parent / f"{stem}_{idx}{suffix}"
            if not candidate.exists():
                return candidate

        raise RuntimeError("이미지 저장 경로가 너무 많이 충돌합니다.")


def _require_env() -> str:
    missing: list[str] = [key for key in REQUIRED_ENV_VARS if not os.getenv(key)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"필수 환경 변수가 누락되었습니다: {joined}")

    player_name: str | None = os.getenv(ENV_PLAYER_NAME)
    if not player_name:
        raise RuntimeError(f"{ENV_PLAYER_NAME} 환경 변수가 필요합니다.")

    return player_name


def _parse_rank_range(range_str: str) -> tuple[int, int]:
    from scripts.main.interface import command_parsers as cp

    try:
        rank_start, rank_end = cp.parse_rank_range(range_str, min_rank=1, max_rank=100)

    except cp.OptionParseError as exc:
        raise RuntimeError(f"랭킹 범위 입력이 올바르지 않습니다: {exc.code}") from exc

    return rank_start, rank_end


def _resolve_player_uuid(player_name: str) -> str:
    from scripts.main.integrations.minecraft import minecraft_profile_service as mps

    real_name, uuid = mps.get_profile_from_name(player_name)
    if not uuid or not real_name:
        raise RuntimeError(f"플레이어 정보를 찾을 수 없습니다: {player_name}")

    return uuid


def _has_internal_level(target_date: datetime.date) -> bool:
    from scripts.main.infrastructure.persistence import data_manager as dm

    items, _ = dm.manager.get_internal_level_page(
        snapshot_date=target_date,
        page_size=1,
        exclusive_start_key=None,
    )
    return bool(items)


def _has_internal_power(target_date: datetime.date) -> bool:
    from scripts.main.infrastructure.persistence import data_manager as dm

    items, _ = dm.manager.get_internal_power_page(
        snapshot_date=target_date,
        page_size=1,
        exclusive_start_key=None,
    )
    return bool(items)


def _has_official_level(target_date: datetime.date) -> bool:
    from scripts.main.infrastructure.persistence import data_manager as dm

    items, _ = dm.manager.get_official_level_top(
        snapshot_date=target_date,
        limit=1,
        exclusive_start_key=None,
    )
    return bool(items)


def _get_user_history(
    uuid: str, start_date: datetime.date, end_date: datetime.date
) -> list[dict[str, Any]]:
    from scripts.main.infrastructure.persistence import data_manager as dm

    items, _ = dm.manager.get_user_snapshot_history(
        uuid=uuid,
        start_date=start_date,
        end_date=end_date,
    )

    return items


def _count_field(items: list[dict[str, Any]], field: str) -> int:
    return sum(1 for item in items if item.get(field) is not None)


def _find_target_date(uuid: str, period: int, lookback_days: int) -> datetime.date:
    start_date: datetime.date = get_today(1)

    for offset in range(lookback_days):
        candidate = start_date - datetime.timedelta(days=offset)

        if not _has_internal_level(candidate):
            continue

        if not _has_internal_power(candidate):
            continue

        if not _has_official_level(candidate):
            continue

        range_start = candidate - datetime.timedelta(days=period - 1)
        history_items = _get_user_history(uuid, range_start, candidate)

        if len(history_items) < 2:
            continue

        if _count_field(history_items, "Level") < 2:
            continue

        if _count_field(history_items, "Power") < 2:
            continue

        if _count_field(history_items, "Level_Rank") < 2:
            continue

        if _count_field(history_items, "Power_Rank") < 2:
            continue

        return candidate

    raise RuntimeError(
        "조건을 만족하는 날짜를 찾지 못했습니다. "
        "REAL_DATA_PLAYER_NAME을 랭킹 상위 유저로 지정하거나 lookback/period를 조정해주세요."
    )


def _build_event(command: CommandName, options: list[dict[str, Any]]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "token": "local-test-token",
        "data": {
            "name": command.value,
            "options": options,
        },
        "member": {
            "user": {
                "id": "local-test-user",
                "username": "local",
            }
        },
        "guild_id": "local-test-guild",
    }

    return {"body": json.dumps(body, ensure_ascii=False)}


def _build_subcommand(name: str, options: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "options": options,
    }


def _build_rank_options(
    range_str: str,
    target_date: datetime.date,
    period: int | None,
) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = [
        {"name": "랭킹범위", "value": range_str},
        {"name": "날짜", "value": target_date.strftime("%Y-%m-%d")},
    ]

    if period is not None:
        options.append({"name": "기간", "value": period})

    return options


def _build_search_options(
    player_name: str,
    target_date: datetime.date,
    period: int,
) -> list[dict[str, Any]]:
    return [
        {"name": "닉네임", "value": player_name},
        {"name": "기간", "value": period},
        {"name": "날짜", "value": target_date.strftime("%Y-%m-%d")},
    ]


def _build_distribution_options(target_date: datetime.date) -> list[dict[str, Any]]:
    return [{"name": "날짜", "value": target_date.strftime("%Y-%m-%d")}]


def _build_register_options(player_name: str) -> list[dict[str, Any]]:
    return [{"name": "닉네임", "value": player_name}]


def _build_command_specs(
    player_name: str,
    target_date: datetime.date,
    rank_range: str,
    period: int,
) -> list[CommandSpec]:
    ranking_level = _build_event(
        CommandName.RANKING,
        [
            _build_subcommand(
                SearchType.LEVEL.value,
                _build_rank_options(rank_range, target_date, None),
            )
        ],
    )

    ranking_power_history = _build_event(
        CommandName.RANKING,
        [
            _build_subcommand(
                SearchType.POWER.value,
                _build_rank_options(rank_range, target_date, period),
            )
        ],
    )

    search_level = _build_event(
        CommandName.SEARCH,
        [
            _build_subcommand(
                SearchType.LEVEL.value,
                _build_search_options(player_name, target_date, period),
            )
        ],
    )

    search_power = _build_event(
        CommandName.SEARCH,
        [
            _build_subcommand(
                SearchType.POWER.value,
                _build_search_options(player_name, target_date, period),
            )
        ],
    )

    search_level_rank = _build_event(
        CommandName.SEARCH,
        [
            _build_subcommand(
                SearchType.LEVEL_RANK.value,
                _build_search_options(player_name, target_date, period),
            )
        ],
    )

    search_power_rank = _build_event(
        CommandName.SEARCH,
        [
            _build_subcommand(
                SearchType.POWER_RANK.value,
                _build_search_options(player_name, target_date, period),
            )
        ],
    )

    user_distribution = _build_event(
        CommandName.USER_DISTRIBUTION,
        _build_distribution_options(target_date),
    )

    register = _build_event(
        CommandName.REGISTER,
        _build_register_options(player_name),
    )

    return [
        CommandSpec(
            label="랭킹 레벨",
            artifact_prefix="ranking_level",
            event_body=ranking_level,
            expect_image=True,
        ),
        CommandSpec(
            label="랭킹 전투력 히스토리",
            artifact_prefix="ranking_power_history",
            event_body=ranking_power_history,
            expect_image=True,
        ),
        CommandSpec(
            label="검색 레벨",
            artifact_prefix="search_level",
            event_body=search_level,
            expect_image=True,
        ),
        CommandSpec(
            label="검색 전투력",
            artifact_prefix="search_power",
            event_body=search_power,
            expect_image=True,
        ),
        CommandSpec(
            label="검색 레벨랭킹",
            artifact_prefix="search_level_rank",
            event_body=search_level_rank,
            expect_image=True,
        ),
        CommandSpec(
            label="검색 전투력랭킹",
            artifact_prefix="search_power_rank",
            event_body=search_power_rank,
            expect_image=True,
        ),
        CommandSpec(
            label="유저분포",
            artifact_prefix="user_distribution",
            event_body=user_distribution,
            expect_image=True,
        ),
        CommandSpec(
            label="등록",
            artifact_prefix="register",
            event_body=register,
            expect_image=False,
        ),
    ]


def _parse_lambda_result(
    result: dict[str, Any],
) -> tuple[int | None, str | None, str | None, str | None]:
    status_code = result.get("statusCode") if isinstance(result, dict) else None
    body_raw = result.get("body") if isinstance(result, dict) else None
    message: str | None = None
    image_path: str | None = None
    copied_image: str | None = None

    if isinstance(body_raw, str):
        try:
            body_json = json.loads(body_raw)

        except Exception:
            body_json = body_raw

        if isinstance(body_json, dict):
            message = body_json.get("msg") or body_json.get("message")
            image_path = body_json.get("image")
            copied_image = body_json.get("copied_image")

    return status_code, message, image_path, copied_image


def run_scenarios(config: RunConfig) -> list[CommandRunResult]:
    player_name: str = _require_env()

    if not config.output_dir:
        raise RuntimeError("output_dir는 필수입니다.")

    config.output_dir.mkdir(parents=True, exist_ok=True)

    uuid = _resolve_player_uuid(player_name)
    _parse_rank_range(config.rank_range)

    target_date = _find_target_date(uuid, config.period, config.lookback_days)

    specs = _build_command_specs(
        player_name=player_name,
        target_date=target_date,
        rank_range=config.rank_range,
        period=config.period,
    )

    from scripts.main import lambda_function as lf
    from scripts.main.integrations.discord import send_msg as sm

    recorder = _SendRecorder(config.output_dir)
    original_send = sm.send
    sm.send = recorder

    results: list[CommandRunResult] = []

    try:
        for spec in specs:
            recorder.set_prefix(spec.artifact_prefix)
            result = lf.lambda_handler(spec.event_body, None)
            status_code, message, image_path, copied_image = _parse_lambda_result(
                result
            )

            results.append(
                CommandRunResult(
                    label=spec.label,
                    artifact_prefix=spec.artifact_prefix,
                    status_code=status_code,
                    message=message,
                    image_path=image_path,
                    copied_image_path=copied_image,
                    expect_image=spec.expect_image,
                )
            )

    finally:
        sm.send = original_send

    return results


def _print_results(results: list[CommandRunResult]) -> None:
    for result in results:
        print(f"[{result.label}] status={result.status_code}")
        print(f"message={result.message}")
        print(f"image_path={result.image_path}")
        print(f"copied_image_path={result.copied_image_path}")
        print("-")


def main() -> None:
    parser = argparse.ArgumentParser(description="실데이터 기반 Lambda 통합 실행")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument("--rank-range", default="1..10")
    parser.add_argument("--period", type=int, default=7)

    args = parser.parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()

    config = RunConfig(
        output_dir=output_dir,
        lookback_days=args.lookback_days,
        rank_range=args.rank_range,
        period=args.period,
    )

    results = run_scenarios(config)
    _print_results(results)


if __name__ == "__main__":
    main()
