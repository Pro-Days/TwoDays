import os
import platform

import boto3
from boto3.dynamodb.conditions import And, Between, Equals, Key

# 운영 체제에 따라 AWS 자격 증명 설정
os_name: str = platform.system()
if os_name == "Linux":
    session = boto3.Session(
        region_name="ap-northeast-2",
    )

else:
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY", None)
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY", None)

    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise ValueError(
            "AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY must be set in environment variables."
        )

    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="ap-northeast-2",
    )

db_name: str = os.environ.get("DB_NAME", "")
dynamodb = session.resource("dynamodb")


def read_data(
    table_name: str, index: str | None = None, condition_dict: dict | None = None
) -> list[dict]:
    """
    DynamoDB에서 데이터를 읽어오는 함수
    """

    table_name = db_name + "-" + table_name
    table = dynamodb.Table(table_name)  # type: ignore

    condition: Between | Equals | And | None = None
    if condition_dict:
        for key, value in condition_dict.items():

            if isinstance(value, list):
                add: Between | Equals = Key(key).between(value[0], value[1])
            else:
                add = Key(key).eq(value)

            if condition is None:
                condition = add
            else:
                condition = condition & add

    query_params: dict[str, str | Between | Equals | And | None] = {
        "KeyConditionExpression": condition
    }

    if index:
        query_params["IndexName"] = index

    response = table.query(**query_params)

    items = response.get("Items", [])

    return items


def scan_data(
    table_name: str,
    index: str | None = None,
    key: str | None = None,
    filter_dict: dict | None = None,
) -> list[dict]:
    """
    DynamoDB에서 데이터를 스캔하는 함수
    사용을 권장하지 않음 (비용 및 성능 문제)
    """

    table_name = db_name + "-" + table_name
    table = dynamodb.Table(table_name)  # type: ignore

    filter_data: Between | Equals | And | None = None
    if filter_dict:
        for _key, value in filter_dict.items():
            if isinstance(value, list):
                add: Between | Equals = Key(_key).between(value[0], value[1])
            else:
                add = Key(_key).eq(value)

            if filter_data is None:
                filter_data = add
            else:
                filter_data = filter_data & add

    scan_params: dict[str, str | Between | Equals | And | None] = {}

    if key:
        scan_params["ProjectionExpression"] = key

    if filter_dict:
        scan_params["FilterExpression"] = filter_data

    if index:
        scan_params["IndexName"] = index

    response = table.scan(**scan_params)

    items = response.get("Items", [])

    # 페이지네이션 처리: LastEvaluatedKey가 있으면 계속해서 스캔
    while "LastEvaluatedKey" in response:
        scan_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_params)

        items.extend(response.get("Items", []))

    return items


def write_data(table_name: str, item: dict) -> None:
    """
    DynamoDB에 데이터를 쓰는 함수
    """

    table_name = db_name + "-" + table_name
    table = dynamodb.Table(table_name)  # type: ignore

    table.put_item(Item=item)


if __name__ == "__main__":
    # print(scan_data("TA_DEV-DailyData"))
    # data = read_data("DailyData", None, {"id": 1, "date-slot": ["2025-01-01#0", "2025-01-01#4"]})
    #     read_data(
    #         "Ranks", index="id-date-index", condition_dict={"id": 1, "date": ["2025-03-10", "2025-03-18"]}
    #     )
    # )

    pass
