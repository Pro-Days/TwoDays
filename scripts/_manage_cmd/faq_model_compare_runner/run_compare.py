"""FAQ 모델 비교 실행 러너(인덱스 자동 갱신 및 요약 출력 포함)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from scripts._manage_cmd import build_faq_index
from scripts._manage_cmd.faq_model_compare_runner import render_summary
from scripts.main.features import faq_model_compare

if TYPE_CHECKING:
    from scripts.main.features.faq_model_compare import (
        CompareConfig,
        CompareReportPayload,
        ModelSpec,
    )


DEFAULT_CONFIG_FILENAME: str = "compare_config.json"


def resolve_default_config_path() -> str:
    # 기본 설정 파일 경로 계산
    base_dir: Path = Path(__file__).resolve().parent
    config_path: Path = base_dir / DEFAULT_CONFIG_FILENAME

    if not config_path.exists():
        # 기본 설정 파일 누락 오류
        raise FileNotFoundError(f"config file not found: {config_path}")

    return str(config_path)


def _build_index_for_model(model: ModelSpec, data_path: str) -> None:
    # 모델별 FAQ 인덱스 자동 갱신
    args: list[str] = ["--data-path", data_path, "--index-path", model.index_path]

    if model.model_id is not None:
        # 모델 ID 지정 인자 추가
        args.extend(["--model-id", model.model_id])

    build_faq_index.main(args)


def main(config_path: str) -> CompareReportPayload:
    # 설정 로드 및 비교 실행
    config: CompareConfig = faq_model_compare.load_config(config_path)

    # 모델별 인덱스 생성/증분 갱신
    for model in config.models:
        _build_index_for_model(model, config.data_path)

    report: CompareReportPayload = faq_model_compare.run_compare(config)
    faq_model_compare.write_report(report, config.output_path)

    if config.output_path:
        # 요약 리포트 경로 계산
        report_path = Path(config.output_path)
        summary_path: Path = report_path.with_name(f"{report_path.stem}_summary.md")

        # 요약 리포트 생성
        render_summary.main(input_path=str(report_path), output_path=str(summary_path))

    return report


if __name__ == "__main__":
    report: CompareReportPayload = main(resolve_default_config_path())

    # print(json.dumps(report, ensure_ascii=False, indent=2))
