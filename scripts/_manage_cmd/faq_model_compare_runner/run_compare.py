"""FAQ 모델 비교 실행 러너."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.main.features import faq_model_compare

if TYPE_CHECKING:
    from scripts.main.features.faq_model_compare import (
        CompareConfig,
        CompareReportPayload,
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


def main(config_path: str) -> CompareReportPayload:
    # 설정 로드 및 비교 실행
    config: CompareConfig = faq_model_compare.load_config(config_path)
    report: CompareReportPayload = faq_model_compare.run_compare(config)
    faq_model_compare.write_report(report, config.output_path)

    return report


def format_report(report: CompareReportPayload) -> str:
    # 리포트 가독성 직렬화
    return json.dumps(report, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    report: CompareReportPayload = main(resolve_default_config_path())
    print(format_report(report))
