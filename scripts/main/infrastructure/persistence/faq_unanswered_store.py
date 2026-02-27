"""FAQ 미응답 질문 저장."""

from __future__ import annotations

import datetime
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

import boto3

FAQ_UNANSWERED_TABLE_ENV: str = "FAQ_UNANSWERED_TABLE"
AWS_REGION: str = os.getenv("AWS_REGION", "ap-northeast-2")
AWS_ACCESS_KEY: str | None = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")


@dataclass(frozen=True)
class UnansweredQuestionInput:
    question: str
    top_score: float | None
    top_ids: list[str]
    guild_id: str | None
    channel_id: str | None
    requester_id: str | None


def _now_kst() -> datetime.datetime:
    # DynamoDB 저장 KST 기준 타임스탬프
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)


def _build_session() -> boto3.Session:
    # 기본 리전/선택 액세스 키 세션 구성
    session_kwargs: dict[str, str] = {"region_name": AWS_REGION}

    if AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY:
        session_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
        session_kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY

    return boto3.Session(**session_kwargs)


class FaqUnansweredStore:
    def __init__(self) -> None:
        self.table_name: str | None = os.getenv(FAQ_UNANSWERED_TABLE_ENV)

        if not self.table_name:
            raise RuntimeError(f"missing required env: {FAQ_UNANSWERED_TABLE_ENV}")

        # 테이블 핸들 생성 시점 고정 재사용
        session: boto3.Session = _build_session()
        dynamodb = session.resource("dynamodb")
        self.table = dynamodb.Table(self.table_name)  # type: ignore

    def save_unanswered_question(
        self,
        data: UnansweredQuestionInput,
    ) -> dict[str, Any] | None:
        if self.table is None:
            return None

        now_kst: datetime.datetime = _now_kst()
        month_key: str = now_kst.strftime("%Y-%m")
        timestamp: str = now_kst.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        question_uuid: str = str(uuid.uuid4())

        # 월 단위 파티션/시간+UUID 정렬키 저장
        item: dict[str, Any] = {
            "PK": f"UNANSWERED#{month_key}",
            "SK": f"TS#{timestamp}#{question_uuid}",
            "question": data.question,
            "question_uuid": question_uuid,
            "created_at": timestamp,
        }

        if data.top_score is not None:
            # DynamoDB Decimal 요구에 따른 float 문자열 변환
            item["top_score"] = Decimal(str(data.top_score))

        if data.top_ids:
            item["top_ids"] = data.top_ids

        if data.guild_id:
            item["guild_id"] = data.guild_id

        if data.channel_id:
            item["channel_id"] = data.channel_id

        if data.requester_id:
            item["requester_id"] = data.requester_id

        self.table.put_item(Item=item)

        return item
