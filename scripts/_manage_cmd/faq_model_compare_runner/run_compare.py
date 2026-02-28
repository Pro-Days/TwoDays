"""FAQ 모델 비교 실행 러너."""

from __future__ import annotations

from pathlib import Path

from scripts.main.features import faq_model_compare


DEFAULT_CONFIG_FILENAME: str = "compare_config.json"


def resolve_default_config_path() -> str:
    # 기본 설정 파일 경로 계산
    base_dir: Path = Path(__file__).resolve().parent
    config_path: Path = base_dir / DEFAULT_CONFIG_FILENAME

    if not config_path.exists():
        # 기본 설정 파일 누락 오류
        raise FileNotFoundError(f"config file not found: {config_path}")

    return str(config_path)


def run_with_config_path(config_path: str) -> dict[str, object]:
    # 설정 로드 및 비교 실행
    config = faq_model_compare.load_config(config_path)
    report = faq_model_compare.run_compare(config)
    faq_model_compare.write_report(report, config.output_path)

    return report


def run_default() -> dict[str, object]:
    # 기본 설정 경로 실행
    config_path: str = resolve_default_config_path()

    return run_with_config_path(config_path)


def main() -> None:
    # 기본 설정 기반 비교 실행
    run_default()


if __name__ == "__main__":
    main()
