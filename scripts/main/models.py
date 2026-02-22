import datetime
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CharacterData:
    """캐릭터 정보 데이터 클래스"""

    uuid: str
    level: Decimal
    date: datetime.date
    power: Decimal = Decimal(0)


@dataclass
class PlayerSearchData:
    """플레이어 검색 결과"""

    name: str
    level: Decimal
    power: Decimal


@dataclass
class RankRow:
    """랭킹 크롤링 원시 행 데이터"""

    name: str
    rank: Decimal
    level: Decimal | None = None
    power: Decimal | None = None
    metric: str | None = None
