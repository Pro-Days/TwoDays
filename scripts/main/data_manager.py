import os
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

import boto3
from boto3.dynamodb.conditions import Attr, ConditionBase, Key

# .env 파일에서 환경 변수 로드
AWS_REGION: str = os.getenv("AWS_REGION", "ap-northeast-2")
AWS_ACCESS_KEY: str | None = os.getenv("AWS_ACCESS_KEY", None)
AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY", None)

SINGLE_TABLE_NAME: str = os.getenv("SINGLE_TABLE_NAME", "").strip()


class GSIName(str, Enum):
    """DynamoDB GSI 이름 상수"""

    OFFICIAL_LEVEL_RANK = "GSI_Official_Level_Rank"
    OFFICIAL_POWER_RANK = "GSI_Official_Power_Rank"
    INTERNAL_LEVEL = "GSI_Internal_Level"
    INTERNAL_POWER = "GSI_Internal_Power"
    FIND_USER_BY_NAME = "GSI_Find_User_By_Name"


def _build_session() -> boto3.Session:
    """AWS 세션을 생성하는 헬퍼 함수"""

    session_kwargs: dict[str, str] = {"region_name": AWS_REGION}

    if AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY:
        session_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
        session_kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY

    return boto3.Session(**session_kwargs)


# AWS 세션과 DynamoDB 리소스 초기화
session: boto3.Session = _build_session()
dynamodb = session.resource("dynamodb")


