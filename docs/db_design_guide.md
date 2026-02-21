# 게임 유저 랭킹 시스템 DB 설계 명세서

본 명세서는 Single Table Design 패턴을 채택하여 유저의 현재 프로필 정보와 과거 일별 기록을 하나의 테이블에서 관리하고, 읽기 비용($RCU$)을 극최적화하는 방향으로 설계되었습니다.

## 1. 기본 테이블 설정 (Base Table)

| 항목 | 설정 값 |
| --- | --- |
| Table Name | `Hanwol_Bot_DEV_Single_Table` |
| Partition Key ($PK$) | `PK` (String) |
| Sort Key ($SK$) | `SK` (String) |

## 2. 데이터 항목(Item) 구조

테이블은 역할에 따라 두 가지 형태의 데이터를 저장합니다.

### A. 프로필 메타데이터 (최신 정보)
유저의 고유 정보와 현재 상태를 나타냅니다. 유저가 닉네임을 변경할 경우 이 항목만 업데이트합니다.

- **$PK$**: `USER#<UUID>` (예: `USER#A101`)
- **$SK$**: `METADATA`

**Attributes:**
- `Name`: 플레이어 이름 (예: "Hello")
- `Name_Lower`: 검색용 소문자 이름 (예: "hello")
- `CurrentLevel`: 유저의 실시간 현재 레벨
- `CurrentPower`: 유저의 실시간 현재 전투력

### B. 일별 스냅샷 (Daily Snapshot)
매일 특정 시점의 유저 상태를 기록합니다. 랭킹 조회 시 추가적인 조인을 방지하기 위해 유저 이름(`Name`)을 비정규화(중복 저장) 합니다.

- **$PK$**: `USER#<UUID>`
- **$SK$**: `SNAP#2026-02-21` (날짜별 식별)

**Attributes:**
- `Name`: 기록 시점의 유저 이름 (조회 시 메타데이터 조회 방지용)
- `Level`: 해당 날짜의 레벨
- `Power`: 해당 날짜의 전투력
- `Level_Rank`: 공식 레벨 순위 (1~100위일 때만 생성)
- `Power_Rank`: 공식 전투력 순위 (1~100위일 때만 생성)

## 3. 보조 인덱스 (GSI) 설정

순위 조회를 효율적으로 수행하기 위해 랭킹 관련 GSI의 $PK$는 베이스 테이블의 $SK$(`SNAP#날짜`)로 설정하며, 유저 검색을 위한 GSI는 `Name_Lower`를 활용합니다.

| 인덱스 명 | Index PK | Index SK | Projection (포함 속성) | 용도 |
| --- | --- | --- | --- | --- |
| `GSI_Official_Level_Rank` | $SK$ | `Level_Rank` | `Name`, `Level` | 공식 레벨 TOP 100 조회 |
| `GSI_Official_Power_Rank` | $SK$ | `Power_Rank` | `Name`, `Power` | 공식 전투력 TOP 100 조회 |
| `GSI_Internal_Level` | $SK$ | `Level` | `Name` | 101위 이하 커스텀 레벨 순위 |
| `GSI_Internal_Power` | $SK$ | `Power` | `Name` | 101위 이하 커스텀 전투력 순위 |
| `GSI_Find_User_By_Name` | `Name_Lower` | `SK` | `Keys Only` | 유저 이름(소문자)으로 UUID 조회 |

## 4. 핵심 구현 로직 (개발 가이드)

### ① 공식 TOP 100 조회 (Fast Path)
공식 순위 속성이 존재하는 데이터만 인덱스에 포함(Sparse Index)되므로 매우 경제적입니다.
- **Action**: Query
- **Index**: `GSI_Official_Level_Rank` (또는 `Power_Rank`)
- **KeyCondition**: `PK = "SNAP#2026-02-21"`
- **ScanIndexForward**: `True` (1위부터 오름차순 정렬)

### ② 101위 이하 커스텀 랭킹 조회 (Relative Path)
공식 순위 외의 방대한 데이터를 조회할 때 사용합니다.
- **Action**: Query
- **Index**: `GSI_Internal_Level`
- **KeyCondition**: `PK = "SNAP#2026-02-21"`
- **ScanIndexForward**: `False` (전투력/레벨 높은 순 내림차순)
- **Pagination**: `ExclusiveStartKey`를 사용하여 다음 페이지 조회

**순위 계산 공식:**
$$Rank = (Page \times PageSize) + Index + 1$$

### ③ 특정 유저의 레벨/전투력/랭킹 히스토리 조회 (History Path)
한 유저의 파티션 키 내에 모든 스냅샷이 모여있으므로 매우 빠르게 조회 가능합니다.
- **Action**: Query (Base Table)
- **KeyCondition**: `PK = "USER#<UUID>"` AND `SK begins_with("SNAP#")`
- **ScanIndexForward**: `False` (최신 기록부터 내림차순)
- **특징**: 특정 기간 조회가 필요한 경우 `SK BETWEEN "SNAP#2026-01-01" AND "SNAP#2026-02-21"` 조건을 사용할 수 있습니다.

### ④ 특정 날짜의 레벨/전투력 범위 유저 조회 (Range Path)
GSI의 Sort Key가 숫자(`Level`)임을 활용하여 특정 구간의 유저들을 필터링합니다.
- **Action**: Query
- **Index**: `GSI_Internal_Level`
- **KeyCondition**: `PK = "SNAP#2026-02-21"` AND `Level BETWEEN 50 AND 80`
- **ScanIndexForward**: `False` (범위 내 고레벨자부터 조회)
- **특징**: "당일" 조회 역시 당일 날짜의 스냅샷 데이터를 대상으로 수행하며, 실시간 최신 정보가 필요한 경우 메타데이터가 아닌 해당 시점의 가장 최근 스냅샷을 활용합니다.

### ⑤ 유저 이름으로 UUID 조회 (Lookup Path)
유저의 닉네임(소문자)을 통해 해당 유저의 고유 ID(UUID)를 빠르게 찾을 때 사용합니다.
- **Action**: Query
- **Index**: `GSI_Find_User_By_Name`
- **KeyCondition**: `Name_Lower = "hello"` AND `SK = "METADATA"`
- **Projection**: `Name` (결과로 기본 테이블의 `PK`인 `USER#<UUID>`와 Name을 획득)
