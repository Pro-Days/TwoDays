"""FAQ 모델 비교 실행."""

from __future__ import annotations

from scripts._manage_cmd.faq_model_compare_runner import run_compare


def main() -> None:
    # 기본 설정 기반 비교 실행
    run_compare.run_default()


if __name__ == "__main__":
    main()
