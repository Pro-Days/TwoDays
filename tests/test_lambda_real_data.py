"""실데이터 기반 Lambda 통합 실행 테스트."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.main.lambda_real_data_runner import CommandRunResult


if not os.getenv("RUN_REAL_DATA_LAMBDA_TESTS"):
    pytest.skip(
        "실데이터 통합 테스트는 RUN_REAL_DATA_LAMBDA_TESTS=1 일 때만 실행합니다.",
        allow_module_level=True,
    )


def test_require_env_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.main.lambda_real_data_runner as runner

    for key in runner.REQUIRED_ENV_VARS:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError):
        runner._require_env()


def test_run_scenarios_with_real_data() -> None:
    import scripts.main.lambda_real_data_runner as runner

    config = runner.RunConfig(
        output_dir=Path("test_outputs"),
        lookback_days=7,
        rank_range="1..10",
        period=7,
    )

    results: list[CommandRunResult] = runner.run_scenarios(config)

    assert results

    for result in results:
        assert result.status_code == 200

    for result in results:
        if result.expect_image:
            assert result.copied_image_path
            assert Path(result.copied_image_path).is_file()
            assert Path(result.copied_image_path).stat().st_size > 0

    register_result: CommandRunResult | None = next(
        (item for item in results if item.label == "등록"), None
    )
    assert register_result is not None
    assert register_result.message
