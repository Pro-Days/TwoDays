"""Bedrock 임베딩 호출 담당."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

import boto3

from scripts.main.shared.utils.log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)

EMBED_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
CONTENT_TYPE: str = "application/json"
ACCEPT_TYPE: str = "application/json"
COHERE_EMBED_V4_MODEL_TOKEN: str = "cohere.embed-v4"
COHERE_EMBED_V4_INPUT_TYPE_DOCUMENT: str = "search_document"
COHERE_EMBED_V4_INPUT_TYPE_QUERY: str = "search_query"

_client: Any | None = None

AWS_REGION_ENV: str = "AWS_REGION"
AWS_ACCESS_KEY_ENV: str = "AWS_ACCESS_KEY"
AWS_SECRET_ACCESS_KEY_ENV: str = "AWS_SECRET_ACCESS_KEY"
AWS_SESSION_TOKEN_ENV: str = "AWS_SESSION_TOKEN"


def _resolve_region() -> str:
    # Bedrock 호출 리전 환경 변수 주입
    region_name: str | None = os.getenv(AWS_REGION_ENV)

    if not region_name:
        raise RuntimeError("missing required env: AWS_REGION")

    return region_name


def _build_session_kwargs(region_name: str) -> dict[str, str]:
    # 명시 자격 증명 기반 세션 구성
    access_key: str | None = os.getenv(AWS_ACCESS_KEY_ENV)
    secret_key: str | None = os.getenv(AWS_SECRET_ACCESS_KEY_ENV)
    session_token: str | None = os.getenv(AWS_SESSION_TOKEN_ENV)
    session_kwargs: dict[str, str] = {"region_name": region_name}

    logger.info(
        "bedrock credential env presence: access_key=%s secret_key=%s session_token=%s",
        bool(access_key),
        bool(secret_key),
        bool(session_token),
    )

    if access_key and secret_key:
        session_kwargs["aws_access_key_id"] = access_key
        session_kwargs["aws_secret_access_key"] = secret_key

        if session_token:
            # 세션 토큰 선택 적용
            session_kwargs["aws_session_token"] = session_token

    return session_kwargs


def _get_client() -> Any:
    global _client

    if _client is None:
        # 최초 호출 시 Bedrock 런타임 클라이언트 생성
        region_name: str = _resolve_region()
        session_kwargs: dict[str, str] = _build_session_kwargs(region_name)

        session = boto3.Session(**session_kwargs)
        _client = session.client("bedrock-runtime", region_name=region_name)

    return _client


def _extract_embedding(payload: dict[str, Any]) -> list[float]:
    # 응답 키 후보 순차 확인
    if "embedding" in payload:
        return [float(value) for value in payload["embedding"]]

    embeddings_value: Any = payload.get("embeddings")

    if isinstance(embeddings_value, list) and embeddings_value:
        first_item: Any = embeddings_value[0]

        if isinstance(first_item, list):
            return [float(value) for value in first_item]

    if isinstance(embeddings_value, dict) and embeddings_value:
        for vector_group in embeddings_value.values():
            if not isinstance(vector_group, list) or not vector_group:
                continue

            first_item: Any = vector_group[0]

            if isinstance(first_item, list):
                return [float(value) for value in first_item]

    raise ValueError("Bedrock embedding response does not contain embedding data.")


def _is_cohere_embed_v4_model(model_id: str) -> bool:
    # Cohere v4 모델 식별자 판별
    return COHERE_EMBED_V4_MODEL_TOKEN in model_id


def _build_embed_payload(model_id: str, text: str, input_type: str | None) -> str:
    # 모델별 임베딩 요청 스키마 분기
    if _is_cohere_embed_v4_model(model_id):
        # Cohere v4 입력 타입 기본값 적용
        resolved_input_type: str = (
            input_type if input_type is not None else COHERE_EMBED_V4_INPUT_TYPE_DOCUMENT
        )

        return json.dumps(
            {
                "texts": [text],
                "input_type": resolved_input_type,
            }
        )

    return json.dumps({"inputText": text})


def _embed_single(
    client: Any,
    model_id: str,
    text: str,
    input_type: str | None,
) -> list[float]:
    """단일 텍스트를 Bedrock 임베딩으로 변환"""

    # 모델별 Bedrock 요청 본문 직렬화
    payload: str = _build_embed_payload(model_id, text, input_type)

    response: dict[str, Any] = client.invoke_model(
        modelId=model_id,
        body=payload,
        contentType=CONTENT_TYPE,
        accept=ACCEPT_TYPE,
    )

    body = response.get("body")
    if body is None:
        raise ValueError("Bedrock response body is empty.")

    # 응답 본문 스트림 읽기 및 JSON 파싱
    raw = body.read()
    data: dict[str, Any] = json.loads(raw)

    return _extract_embedding(data)


def embed_texts(
    texts: list[str],
    model_id: str = EMBED_MODEL_ID,
    input_type: str | None = None,
) -> list[list[float]]:
    """텍스트 목록을 지정 모델 Bedrock 임베딩으로 변환"""

    # 모델 ID 필수값 검증
    cleaned_model_id: str = model_id.strip()
    cleaned_input_type: str | None = None

    if not cleaned_model_id:
        raise ValueError("model_id is required.")

    if input_type is not None:
        # 입력 타입 공백 값 방지
        cleaned_input_type = input_type.strip()

        if not cleaned_input_type:
            raise ValueError("input_type must not be blank.")

    if not texts:
        return []

    logger.debug(
        "bedrock embed_texts_with_model start: "
        f"count={len(texts)} model_id={cleaned_model_id}"
    )
    client = _get_client()
    embeddings: list[list[float]] = []

    for text in texts:
        # 배치 미지원에 따른 순차 임베딩 생성
        embeddings.append(
            _embed_single(client, cleaned_model_id, text, cleaned_input_type)
        )

    return embeddings