class SingleTableDataManager:
    """
    Single Table 전용 데이터 접근 매니저 클래스.
    """

    def __init__(self) -> None:
        # 테이블 초기화
        self.table = dynamodb.Table(SINGLE_TABLE_NAME)  # type: ignore

    @staticmethod
    def user_pk(uuid: str) -> str:
        return f"USER#{uuid}"

    @staticmethod
    def snapshot_sk(target_date: date | str) -> str:

        if isinstance(target_date, date):
            return f"SNAP#{target_date.strftime('%Y-%m-%d')}"

        return f"SNAP#{target_date}"

    @staticmethod
    def uuid_from_user_pk(pk: str) -> str:
        return pk.removeprefix("USER#")

    def _put_item(self, item: dict[str, Any]) -> None:
        self.table.put_item(Item=item)

    def _query(
        self,
        key_condition: ConditionBase,
        index_name: GSIName | None = None,
        filter_expression: ConditionBase | None = None,
        projection_expression: str | None = None,
        scan_index_forward: bool = True,
        limit: int | None = None,
        # 페이징을 위한 ExclusiveStartKey: LastEvaluatedKey
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Query: 단일 페이지 조회"""

        query_params: dict[str, Any] = {
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": scan_index_forward,
        }

        if index_name:
            query_params["IndexName"] = index_name.value
        if filter_expression is not None:
            query_params["FilterExpression"] = filter_expression
        if projection_expression:
            query_params["ProjectionExpression"] = projection_expression
        if limit is not None:
            query_params["Limit"] = limit
        if exclusive_start_key is not None:
            query_params["ExclusiveStartKey"] = exclusive_start_key

        response = self.table.query(**query_params)
        return response.get("Items", []), response.get("LastEvaluatedKey")

    def _query_all(
        self,
        key_condition: ConditionBase,
        index_name: GSIName | None = None,
        filter_expression: ConditionBase | None = None,
        projection_expression: str | None = None,
        scan_index_forward: bool = True,
    ) -> list[dict[str, Any]]:
        """Query: 전체 페이지 조회 (자동 페이징)"""

        items: list[dict[str, Any]] = []
        last_evaluated_key: dict[str, Any] | None = None

        while True:
            page_items, last_evaluated_key = self._query(
                key_condition=key_condition,
                index_name=index_name,
                filter_expression=filter_expression,
                projection_expression=projection_expression,
                scan_index_forward=scan_index_forward,
                exclusive_start_key=last_evaluated_key,
            )
            items.extend(page_items)

            if not last_evaluated_key:
                break

        return items

    def _scan(
        self,
        index_name: GSIName | None = None,
        filter_expression: ConditionBase | None = None,
        projection_expression: str | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Scan: 단일 페이지 조회"""

        scan_params: dict[str, Any] = {}

        if index_name:
            scan_params["IndexName"] = index_name.value
        if filter_expression is not None:
            scan_params["FilterExpression"] = filter_expression
        if projection_expression:
            scan_params["ProjectionExpression"] = projection_expression
        if limit is not None:
            scan_params["Limit"] = limit
        if exclusive_start_key is not None:
            scan_params["ExclusiveStartKey"] = exclusive_start_key

        response = self.table.scan(**scan_params)
        return response.get("Items", []), response.get("LastEvaluatedKey")

    def _scan_all(
        self,
        index_name: GSIName | None = None,
        filter_expression: ConditionBase | None = None,
        projection_expression: str | None = None,
    ) -> list[dict[str, Any]]:
        """Scan: 전체 페이지 조회 (자동 페이징)"""

        items: list[dict[str, Any]] = []
        last_evaluated_key: dict[str, Any] | None = None

        while True:
            page_items, last_evaluated_key = self._scan(
                index_name=index_name,
                filter_expression=filter_expression,
                projection_expression=projection_expression,
                exclusive_start_key=last_evaluated_key,
            )
            items.extend(page_items)

            if not last_evaluated_key:
                break

        return items

    # -----------------------------
    # 도메인 특화 메서드
    # 유저 메타데이터 저장, 일일 스냅샷 저장, 랭킹 조회, 유저별 스냅샷 조회 등
    # -----------------------------
    def put_user_metadata(
        self,
        uuid: str,
        name: str,
        current_level: Decimal,
        current_power: Decimal,
        extra: dict[str, Any] | None = None,
    ) -> None:
        item: dict[str, Any] = {
            "PK": self.user_pk(uuid),
            "SK": "METADATA",
            "Name": name,
            "Name_Lower": name.lower(),
            "CurrentLevel": current_level,
            "CurrentPower": current_power,
        }

        if extra:
            item.update(extra)

        self._put_item(item)

    def get_user_metadata(self, uuid: str) -> dict[str, Any] | None:
        items, _ = self._query(
            key_condition=Key("PK").eq(self.user_pk(uuid)) & Key("SK").eq("METADATA"),
            limit=1,
        )
        return items[0] if items else None

    def find_user_metadata_by_name(self, name: str) -> dict[str, Any] | None:
        items, _ = self._query(
            key_condition=Key("Name_Lower").eq(name.lower()) & Key("SK").eq("METADATA"),
            index_name=GSIName.FIND_USER_BY_NAME,
            limit=1,
        )

        return items[0] if items else None

    def scan_all_user_metadata(self) -> list[dict[str, Any]]:
        return self._scan_all(filter_expression=Attr("SK").eq("METADATA"))

    def put_daily_snapshot(
        self,
        uuid: str,
        snapshot_date: date | str,
        name: str,
        level: Decimal,
        power: Decimal,
        level_rank: Decimal | None = None,
        power_rank: Decimal | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        item: dict[str, Any] = {
            "PK": self.user_pk(uuid),
            "SK": self.snapshot_sk(snapshot_date),
            "Name": name,
            "Level": level,
            "Power": power,
        }

        if level_rank is not None:
            item["Level_Rank"] = level_rank
        if power_rank is not None:
            item["Power_Rank"] = power_rank
        if extra:
            item.update(extra)

        self._put_item(item)

    def get_official_level_top(
        self,
        snapshot_date: date | str,
        limit: int = 100,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """공식 레벨 랭킹 조회 (레벨 높은 순)"""

        return self._query(
            key_condition=Key("SK").eq(self.snapshot_sk(snapshot_date)),
            index_name=GSIName.OFFICIAL_LEVEL_RANK,
            scan_index_forward=True,
            limit=limit,
            exclusive_start_key=exclusive_start_key,
        )

    def get_official_power_top(
        self,
        snapshot_date: date | str,
        limit: int = 100,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """공식 전투력 랭킹 조회 (전투력 높은 순)"""

        return self._query(
            key_condition=Key("SK").eq(self.snapshot_sk(snapshot_date)),
            index_name=GSIName.OFFICIAL_POWER_RANK,
            scan_index_forward=True,
            limit=limit,
            exclusive_start_key=exclusive_start_key,
        )

    def get_internal_level_page(
        self,
        snapshot_date: date | str,
        page_size: int = 100,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """
        내부 레벨 랭킹 조회 (레벨 높은 순)
        DB에 저장된 레벨을 기준으로 조회
        """

        return self._query(
            key_condition=Key("SK").eq(self.snapshot_sk(snapshot_date)),
            index_name=GSIName.INTERNAL_LEVEL,
            scan_index_forward=False,
            limit=page_size,
            exclusive_start_key=exclusive_start_key,
        )

    def get_internal_power_page(
        self,
        snapshot_date: date | str,
        page_size: int = 100,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """
        내부 전투력 랭킹 조회 (전투력 높은 순)
        DB에 저장된 전투력을 기준으로 조회
        """

        return self._query(
            key_condition=Key("SK").eq(self.snapshot_sk(snapshot_date)),
            index_name=GSIName.INTERNAL_POWER,
            scan_index_forward=False,
            limit=page_size,
            exclusive_start_key=exclusive_start_key,
        )

    def get_user_snapshot_history(
        self,
        uuid: str,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """유저 스냅샷 조회"""

        key_condition: ConditionBase = Key("PK").eq(self.user_pk(uuid))

        if start_date is not None and end_date is not None:
            key_condition = key_condition & Key("SK").between(
                self.snapshot_sk(start_date), self.snapshot_sk(end_date)
            )
        elif start_date is not None:
            key_condition = key_condition & Key("SK").gte(self.snapshot_sk(start_date))
        elif end_date is not None:
            key_condition = key_condition & Key("SK").lte(self.snapshot_sk(end_date))
        else:
            key_condition = key_condition & Key("SK").begins_with("SNAP#")

        return self._query(
            key_condition=key_condition,
            scan_index_forward=False,
            limit=limit,
            exclusive_start_key=exclusive_start_key,
        )

    def get_user_snapshot(
        self, uuid: str, snapshot_date: date | str
    ) -> dict[str, Any] | None:
        items, _ = self.get_user_snapshot_history(
            uuid=uuid,
            start_date=snapshot_date,
            end_date=snapshot_date,
            limit=1,
        )
        return items[0] if items else None

    def get_level_range_users(
        self,
        snapshot_date: date | str,
        min_level: Decimal,
        max_level: Decimal,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """레벨 범위 내 유저 조회"""

        key_condition = Key("SK").eq(self.snapshot_sk(snapshot_date)) & Key(
            "Level"
        ).between(min_level, max_level)

        return self._query(
            key_condition=key_condition,
            index_name=GSIName.INTERNAL_LEVEL,
            scan_index_forward=False,
            limit=limit,
            exclusive_start_key=exclusive_start_key,
        )

    def get_power_range_users(
        self,
        snapshot_date: date | str,
        min_power: Decimal,
        max_power: Decimal,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """전투력 범위 내 유저 조회"""

        key_condition = Key("SK").eq(self.snapshot_sk(snapshot_date)) & Key(
            "Power"
        ).between(min_power, max_power)

        return self._query(
            key_condition=key_condition,
            index_name=GSIName.INTERNAL_POWER,
            scan_index_forward=False,
            limit=limit,
            exclusive_start_key=exclusive_start_key,
        )


# 데이터 매니저 인스턴스 생성
# 싱글톤 패턴
manager = SingleTableDataManager()


if __name__ == "__main__":
    pass
