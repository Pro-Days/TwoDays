import os
import boto3
import platform
from boto3.dynamodb.conditions import Key


os_name = platform.system()
if os_name == "Linux":
    session = boto3.Session(
        region_name="ap-northeast-2",
    )
else:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="ap-northeast-2",
    )

db_name = os.environ.get("DB_NAME", "")
dynamodb = session.resource("dynamodb")


def read_data(table_name, index=None, condition_dict=None):
    table_name = db_name + "-" + table_name
    table = dynamodb.Table(table_name)  # type: ignore

    condition = None
    if condition_dict:
        for key, value in condition_dict.items():

            if isinstance(value, list):
                add = Key(key).between(value[0], value[1])
            else:
                add = Key(key).eq(value)

            if condition is None:
                condition = add
            else:
                condition = condition & add

    query_params = {"KeyConditionExpression": condition}

    if index:
        query_params["IndexName"] = index

    response = table.query(**query_params)

    items = response.get("Items", [])

    return items if items else None


def scan_data(table_name, index=None, key=None, filter_dict=None):
    table_name = db_name + "-" + table_name
    table = dynamodb.Table(table_name)  # type: ignore

    filter_data = None
    if filter_dict:
        for _key, value in filter_dict.items():
            if isinstance(value, list):
                add = Key(_key).between(value[0], value[1])
            else:
                add = Key(_key).eq(value)

            if filter_data is None:
                filter_data = add
            else:
                filter_data = filter_data & add

    scan_params = {}

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

    return items if items else None


def write_data(table_name, item):
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
