"""디스코드 인터랙션 이벤트를 검증하고 메인 Lambda로 전달한다."""

import json
import os
import traceback

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

import boto3
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

PUBLIC_KEY: str | None = os.getenv("DISCORD_PUBLIC_KEY")


def _resolve_interaction_flags(body: dict) -> int:
    """
    플래그 계산
    - 64: 나만보기
    - 128: 응답이 로딩 중임을 나타냄 (기본값)
    """

    flag: int = 128
    data: dict = body.get("data", {})
    command_type: int | None = data.get("type")

    if command_type == 3:
        return flag + 64

    options: list[dict] = data.get("options", []) or []
    for i in options:
        if i.get("name") == "나만보기" and i.get("value"):
            flag += 64
            break

        elif "options" in i:
            for j in i["options"]:
                if j.get("name") == "나만보기" and j.get("value"):
                    flag += 64
                    break

    return flag


def lambda_handler(event, context):
    try:
        print(f"start!\nevent: {event}")

        # PUBLIC_KEY가 설정되어 있지 않으면 500 반환
        if not PUBLIC_KEY:
            return {"statusCode": 500, "body": json.dumps("public key not set")}

        body: dict = json.loads(event["body"])

        signature: str = event.get("headers", {}).get("x-signature-ed25519", "")
        timestamp: str = event.get("headers", {}).get("x-signature-timestamp", "")

        if not signature or not timestamp:
            return {"statusCode": 401, "body": json.dumps("missing request signature")}

        # 키 검증
        verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
        message: str = timestamp + event["body"]

        try:
            verify_key.verify(message.encode(), signature=bytes.fromhex(signature))

        # 검증 실패 시 401 반환
        except BadSignatureError:
            return {"statusCode": 401, "body": json.dumps("invalid request signature")}

        # 검증 성공
        print("verify complete")

        cmd_type: int = body["type"]

        # 1: 핑
        if cmd_type == 1:
            return {"statusCode": 200, "body": json.dumps({"type": 1})}

        # 2: 명령어
        elif cmd_type == 2:

            lambda_service = boto3.client(
                service_name="lambda", region_name="ap-northeast-2"
            )
            function_name: str | None = os.getenv("MAIN_LAMBDA_FUNCTION_NAME")

            if not function_name:
                return {
                    "statusCode": 500,
                    "body": json.dumps("main lambda function name not resolved"),
                }

            # 람다 함수 호출 (비동기)
            lambda_service.invoke(
                FunctionName=function_name,
                InvocationType="Event",
                Payload=json.dumps(event),
            )

            body: dict = json.loads(event["body"])
            flag: int = _resolve_interaction_flags(body)

            # 람다 함수 호출 후 바로 응답 반환
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "type": 5,
                        "data": {
                            "flags": flag,
                        },
                    }
                ),
            }

        # 그 외의 요청 타입은 400 반환
        else:
            return {"statusCode": 400, "body": json.dumps("unhandled request type")}

    # 람다 함수 호출이나 검증 과정에서 예외 발생 시 400 반환
    except Exception:
        return {"statusCode": 400, "body": json.dumps(traceback.format_exc())}
