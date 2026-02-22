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
