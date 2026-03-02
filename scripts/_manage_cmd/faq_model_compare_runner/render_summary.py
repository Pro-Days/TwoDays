"""FAQ 모델 비교 요약 리포트 변환."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

DEFAULT_INPUT_PATH: str = "outputs/faq_model_compare.json"
DEFAULT_OUTPUT_PATH: str = "outputs/faq_model_compare_summary.md"
MAX_TEXT_PREVIEW: int = 80


class CandidatePayload(TypedDict):
    entry_id: str
    question: str
    score: float
    answer: str


class ModelResultPayload(TypedDict):
    model_label: str
    model_id: str
    index_path: str
    threshold: float
    top_score: float | None
    confidence: float | None
    matched: bool
    is_correct: bool
    top_ids: list[str]
    answer: str
    candidates: list[CandidatePayload]


class QuestionReportPayload(TypedDict):
    text: str
    expected_faq_id: str
    results: list[ModelResultPayload]


class ModelAggregatePayload(TypedDict):
    model_label: str
    model_id: str
    index_path: str
    accuracy_top1: float
    correct_count: int
    total_count: int
    avg_confidence: float | None


class SettingsPayload(TypedDict):
    threshold: float
    top_k: int


class CompareReportPayload(TypedDict):
    settings: SettingsPayload
    models: list[ModelAggregatePayload]
    questions: list[QuestionReportPayload]


@dataclass(frozen=True)
class RenderArgs:
    input_path: str
    output_path: str


@dataclass
class ModelSummary:
    label: str
    total: int
    correct_top1: int
    correct_topk: int


def _build_parser() -> argparse.ArgumentParser:
    # CLI 옵션 파서 구성
    parser = argparse.ArgumentParser(description="FAQ 모델 비교 요약 리포트 생성")
    parser.add_argument(
        "--input-path",
        default=DEFAULT_INPUT_PATH,
        help="비교 리포트 JSON 경로",
    )
    parser.add_argument(
        "--output-path",
        default=DEFAULT_OUTPUT_PATH,
        help="요약 마크다운 출력 경로",
    )

    return parser


def _parse_args(argv: list[str]) -> RenderArgs:
    # CLI 인자 파싱
    parser = _build_parser()
    namespace = parser.parse_args(argv)

    return RenderArgs(
        input_path=namespace.input_path, output_path=namespace.output_path
    )


def _load_report(path: str) -> CompareReportPayload:
    # 비교 리포트 JSON 로드
    report_path = Path(path)

    if not report_path.exists():
        raise FileNotFoundError(f"report not found: {report_path}")

    raw = json.loads(report_path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError("invalid report payload")

    return cast(CompareReportPayload, raw)


def _format_bool(value: bool) -> str:
    # 불리언 표시 변환
    return "O" if value else "X"


def _format_float(value: float | None, digits: int) -> str:
    # 숫자 표시 포맷팅
    if value is None:
        return "-"

    return f"{value:.{digits}f}"


def _format_ratio(numerator: int, denominator: int, digits: int) -> str:
    # 비율 표시 포맷팅
    if denominator == 0:
        return "-"

    return f"{numerator / denominator:.{digits}f}"


def _compact_text(value: str) -> str:
    # 개행 제거 및 공백 정리
    return " ".join(value.split())


def _sanitize_table_text(value: str) -> str:
    # 마크다운 테이블 안전 문자열 구성
    compact = _compact_text(value)

    return compact.replace("|", "\\|")


def _truncate_text(value: str, limit: int) -> str:
    # 길이 제한 문자열 구성
    if len(value) <= limit:
        return value

    return value[: max(0, limit - 3)] + "..."


def _extract_top_id(result: ModelResultPayload) -> str:
    # Top1 FAQ ID 추출
    top_ids = result["top_ids"]

    if not top_ids:
        return "-"

    return str(top_ids[0])


def _extract_top_score(result: ModelResultPayload) -> float | None:
    # Top1 점수 추출
    candidates = result["candidates"]

    if not candidates:
        return None

    return candidates[0]["score"]


def _extract_top2_score(result: ModelResultPayload) -> float | None:
    # Top2 점수 추출
    candidates = result["candidates"]

    if len(candidates) < 2:
        return None

    return candidates[1]["score"]


def _extract_expected_rank(expected_id: str, result: ModelResultPayload) -> str:
    # 기대 FAQ ID 순위 계산
    for index, candidate in enumerate(result["candidates"], start=1):
        if candidate["entry_id"] == expected_id:
            return str(index)

    return "-"


def _extract_top_question(result: ModelResultPayload) -> str:
    # Top1 질문 텍스트 추출
    candidates = result["candidates"]

    if not candidates:
        return "-"

    top_question = _sanitize_table_text(candidates[0]["question"])

    return _truncate_text(top_question, MAX_TEXT_PREVIEW) or "-"


def _build_model_summaries(report: CompareReportPayload) -> list[ModelSummary]:
    # 모델별 요약 집계
    summaries: dict[str, ModelSummary] = {}

    for question in report["questions"]:
        # 질문 기준 기대 ID 확보
        expected_id = question["expected_faq_id"]

        for result in question["results"]:
            # 모델별 누적 집계
            label = result["model_label"]
            summary = summaries.get(label)

            if summary is None:
                summary = ModelSummary(
                    label=label, total=0, correct_top1=0, correct_topk=0
                )
                summaries[label] = summary

            summary.total += 1

            if result["is_correct"]:
                summary.correct_top1 += 1

            if expected_id in result["top_ids"]:
                summary.correct_topk += 1

    return list(summaries.values())


def build_summary(report: CompareReportPayload) -> str:
    # 요약 마크다운 구성
    settings = report["settings"]
    questions = report["questions"]
    model_summaries = _build_model_summaries(report)
    lines: list[str] = []

    lines.append("# FAQ 모델 비교 요약")
    lines.append("")
    lines.append("## 설정")
    lines.append(f"- threshold: {settings['threshold']}")
    lines.append(f"- top_k: {settings['top_k']}")
    lines.append("")
    lines.append("## 모델 요약")
    lines.append("| 모델 | Top1 정확도 | TopK 정확도 | Top1 정답 | TopK 정답 |")
    lines.append("|---|---|---|---|---|")

    for summary in sorted(model_summaries, key=lambda item: item.label):
        # 모델 요약 행 구성
        top1_accuracy = _format_ratio(summary.correct_top1, summary.total, 4)
        topk_accuracy = _format_ratio(summary.correct_topk, summary.total, 4)
        top1_count = f"{summary.correct_top1}/{summary.total}"
        topk_count = f"{summary.correct_topk}/{summary.total}"

        lines.append(
            "| "
            + " | ".join(
                [
                    _sanitize_table_text(summary.label),
                    top1_accuracy,
                    topk_accuracy,
                    top1_count,
                    topk_count,
                ]
            )
            + " |"
        )

    lines.append("")

    for index, question in enumerate(questions, start=1):
        # 질문별 테이블 구성
        question_text = _compact_text(question["text"])
        expected_id = _compact_text(question["expected_faq_id"])

        lines.append(f"## 질문 {index}")
        lines.append(f"- 질문: {question_text}")
        lines.append(f"- 기대 FAQ ID: {expected_id}")
        lines.append("")
        lines.append(
            "| 모델 | 매칭 | 정답 | Top1 FAQ | Top1 점수 | Top1-Top2 | "
            "Confidence | 기대 순위 | Top1 질문 |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")

        for result in question["results"]:
            # 모델별 행 구성
            model_label = _sanitize_table_text(result["model_label"])
            matched = _format_bool(result["matched"])
            is_correct = _format_bool(result["is_correct"])
            top_id = _sanitize_table_text(_extract_top_id(result))
            top1_score_value = _extract_top_score(result)
            top2_score_value = _extract_top2_score(result)
            top_score = _format_float(top1_score_value, 4)
            score_gap = (
                _format_float(top1_score_value - top2_score_value, 4)
                if top1_score_value is not None and top2_score_value is not None
                else "-"
            )
            confidence = _format_float(result["confidence"], 4)
            expected_rank = _extract_expected_rank(question["expected_faq_id"], result)
            top_question = _extract_top_question(result)

            lines.append(
                "| "
                + " | ".join(
                    [
                        model_label,
                        matched,
                        is_correct,
                        top_id,
                        top_score,
                        score_gap,
                        confidence,
                        expected_rank,
                        top_question,
                    ]
                )
                + " |"
            )

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_summary(content: str, output_path: str) -> str:
    # 요약 파일 저장
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    return str(output)


def main(input_path: str, output_path: str) -> str:
    # 전체 실행 흐름
    report: CompareReportPayload = _load_report(input_path)
    summary: str = build_summary(report)
    output_path = write_summary(summary, output_path)

    print(output_path)

    return output_path
