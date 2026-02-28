"""Bedrock 임베딩 테스트."""

from __future__ import annotations

import pytest

from scripts.main.integrations.bedrock import bedrock_embeddings
from tests.support import bootstrap  # noqa: F401


@pytest.fixture(autouse=True)
def reset_bedrock_client() -> None:
    # 테스트 간 클라이언트 상태 초기화
    bedrock_embeddings._client = None

    yield

    bedrock_embeddings._client = None


def test_get_client_requires_region(monkeypatch, mocker) -> None:
    # 리전/자격 증명 환경 변수 제거
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)
    # 세션 생성 호출 추적
    session_factory = mocker.patch.object(
        bedrock_embeddings.boto3,
        "Session",
    )

    # 리전 누락 오류 검증
    with pytest.raises(RuntimeError):
        bedrock_embeddings._get_client()

    session_factory.assert_not_called()


def test_get_client_uses_env_region_and_credentials(monkeypatch, mocker) -> None:
    # 리전/자격 증명 환경 변수 설정
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_ACCESS_KEY", "test-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test-token")
    # 세션/클라이언트 모킹
    fake_client = mocker.Mock()
    fake_session = mocker.Mock()
    fake_session.client.return_value = fake_client
    session_factory = mocker.patch.object(
        bedrock_embeddings.boto3,
        "Session",
        return_value=fake_session,
    )

    # 클라이언트 생성 실행
    client = bedrock_embeddings._get_client()

    # 세션/클라이언트 호출 검증
    assert client is fake_client
    session_factory.assert_called_once_with(
        region_name="ap-northeast-2",
        aws_access_key_id="test-access",
        aws_secret_access_key="test-secret",
        aws_session_token="test-token",
    )
    fake_session.client.assert_called_once_with(
        "bedrock-runtime",
        region_name="ap-northeast-2",
    )


def test_extract_embedding_prefers_embedding_key() -> None:
    # embedding 키 우선 처리 검증
    payload = {"embedding": [0.1, 0.2]}

    result = bedrock_embeddings._extract_embedding(payload)

    assert result == [0.1, 0.2]


def test_extract_embedding_reads_embeddings_list() -> None:
    # embeddings 리스트 처리 검증
    payload = {"embeddings": [[0.3, 0.4]]}

    result = bedrock_embeddings._extract_embedding(payload)

    assert result == [0.3, 0.4]


def test_extract_embedding_raises_on_missing_data() -> None:
    # 임베딩 데이터 누락 오류 검증
    payload = {"other": []}

    with pytest.raises(ValueError):
        bedrock_embeddings._extract_embedding(payload)


def test_embed_texts_with_model_uses_model_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 지정 모델 ID 전달 검증 시나리오 준비
    calls: list[tuple[str, str]] = []
    fake_client = object()

    def fake_get_client() -> object:
        return fake_client

    def fake_embed_single(client: object, model_id: str, text: str) -> list[float]:
        calls.append((model_id, text))
        return [0.1]

    monkeypatch.setattr(bedrock_embeddings, "_get_client", fake_get_client)
    monkeypatch.setattr(bedrock_embeddings, "_embed_single", fake_embed_single)

    # 임베딩 실행
    result = bedrock_embeddings.embed_texts_with_model(
        "test-model",
        ["alpha", "beta"],
    )

    # 호출 파라미터 검증
    assert result == [[0.1], [0.1]]
    assert calls == [("test-model", "alpha"), ("test-model", "beta")]


def test_embed_texts_with_model_empty_texts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 빈 입력 처리 시나리오 준비
    def fake_get_client() -> object:
        raise AssertionError("_get_client should not be called.")

    monkeypatch.setattr(bedrock_embeddings, "_get_client", fake_get_client)

    # 빈 입력 반환 검증
    result = bedrock_embeddings.embed_texts_with_model("model-x", [])

    assert result == []


def test_embed_texts_with_model_requires_model_id() -> None:
    # 모델 ID 누락 오류 검증
    with pytest.raises(ValueError):
        bedrock_embeddings.embed_texts_with_model(" ", ["text"])
