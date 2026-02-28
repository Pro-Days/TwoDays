"""FAQ 모델 비교 러너 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support import bootstrap  # noqa: F401
from scripts._manage_cmd import compare_faq_models
from scripts._manage_cmd.faq_model_compare_runner import run_compare
from scripts.main.features import faq_model_compare


def test_resolve_default_config_path_exists() -> None:
    # 기본 설정 경로 확인
    config_path = run_compare.resolve_default_config_path()

    path = Path(config_path)

    assert path.name == run_compare.DEFAULT_CONFIG_FILENAME
    assert path.exists() is True


def test_run_with_config_path_calls_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 비교 파이프라인 호출 검증
    captured: dict[str, object] = {}
    fake_config = faq_model_compare.CompareConfig(
        data_path="assets/faq/faq_data.json",
        questions=[
            faq_model_compare.QuestionSpec(
                text="테스트 질문",
                expected_faq_id="faq-001",
            )
        ],
        models=[
            faq_model_compare.ModelSpec(
                label="model-x",
                index_path="assets/faq/faq_index.npz",
                threshold=None,
                top_k=None,
            )
        ],
        threshold=0.8,
        top_k=3,
        output_path="outputs/faq_model_compare.json",
    )

    def fake_load_config(config_path: str) -> faq_model_compare.CompareConfig:
        captured["config_path"] = config_path
        return fake_config

    def fake_run_compare(config: faq_model_compare.CompareConfig) -> dict[str, object]:
        captured["config"] = config
        return {"report": True}

    def fake_write_report(report: dict[str, object], output_path: str | None) -> None:
        captured["report"] = report
        captured["output_path"] = output_path

    monkeypatch.setattr(faq_model_compare, "load_config", fake_load_config)
    monkeypatch.setattr(faq_model_compare, "run_compare", fake_run_compare)
    monkeypatch.setattr(faq_model_compare, "write_report", fake_write_report)

    report = run_compare.run_with_config_path("config.json")

    assert report == {"report": True}
    assert captured["config_path"] == "config.json"
    assert captured["config"] is fake_config
    assert captured["output_path"] == "outputs/faq_model_compare.json"


def test_run_default_uses_default_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 기본 설정 경로 사용 검증
    captured: dict[str, object] = {}

    def fake_resolve_default_config_path() -> str:
        return "default_config.json"

    def fake_run_with_config_path(config_path: str) -> dict[str, object]:
        captured["config_path"] = config_path
        return {"ok": True}

    monkeypatch.setattr(
        run_compare,
        "resolve_default_config_path",
        fake_resolve_default_config_path,
    )
    monkeypatch.setattr(
        run_compare,
        "run_with_config_path",
        fake_run_with_config_path,
    )

    result = run_compare.run_default()

    assert result == {"ok": True}
    assert captured["config_path"] == "default_config.json"


def test_compare_faq_models_main_calls_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 비교 스크립트 실행 위임 검증
    captured: dict[str, object] = {}

    def fake_run_default() -> dict[str, object]:
        captured["called"] = True
        return {"done": True}

    monkeypatch.setattr(run_compare, "run_default", fake_run_default)

    compare_faq_models.main()

    assert captured["called"] is True
