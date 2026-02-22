from __future__ import annotations

import datetime
import math
import platform
import random
from decimal import Decimal
from typing import TYPE_CHECKING

import data_manager as dm
import get_rank_info as gri
import matplotlib
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import misc
import numpy as np
import pandas as pd
from log_utils import get_logger
from models import CharacterData

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)

# 스타일 설정
plt.style.use("seaborn-v0_8-pastel")

# 폰트 설정
# TODO: 폰트 라이센스 확인하고 변경하기
if platform.system() == "Linux":
    font_path: str = "/opt/NanumSquareRoundEB.ttf"
else:
    font_path = misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf")

# 폰트 등록
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = prop.get_name()

# 그래프 백엔드 설정 (서버 환경에서는 GUI 백엔드 대신 'Agg' 사용)
matplotlib.use("Agg")


def get_current_character_data(uuid: str, days_before=0) -> CharacterData:
    """
    최신 캐릭터 정보 가져오기
    오픈 이전에는 임의로 생성해서 반환
    """

    # 날짜 계산
    today: datetime.date = misc.get_today(days_before)
    base_date: datetime.date = datetime.date(2026, 2, 1)

    delta_days: int = (today - base_date).days

    character_data = CharacterData(uuid=uuid, level=Decimal(1.0), date=today)

    # 레벨 계산
    # 캐릭터마다 레벨업 속도에 약간의 변동을 주기 위해 시드 고정된 랜덤값 생성
    random.seed(sum(ord(c) for c in uuid))
    coef: float = random.uniform(0.3, 0.7)

    # 지난 날짜만큼 레벨업 시뮬레이션
    for _ in range(delta_days):
        # 레벨이 200 미만일 때와 이상일 때 레벨업 방식 다르게 적용
        character_data.level += Decimal(
            round(
                Decimal(2.5)
                * Decimal(coef + random.uniform(-0.3, 0.8))
                * Decimal(math.cos((float(character_data.level) / 205) * math.pi / 2)),
                4,
            )
        )
        character_data.level = min(character_data.level, Decimal(200.0))

    logger.debug(
        "get_current_character_data complete: "
        f"uuid={uuid} "
        f"date={character_data.date} "
        f"level={character_data.level}",
    )

    return character_data


