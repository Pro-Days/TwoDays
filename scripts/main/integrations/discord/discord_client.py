from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

DISCORD_HTTP_TIMEOUT: tuple[float, float] = (3, 10)


@dataclass
class DiscordHttpResult:
    # 응답 객체와 파싱된 body를 같이 돌려줘, 호출부의 중복 파싱을 줄임
    response: requests.Response
    body: Any


def safe_response_body(response: requests.Response) -> Any:
    # 실패 응답도 로깅 가능한 형태로 남기기 위해 JSON 파싱 실패 시 text로 폴백
    try:
        return response.json()

    except Exception:
        return response.text


# *
def patch_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: tuple[float, float] = DISCORD_HTTP_TIMEOUT,
) -> DiscordHttpResult:
    # JSON 요청 래퍼는 전송 방식만 감추고 예외 처리 정책은 호출부가 결정
    response: requests.Response = requests.patch(
        url,
        headers=headers,
        data=json.dumps(payload),
        timeout=timeout,
    )

    return DiscordHttpResult(response=response, body=safe_response_body(response))


# *
def post_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: tuple[float, float] = DISCORD_HTTP_TIMEOUT,
) -> DiscordHttpResult:
    response: requests.Response = requests.post(
        url,
        headers=headers,
        data=json.dumps(payload),
        timeout=timeout,
    )

    return DiscordHttpResult(response=response, body=safe_response_body(response))


# *
def post_multipart(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    multipart_data: dict[str, Any],
    timeout: tuple[float, float] = DISCORD_HTTP_TIMEOUT,
) -> DiscordHttpResult:
    # 파일 업로드 요청만 multipart 경로로 분리
    response: requests.Response = requests.post(
        url,
        headers=headers,
        files=multipart_data,
        timeout=timeout,
    )

    return DiscordHttpResult(response=response, body=safe_response_body(response))