def get_character_info(uuid: str, name: str, period: int, target_date: datetime.date):
    """
    캐릭터 정보 이미지 생성 및 메시지 반환
    """

    logger.info(
        "get_character_info start: "
        f"uuid={uuid} "
        f"name={name} "
        f"period={period} "
        f"date={target_date}"
    )

    data: list[CharacterData] = get_character_data(uuid, period, target_date)

    if not data:
        logger.warning("get_character_info no data: " f"uuid={uuid} name={name}")

        return (
            f"{name}님의 캐릭터 정보가 없어요. 다시 확인해주세요.",
            None,
        )

    # 실제 데이터로 기간 계산
    period_new: int = len(data)

    # 기간이 1이라면 (등록 직후 데이터가 없을 때)
    if period_new == 1:
        current_level: Decimal = data[0].level

        ranks: list[CharacterData]
        rank: int | None = None

        # 오늘 날짜라면 실시간 랭킹 데이터에서 순위 찾기
        if target_date == misc.get_today():
            ranks = gri.get_current_rank_data()

            for i, j in enumerate(ranks):
                if j.uuid == uuid:
                    rank = i + 1
                    break

        # 아니라면 해당 날짜 랭킹 데이터에서 순위 찾기
        else:
            ranks = gri.get_rank_data(target_date)

            for i, j in enumerate(ranks):
                if j.uuid == uuid:
                    rank = i + 1
                    break

        text_day: str = (
            "지금"
            if target_date == misc.get_today()
            else target_date.strftime("%Y년 %m월 %d일")
        )
        text_rank: str = f"\n레벨 랭킹은 {rank}위에요." if rank is not None else ""

        return f"{text_day} {name}님의 레벨은 {current_level}이에요." + text_rank, None

    # 기간이 1보다 크다면 그래프 생성
    all_character_avg: list[CharacterData] = get_all_character_avg(
        period_new, target_date
    )

    similar_character_avg: list[CharacterData] = get_similar_character_avg(
        period_new,
        target_date,
        # 당일 데이터라면 전날 레벨, 아니라면 그 날 레벨 사용
        float(data[-2 if target_date == misc.get_today() else -1].level),
    )

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    y_min = df["level"].min()
    y_max = df["level"].max()
    y_range = y_max - y_min

    # avg
    df_avg = pd.DataFrame(all_character_avg)
    display_avg = len(df_avg) > 1 and not (
        (df_avg["level"].max() < y_min - y_range / 10)
        or (df_avg["level"].min() > y_max + y_range / 3)
    )
    if display_avg:
        df_avg["date"] = pd.to_datetime(df_avg["date"])

    # sim
    df_sim = pd.DataFrame(similar_character_avg)
    display_sim = len(df_sim) > 1 and not (
        (df_sim["level"].max() < y_min - y_range / 10)
        or (df_sim["level"].min() > y_max + y_range / 3)
    )
    if display_sim:
        df_sim["date"] = pd.to_datetime(df_sim["date"])

    # 이미지 생성
    plt.figure(figsize=(10, 4))
    smooth_coeff = 10

    # 레이블 설정
    labels: dict[str, str] = {"default": f"{name}의 캐릭터 레벨"}
    if display_avg:
        labels["avg"] = "등록된 전체 캐릭터의 평균 레벨"
    if display_sim:
        labels["sim"] = "유사한 레벨의 캐릭터의 평균 레벨"

    # x, y 데이터 생성
    x = np.arange(len(df["date"]))
    y = np.array(df["level"].values, dtype=float)

    x_new = np.linspace(
        x.min(), x.max(), len(df["date"]) * smooth_coeff - smooth_coeff + 1
    )
    # PCHIP 보간
    y_smooth = misc.pchip_interpolate(x, y, x_new)

    # 점
    plt.plot(
        df["date"],
        df["level"],
        color="C0",
        marker="o" if period_new <= 30 else ".",
        label=labels["default"],
        linestyle="",
    )
    # 선
    plt.plot(
        df["date"][0] + pd.to_timedelta(x_new, unit="D"),
        y_smooth,
        color="C0",
    )

    if display_avg:
        x_avg = np.arange(len(df_avg["date"]))
        y_avg = np.array(df_avg["level"].values, dtype=float)

        x_new_avg = np.linspace(
            x_avg.min(),
            x_avg.max(),
            len(df_avg["date"]) * smooth_coeff - smooth_coeff + 1,
        )
        # PCHIP 보간
        y_smooth_avg = misc.pchip_interpolate(x_avg, y_avg, x_new_avg)

        # 점
        plt.plot(
            df_avg["date"],
            df_avg["level"],
            color="C2",
            marker="o" if period_new <= 30 else ".",
            label=labels["avg"],
            linestyle="",
        )
        # 선
        plt.plot(
            df_avg["date"][0] + pd.to_timedelta(x_new_avg, unit="D"),
            y_smooth_avg,
            color="C2",
        )

    if display_sim:
        x_sim = np.arange(len(df_sim["date"]))
        y_sim = np.array(df_sim["level"].values, dtype=float)

        x_new_sim = np.linspace(
            x_sim.min(),
            x_sim.max(),
            len(df_sim["date"]) * smooth_coeff - smooth_coeff + 1,
        )
        # PCHIP 보간
        y_smooth_sim = misc.pchip_interpolate(x_sim, y_sim, x_new_sim)

        # 점
        plt.plot(
            df_sim["date"],
            df_sim["level"],
            color="C3",
            marker="o" if period_new <= 30 else ".",
            label=labels["sim"],
            linestyle="",
        )
        # 선
        plt.plot(
            df_sim["date"][0] + pd.to_timedelta(x_new_sim, unit="D"),
            y_smooth_sim,
            color="C3",
        )

    if y_min == y_max:  # y 범위가 하나일때 (변동 없을때)
        plt.ylim(y_max - 1, y_max + 1)
    else:
        plt.ylim(y_min - y_range / 10, y_max + y_range / 3)

    for i in range(len(df) - 1):
        # 그래프 영역에 색칠
        plt.fill_between(
            df["date"][0]
            + pd.to_timedelta(
                x_new[i * smooth_coeff : i * smooth_coeff + smooth_coeff + 1], unit="D"
            ),
            y_smooth[i * smooth_coeff : i * smooth_coeff + smooth_coeff + 1],
            color="#A0DEFF",
            alpha=1,
        )
        # df["date"][0] + pd.to_timedelta(x_new, unit="D"), y_smooth
        # 0~4, 3~7, 6~10, 9~13, 12~16

    ax = plt.gca()

    # Set date format on x-axis
    date_format: mdates.DateFormatter = mdates.DateFormatter("%m월 %d일")
    ax.xaxis.set_major_formatter(date_format)
    # 표시할 x축 날짜 직접 계산
    n_ticks = min(5, len(df))  # 최대 tick 개수
    tick_interval = max(1, (len(df) - 1) // (n_ticks - 1))  # 간격 계산
    tick_indices = range(len(df) - 1, -1, -tick_interval)  # 마지막 데이터부터 역순으로

    # 실제 데이터 포인트의 날짜만 선택
    ticks = [float(mdates.date2num(df["date"].iloc[i])) for i in tick_indices]
    ax.xaxis.set_major_locator(ticker.FixedLocator(ticks))

    # x축 범위를 데이터 범위로 제한 (여백 추가)
    date_range = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    plt.xlim(
        df["date"].iloc[0] - pd.Timedelta(days=date_range * 0.02),  # 2% 여백
        df["date"].iloc[-1] + pd.Timedelta(days=date_range * 0.02),
    )

    # 레이블 표시 로직 변경 - 날짜 tick과 동일한 간격 사용
    for i in tick_indices:
        plt.annotate(
            f"Lv.{int(df['level'].iloc[i])}  {(df['level'].iloc[i] % 1) * 100:.2f}%",
            (df["date"].iloc[i], df["level"].iloc[i]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8,
        )

    # 그래프 테두리 설정
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    # ax.spines["bottom"].set_visible(False)

    plt.yticks([])
    plt.legend(loc="upper left")

    os_name = platform.system()
    if os_name == "Linux":
        image_path = "/tmp/image.png"
    else:
        image_path = "image.png"

    plt.savefig(image_path, dpi=250, bbox_inches="tight")
    plt.close()

    current_level = df["level"].iat[-1]
    l0 = df["level"].iat[0]
    l1 = df["level"].iat[-1]
    level_change = l1 - l0

    exp_avg, next_lvup, max_lv_day = calc_exp_change(float(l0), float(l1), period_new)

    rank = None
    if target_date == misc.get_today():
        ranks = gri.get_current_rank_data()
        for i, j in enumerate(ranks):
            if j.uuid == uuid:
                rank = i + 1
                break
    else:
        ranks = gri.get_rank_data(target_date)

        if not ranks:
            rank = None
        else:
            for i, j in enumerate(ranks):
                if j.uuid == uuid:
                    rank = i + 1
                    break

    text_day = (
        "지금"
        if target_date == misc.get_today()
        else target_date.strftime("%Y년 %m월 %d일")
    )
    text_changed = f"{period_new}일간 총 {level_change:.2f}레벨, 매일 평균 {level_change / period_new:.2%} 상승하셨어요!"
    text_rank = f"\n레벨 랭킹은 {rank}위에요." if rank is not None else ""
    # exp_change, next_lvup, max_lv_day
    text_exp = f"\n일일 평균 획득 경험치는 {int(exp_avg)}이고, 약 {next_lvup}일 후에 레벨업을 할 것 같아요."

    msg = f"{text_day} {name}님의 레벨은 {current_level:.2f}이고, {text_changed}{text_exp}{text_rank}"

    logger.info(
        "get_character_info complete: "
        f"uuid={uuid} "
        f"name={name} "
        f"points={len(data)} "
        f"image={image_path}"
    )

    return msg, image_path


def calc_exp_change(l0: float, l1: float, period: int) -> tuple[float, int, int]:
    exps = misc.get_exp_data()

    exp = 0
    for i in range(int(l0), int(l1)):
        exp += exps[i]
    exp += int((l1 % 1) * exps[int(l1)])
    exp -= int((l0 % 1) * exps[int(l0)])

    exp_mean = exp / period

    next_lvup = int(exps[int(l1)] * (1 - (l1 % 1)) / exp_mean) + 1

    max_exp = sum([i for i in exps[int(l1) :]]) + exps[int(l1)] * (1 - (l1 % 1))

    max_day = int(max_exp / exp_mean) + 1

    return exp_mean, next_lvup, max_day


def get_charater_rank_history(
    uuid: str, name: str, period: int, target_date: datetime.date
):
    logger.info(
        "get_charater_rank_history start: "
        f"uuid={uuid} "
        f"name={name} "
        f"period={period} "
        f"date={target_date}"
    )

    today = misc.get_today()
    current_data: list[CharacterData] = (
        gri.get_current_rank_data() if target_date == today else []
    )

    start_date: datetime.date = target_date - datetime.timedelta(days=period - 1)
    target_date_text: str = target_date.strftime("%Y년 %m월 %d일")

    history_items, _ = dm.manager.get_user_snapshot_history(
        uuid=uuid,
        start_date=start_date,
        end_date=target_date,
    )

    rank_by_date: dict[datetime.date, int | None] = {}
    for item in history_items:
        sk = item.get("SK")
        if not isinstance(sk, str) or not sk.startswith("SNAP#"):
            continue

        date_value = datetime.datetime.strptime(
            sk.removeprefix("SNAP#"), "%Y-%m-%d"
        ).date()
        rank = item.get("Level_Rank")
        if rank is None:
            continue

        rank_by_date[date_value] = int(rank)

    first_rank_date: datetime.date | None = min(rank_by_date) if rank_by_date else None
    data: list[dict] = []
    for d in range(period):
        date_value = start_date + datetime.timedelta(days=d)
        if first_rank_date is None:
            continue
        if target_date == today and date_value == target_date:
            continue
        if first_rank_date and date_value < first_rank_date:
            continue

        date_str = date_value.strftime("%Y-%m-%d")
        data.append(
            {
                "rank": rank_by_date.get(date_value),
                "date": date_str,
            }
        )

    if target_date == today:
        rank = 101
        for i, item in enumerate(current_data):
            if item.uuid == uuid:
                rank = i + 1
                break

        data.append(
            {
                "rank": rank,
                "date": target_date,
            }
        )

    if not data:
        logger.warning(
            "get_charater_rank_history no data: "
            f"uuid={uuid} "
            f"name={name} "
            f"date={target_date}"
        )

        return f"{target_date_text} {name}님의 랭킹 정보가 없어요.", None

    # 실제 데이터로 기간 계산
    period = len(data)

    # 기간이 1이라면 (등록 직후 데이터가 없을 때)
    if period == 1:
        text_day: str = "지금" if target_date == today else target_date_text
        cur_rank = data[0]["rank"]
        text_rank: str = (
            f"{name}님의 랭킹은 {f'{cur_rank}위에요.' if cur_rank else '순위에 등록되어있지 않아요.'}"
        )
        return f"{text_day} {text_rank}", None

    # 이미지 생성
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    plt.figure(figsize=(10, 4))
    smooth_coeff = 10

    label: str = f"{name}의 랭킹 히스토리"

    x = np.arange(len(df["date"]))
    y = np.array(df["rank"], dtype=float)

    x_new = np.linspace(
        x.min(), x.max(), len(df["date"]) * smooth_coeff - smooth_coeff + 1
    )

    y_smooth = misc.pchip_interpolate(x, y, x_new)

    plt.plot(
        df["date"][0] + pd.to_timedelta(x_new, unit="D"),
        y_smooth,
        color="C0",
    )
    plt.plot(
        df["date"][df["rank"].notna()],
        df["rank"][df["rank"].notna()],
        color="C0",
        marker="o" if period <= 50 else ".",
        label=label,
        linestyle="",
    )
    plt.plot(
        df["date"][df["rank"].isna()],
        df["rank"][df["rank"].isna()],
        color="C2",
        marker="o" if period <= 50 else ".",
        linestyle="",
    )

    ylim = (min(df["rank"].max() + 5, 102), max(df["rank"].min() - 5, -1))
    plt.ylim(ylim)

    for i in range(len(df) - 1):
        plt.fill_between(
            df["date"][0]
            + pd.to_timedelta(
                x_new[i * smooth_coeff : i * smooth_coeff + smooth_coeff + 1], unit="D"
            ),
            y_smooth[i * smooth_coeff : i * smooth_coeff + smooth_coeff + 1],
            101,
            color="#A0DEFF",
            alpha=1,
        )
        # df["date"][0] + pd.to_timedelta(x_new, unit="D"), y_smooth
        # 0~4, 3~7, 6~10, 9~13, 12~16

    ax = plt.gca()

    # Set date format on x-axis
    date_format = mdates.DateFormatter("%m월 %d일")
    ax.xaxis.set_major_formatter(date_format)
    # 표시할 x축 날짜 직접 계산
    n_ticks = min(8, len(df))  # 최대 tick 개수
    tick_interval = max(1, (len(df) - 1) // (n_ticks - 1))  # 간격 계산
    tick_indices = range(len(df) - 1, -1, -tick_interval)  # 마지막 데이터부터 역순으로

    # 실제 데이터 포인트의 날짜만 선택
    ticks = [float(mdates.date2num(df["date"].iloc[i])) for i in tick_indices]
    ax.xaxis.set_major_locator(ticker.FixedLocator(ticks))

    # x축 범위를 데이터 범위로 제한 (여백 추가)
    date_range = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    plt.xlim(
        df["date"].iloc[0] - pd.Timedelta(days=date_range * 0.02),  # 2% 여백
        df["date"].iloc[-1] + pd.Timedelta(days=date_range * 0.02),
    )

    # 레이블 표시 로직 변경 - 날짜 tick과 동일한 간격 사용
    for i in tick_indices:
        plt.annotate(
            f"{df['rank'].iloc[i]}위" if df["rank"].iloc[i] < 101 else "N/A",
            (df["date"].iloc[i], df["rank"].iloc[i]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
        )

    # 최고 랭킹에 텍스트 추가
    if min(df["rank"]) < 101:
        date = int(df["rank"].idxmin())

        if date not in tick_indices:
            plt.annotate(
                f"{min(df['rank'])}위",
                (df["date"].iloc[date], df["rank"].min()),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
            )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    # ax.spines["bottom"].set_visible(False)

    plt.yticks([])
    plt.legend()

    os_name = platform.system()
    if os_name == "Linux":
        image_path = "/tmp/image.png"
    else:
        image_path = "image.png"

    plt.savefig(image_path, dpi=250, bbox_inches="tight")
    plt.close()

    msg: str = f"{period}일 동안의 {name}님의 랭킹 변화를 보여드릴게요."

    logger.info(
        "get_charater_rank_history complete: "
        f"uuid={uuid} "
        f"name={name} "
        f"period={period} "
        f"image={image_path}"
    )

    return msg, image_path


def _get_internal_level_rows(target_date: datetime.date) -> list[dict]:
    rows: list[dict] = []
    last_evaluated_key = None

    while True:
        page, last_evaluated_key = dm.manager.get_internal_level_page(
            snapshot_date=target_date,
            page_size=200,
            exclusive_start_key=last_evaluated_key,
        )
        if not page:
            break

        rows.extend(page)
        if not last_evaluated_key:
            break

    return rows


def get_character_data(
    uuid: str, period: int, target_date: datetime.date
) -> list[CharacterData]:
    """
    특정 기간 동안의 캐릭터 정보 가져오기
    """

    logger.debug(
        "get_character_data start: "
        f"uuid={uuid} "
        f"period={period} "
        f"target_date={target_date}"
    )

    # 시작 날짜 계산
    start_date: datetime.date = target_date - datetime.timedelta(days=period - 1)

    db_data, _ = dm.manager.get_user_snapshot_history(
        uuid=uuid,
        start_date=start_date,
        end_date=target_date,
    )

    data: list[CharacterData] = []

    for item in sorted(db_data, key=lambda row: row.get("SK", "")):
        sk = item.get("SK")
        if not isinstance(sk, str) or not sk.startswith("SNAP#"):
            continue
        if "Level" not in item:
            continue

        date = datetime.datetime.strptime(sk.removeprefix("SNAP#"), "%Y-%m-%d").date()
        data.append(CharacterData(uuid=uuid, level=item["Level"], date=date))

    # 당일 데이터라면 실시간으로 레벨 정보 가져와서 추가
    if target_date == misc.get_today() and (not data or data[-1].date != target_date):
        today_data: CharacterData = get_current_character_data(uuid=uuid)
        data.append(today_data)

    logger.debug(
        "get_character_data complete: "
        f"uuid={uuid} "
        f"points={len(data)} "
        f"target_date={target_date}"
    )

    return data


def get_all_character_avg(
    period: int, target_date: datetime.date
) -> list[CharacterData]:
    data: list[CharacterData] = []

    start_date: datetime.date = target_date - datetime.timedelta(days=period - 1)
    for d in range(period):
        date_value = start_date + datetime.timedelta(days=d)
        rows = _get_internal_level_rows(date_value)
        levels = [row["Level"] for row in rows if "Level" in row]
        if not levels:
            continue

        avg_level = Decimal(round(float(sum(levels) / len(levels)), 4))
        data.append(
            CharacterData(
                uuid="avg",
                level=avg_level,
                date=date_value,
            )
        )

    return data


def get_similar_character_avg(
    period: int, target_date: datetime.date, level: float
) -> list[CharacterData]:
    data: list[CharacterData] = []

    start_date: datetime.date = target_date - datetime.timedelta(days=period - 1)

    levels_by_date: dict[datetime.date, list[tuple[str, Decimal]]] = {}
    for d in range(period):
        date_value = start_date + datetime.timedelta(days=d)
        rows = _get_internal_level_rows(date_value)

        normalized: list[tuple[str, Decimal]] = []
        for row in rows:
            pk = row.get("PK")
            if not isinstance(pk, str) or "Level" not in row:
                continue
            normalized.append((dm.manager.uuid_from_user_pk(pk), row["Level"]))

        if normalized:
            levels_by_date[date_value] = normalized

    if not levels_by_date:
        return []

    today = misc.get_today()
    base_date = (
        today - datetime.timedelta(days=1) if target_date == today else target_date
    )
    base_rows = levels_by_date.get(base_date, [])
    if not base_rows:
        return []

    MAX_LEVEL_RANGE = 10
    MIN_CHARACTER_COUNT = 10
    characters: set[str] = set()
    for level_range in range(1, MAX_LEVEL_RANGE + 1):
        characters = {
            uuid
            for uuid, item_level in base_rows
            if abs(float(item_level) - level) <= level_range
        }
        if len(characters) >= MIN_CHARACTER_COUNT:
            break

    if not characters:
        return []

    for date_value in sorted(levels_by_date):
        selected_levels = [
            item_level
            for uuid, item_level in levels_by_date[date_value]
            if uuid in characters
        ]
        if not selected_levels:
            continue

        avg_level = Decimal(
            round(float(sum(selected_levels) / len(selected_levels)), 4)
        )
        data.append(
            CharacterData(
                uuid="sim",
                level=avg_level,
                date=date_value,
            )
        )

    return data


if __name__ == "__main__":
    # today = datetime.datetime.strptime("2025-03-29", "%Y-%m-%d").date()
    today = misc.get_today()

    # print(get_charater_rank_history("abca", 1, 10, today))
    # print(get_character_info("prodays", 2, 10, today))
    print(get_current_character_data("1mkr", -26))
    # print(get_character_data("steve", 1, 7, today))
    # print(get_similar_character_avg(7, today, 1))

    pass
