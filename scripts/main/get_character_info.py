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
    from collections.abc import Callable
    from logging import Logger

    from matplotlib.axes import Axes


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


def _find_rank_position(
    uuid: str, target_date: datetime.date, metric: str = "level"
) -> int | None:
    """주어진 UUID의 캐릭터가 특정 날짜의 랭킹에서 몇 위인지 찾는 함수"""

    ranks: list[CharacterData]

    if target_date == misc.get_today():
        ranks = gri.get_current_rank_data(metric=metric)
    else:
        ranks = gri.get_rank_data(target_date, metric=metric)

    for i, item in enumerate(ranks, start=1):
        if item.uuid == uuid:
            return i

    return None


def _save_and_close_chart(dpi: int = 250) -> str:
    image_path: str = "/tmp/image.png" if platform.system() == "Linux" else "image.png"

    plt.savefig(image_path, dpi=dpi, bbox_inches="tight")
    plt.close()

    return image_path


def _build_tick_indices(point_count: int, max_ticks: int) -> list[int]:
    """그래프의 x축에 표시할 날짜 tick의 인덱스를 계산하는 함수"""

    if point_count <= 0:
        return []
    if point_count == 1:
        return [0]

    n_ticks: int = min(max_ticks, point_count)
    if n_ticks <= 1:
        return [point_count - 1]

    tick_interval: int = max(1, (point_count - 1) // (n_ticks - 1))

    return list(range(point_count - 1, -1, -tick_interval))


def _configure_date_axis(ax: Axes, df: pd.DataFrame, max_ticks: int) -> list[int]:
    """
    x축을 날짜 형식으로 설정하고
    표시할 날짜 tick의 인덱스를 계산하여 축에 적용하는 함수
    """

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m월 %d일"))

    tick_indices: list[int] = _build_tick_indices(len(df), max_ticks)

    if tick_indices:
        ticks: list[float] = [
            float(mdates.date2num(df["date"].iloc[i])) for i in tick_indices
        ]

        ax.xaxis.set_major_locator(ticker.FixedLocator(ticks))

    date_range: int = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    plt.xlim(
        df["date"].iloc[0] - pd.Timedelta(days=date_range * 0.02),
        df["date"].iloc[-1] + pd.Timedelta(days=date_range * 0.02),
    )

    return tick_indices


def _style_minimal_axes(ax: Axes) -> None:
    """그래프의 상단, 우측, 좌측 테두리를 제거하는 함수"""

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)


def _compute_smooth_curve(
    df: pd.DataFrame, value_col: str
) -> tuple[np.ndarray, np.ndarray]:
    """PCHIP 보간법을 사용하여 부드러운 곡선을 계산하는 함수"""

    SMOOTH_COEFF: int = 10

    x: np.ndarray = np.arange(len(df["date"]))
    y: np.ndarray = np.array(df[value_col].values, dtype=float)

    x_new: np.ndarray = np.linspace(
        x.min(), x.max(), len(df["date"]) * SMOOTH_COEFF - SMOOTH_COEFF + 1
    )
    y_smooth: np.ndarray = _pchip_interpolate(x, y, x_new)

    return x_new, y_smooth


def _pchip_slopes(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    (x, y)가 주어졌을 때, 각 x[i]에서의 접선 기울기 m[i]를
    Fritsch-Carlson 방법에 따라 계산하여 반환합니다.
    """
    n: int = len(x)
    m: np.ndarray = np.zeros(n)

    # 1) h, delta 계산
    h: np.ndarray = np.diff(x)  # 길이 n-1
    delta: np.ndarray = np.diff(y) / h  # 길이 n-1

    # 내부 점(1 ~ n-2)에 대한 기울기 계산
    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] > 0:  # 부호가 같을 때만 보정
            w1: float = 2 * h[i] + h[i - 1]
            w2: float = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])

        else:
            # 만약 delta[i-1]과 delta[i] 부호가 다르거나
            # 하나라도 0이면 모노토닉 유지 위해 기울기 0
            m[i] = 0.0

    # 양 끝점 기울기
    m[0] = delta[0]
    m[-1] = delta[-1]

    return m


def _pchip_interpolate(x: np.ndarray, y: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    """
    x, y 데이터를 PCHIP 방식으로 보간하여
    새로 주어진 x_new에서의 보간값을 반환
    """

    # y를 float으로 변환
    y = np.array(y, dtype=float)

    # 길이 확인
    if len(x) != len(y):
        raise ValueError("x와 y의 길이가 다름!")
    if np.any(np.diff(x) <= 0):
        raise ValueError("x는 오름차순으로 정렬되어 있어야 합니다.")

    # 각 점에서의 기울기 계산
    m: np.ndarray = _pchip_slopes(x, y)

    # 보간결과를 담을 배열
    y_new: np.ndarray = np.zeros_like(x_new, dtype=float)

    # 구간별로 x_new를 찾아가며 보간
    # 각 x_new[i]에 대해 어느 구간에 속하는지를 찾아서
    # 해당 구간의 3차 Hermite 다항식을 이용해 계산
    for i, xn in enumerate(x_new):
        # xn이 어느 구간에 속하는지 찾기
        if xn <= x[0]:
            # 범위 밖이면, 여기서는 그냥 가장 왼쪽 값으로 extrapolation
            y_new[i] = y[0]
            continue

        elif xn >= x[-1]:
            # 범위 밖이면, 여기서는 가장 오른쪽 값으로 extrapolation
            y_new[i] = y[-1]
            continue

        else:
            idx: int = np.searchsorted(x, xn) - 1

            x0, x1 = x[idx], x[idx + 1]
            y0, y1 = y[idx], y[idx + 1]
            m0, m1 = m[idx], m[idx + 1]
            h = x1 - x0
            t = (xn - x0) / h

            a = y0
            b = m0
            c = (3 * (y1 - y0) / h - 2 * m0 - m1) / h
            d = (m0 + m1 - 2 * (y1 - y0) / h) / (h**2)

            val = a + b * (t * h) + c * (t * h) ** 2 + d * (t * h) ** 3

            y_new[i] = val

    return y_new


def _plot_smoothed_series(
    df: pd.DataFrame,
    value_col: str,
    color: str,
    label: str,
    period: int,
) -> tuple[np.ndarray, np.ndarray]:
    """value_col 열을 PCHIP 보간법으로 부드럽게 그려주는 함수"""

    x_new, y_smooth = _compute_smooth_curve(df, value_col)

    # 기간에 따라 마커 스타일을 다르게 설정
    MARKER_THRESHOLD: int = 30

    plt.plot(
        df["date"],
        df[value_col],
        color=color,
        marker="o" if period <= MARKER_THRESHOLD else ".",
        label=label,
        linestyle="",
    )

    plt.plot(
        df["date"].iloc[0] + pd.to_timedelta(x_new, unit="D"),
        y_smooth,
        color=color,
    )

    return x_new, y_smooth


def _fill_smoothed_area(
    start_date: pd.Timestamp,
    x_new: np.ndarray,
    y_smooth: np.ndarray,
    segment_count: int,
    color: str,
    alpha: float,
    baseline: float | None = None,
) -> None:
    """x_new, y_smooth로 표현된 부드러운 곡선 아래 영역을 색칠하는 함수"""

    SMOOTH_COEFF = 10

    for i in range(segment_count):
        xs: pd.DatetimeIndex = start_date + pd.to_timedelta(
            x_new[i * SMOOTH_COEFF : i * SMOOTH_COEFF + SMOOTH_COEFF + 1], unit="D"
        )

        ys: np.ndarray = y_smooth[
            i * SMOOTH_COEFF : i * SMOOTH_COEFF + SMOOTH_COEFF + 1
        ]

        if baseline is None:
            plt.fill_between(xs, ys, color=color, alpha=alpha)
        else:
            plt.fill_between(xs, ys, baseline, color=color, alpha=alpha)


def _to_time_series_df(rows: list[CharacterData]) -> pd.DataFrame:
    """데이터 리스트를 DataFrame으로 변환하고 date 컬럼을 datetime으로 변환"""

    df: pd.DataFrame = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    return df


def _apply_relative_ylim(
    df: pd.DataFrame,
    value_col: str,
) -> None:
    """값 범위에 비례한 y축 범위를 설정"""

    LOWER_RATIO = 0.1
    UPPER_RATIO = 0.3
    LOWER_MIN = 1.0
    UPPER_MIN = 1.0

    y_min: float = float(df[value_col].min())
    y_max: float = float(df[value_col].max())
    y_range: float = y_max - y_min

    plt.ylim(
        y_min - max(y_range * LOWER_RATIO, LOWER_MIN),
        y_max + max(y_range * UPPER_RATIO, UPPER_MIN),
    )


def _format_level_point_label(df: pd.DataFrame, idx: int) -> str:
    """레벨 포인트 레이블을 'Lv.AB CD.EF%' 형식으로 반환하는 함수"""

    value: float = float(df["level"].iloc[idx])

    return f"Lv.{int(value)}  {(value % 1) * 100:.2f}%"


def _format_power_point_label(df: pd.DataFrame, idx: int) -> str:
    """전투력 포인트 레이블을 'AB,CDE' 형식으로 반환하는 함수"""

    return f"{int(df['power'].iloc[idx]):,}"


def _render_metric_history_chart(
    df: pd.DataFrame,
    value_col: str,
    period: int,
    main_label: str,
    main_color: str,
    fill_color: str,
    fill_alpha: float,
    point_label_formatter: Callable[[pd.DataFrame, int], str],
    extra_series: list[dict] | None = None,
) -> str:
    """그래프를 생성하는 공통 함수"""

    plt.figure(figsize=(10, 4))

    x_new, y_smooth = _plot_smoothed_series(
        df=df,
        value_col=value_col,
        color=main_color,
        label=main_label,
        period=period,
    )

    for series in extra_series or []:
        _plot_smoothed_series(
            df=series["df"],
            value_col=series.get("value_col", value_col),
            color=series["color"],
            label=series["label"],
            period=period,
        )

    _apply_relative_ylim(df, value_col)

    _fill_smoothed_area(
        start_date=df["date"].iloc[0],
        x_new=x_new,
        y_smooth=y_smooth,
        segment_count=len(df) - 1,
        color=fill_color,
        alpha=fill_alpha,
    )

    ax: Axes = plt.gca()
    tick_indices: list[int] = _configure_date_axis(ax, df, max_ticks=5)

    for i in tick_indices:
        plt.annotate(
            point_label_formatter(df, i),
            (df["date"].iloc[i], df[value_col].iloc[i]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8,
        )

    _style_minimal_axes(ax)
    plt.yticks([])
    plt.legend(loc="upper left")

    return _save_and_close_chart()


def _estimate_level(uuid: str, delta_days: int) -> Decimal:
    """
    임시 레벨 계산식
    UUID 기반 편차를 조합해 결정적으로 계산
    """

    # 캐릭터마다 레벨업 속도에 약간의 변동을 주기 위해 시드 고정된 랜덤값 생성
    random.seed(sum(ord(c) for c in uuid))
    coef: float = random.uniform(0.3, 0.7)

    level: Decimal = Decimal(1.0)

    # 지난 날짜만큼 레벨업 시뮬레이션
    for _ in range(delta_days):
        level += Decimal(
            round(
                Decimal(2.5)
                * Decimal(coef + random.uniform(-0.3, 0.8))
                * Decimal(math.cos((float(level) / 205) * math.pi / 2)),
                4,
            )
        )
        level = min(level, Decimal(200.0))

    return level


def _estimate_power(uuid: str, level: Decimal) -> Decimal:
    """
    임시 전투력 계산식
    레벨 기반 성장 + UUID 기반 편차를 조합해 결정적으로 계산
    """

    seed: int = sum(ord(c) for c in uuid)
    level_f: float = float(level)

    base_power: float = (level_f**3) * 18 + (level_f**2) * 140 + level_f * 700
    uuid_bias: float = 0.9 + ((seed % 31) / 100)
    level_band_bias: float = 0.96 + ((int(level_f * 10) + seed) % 9) / 100

    return Decimal(round(base_power * uuid_bias * level_band_bias))


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

    character_data.level = _estimate_level(uuid=uuid, delta_days=delta_days)

    character_data.power = _estimate_power(uuid=uuid, level=character_data.level)

    logger.debug(
        "get_current_character_data complete: "
        f"uuid={uuid} "
        f"date={character_data.date} "
        f"level={character_data.level}",
        f"power={character_data.power}",
    )

    return character_data


def get_character_level_info(
    uuid: str, name: str, period: int, target_date: datetime.date
) -> tuple[str, str | None]:
    """캐릭터 정보 이미지 생성 및 메시지 반환"""

    logger.info(
        "get_character_level_info start: "
        f"uuid={uuid} "
        f"name={name} "
        f"period={period} "
        f"date={target_date}"
    )

    data: list[CharacterData] = get_character_data(uuid, period, target_date)

    if not data:
        logger.warning("get_character_level_info no data: " f"uuid={uuid} name={name}")

        return (
            f"{name}님의 캐릭터 정보가 없어요. 다시 확인해주세요.",
            None,
        )

    # 실제 데이터로 기간 계산
    period_new: int = len(data)

    text_day: str = (
        "지금"
        if target_date == misc.get_today()
        else target_date.strftime("%Y년 %m월 %d일")
    )

    rank: int | None = _find_rank_position(uuid, target_date, metric="level")
    text_rank: str = f"\n레벨 랭킹은 {rank}위에요." if rank is not None else ""

    # 기간이 1이라면 (등록 직후 데이터가 없을 때)
    if period_new == 1:

        return (
            f"{text_day} {name}님의 레벨은 {data[0].level}이에요." + text_rank,
            None,
        )

    # 기간이 1보다 크다면 그래프 생성

    # 레이블 설정
    labels: dict[str, str] = {"default": f"{name}의 캐릭터 레벨"}

    # 그래프에 표시할 추가 시리즈 설정
    extra_series: list[dict] = []

    df: pd.DataFrame = _to_time_series_df(data)

    y_min: float = df["level"].min()
    y_max: float = df["level"].max()
    y_range: float = y_max - y_min

    # 전체 평균
    all_character_avg: list[CharacterData] = get_all_character_avg(
        period_new, target_date
    )
    df_avg: pd.DataFrame = pd.DataFrame(all_character_avg)
    display_avg: bool = len(df_avg) > 1 and not (
        (df_avg["level"].max() < y_min - y_range / 10)
        or (df_avg["level"].min() > y_max + y_range / 3)
    )

    if display_avg:
        df_avg: pd.DataFrame = _to_time_series_df(all_character_avg)
        labels["avg"] = "등록된 전체 캐릭터의 평균 레벨"
        extra_series.append(
            {
                "df": df_avg,
                "value_col": "level",
                "color": "C2",
                "label": labels["avg"],
            }
        )

    # 유사 레벨 평균
    similar_character_avg: list[CharacterData] = get_similar_character_avg(
        period_new,
        target_date,
        # 당일 데이터라면 전날 레벨, 아니라면 그 날 레벨 사용
        float(data[-2 if target_date == misc.get_today() else -1].level),
    )
    df_sim: pd.DataFrame = pd.DataFrame(similar_character_avg)
    display_sim: bool = len(df_sim) > 1 and not (
        (df_sim["level"].max() < y_min - y_range / 10)
        or (df_sim["level"].min() > y_max + y_range / 3)
    )

    if display_sim:
        df_sim: pd.DataFrame = _to_time_series_df(similar_character_avg)
        labels["sim"] = "유사한 레벨의 캐릭터의 평균 레벨"
        extra_series.append(
            {
                "df": df_sim,
                "value_col": "level",
                "color": "C3",
                "label": labels["sim"],
            }
        )

    image_path: str = _render_metric_history_chart(
        df=df,
        value_col="level",
        period=period_new,
        main_label=labels["default"],
        main_color="C0",
        fill_color="#A0DEFF",
        fill_alpha=1,
        point_label_formatter=_format_level_point_label,
        extra_series=extra_series,
    )

    current_level = df["level"].iat[-1]
    l0 = df["level"].iat[0]
    l1 = df["level"].iat[-1]
    level_change = l1 - l0  # type: ignore

    exp_avg, next_lvup, max_lv_day = calc_exp_change(float(l0), float(l1), period_new)  # type: ignore

    text_changed: str = (
        f"{period_new}일간 총 {level_change:.2f}레벨, 매일 평균 {level_change / period_new:.2%} 상승하셨어요!"  # type: ignore
    )
    text_rank: str = f"\n레벨 랭킹은 {rank}위에요." if rank is not None else ""
    # exp_change, next_lvup, max_lv_day
    text_exp: str = (
        (
            f"\n일일 평균 획득 경험치는 {int(exp_avg)}이고, 약 {next_lvup}일 후에 레벨업을 할 것 같아요."
        )
        if next_lvup > 0
        else f"\n일일 평균 획득 경험치는 {int(exp_avg)}이에요."
    )

    msg: str = (
        f"{text_day} {name}님의 레벨은 {current_level:.2f}이고, {text_changed}{text_exp}{text_rank}"
    )

    logger.info(
        "get_character_info complete: "
        f"uuid={uuid} "
        f"name={name} "
        f"points={len(data)} "
        f"image={image_path}"
    )

    return msg, image_path


def get_character_power_info(
    uuid: str, name: str, period: int, target_date: datetime.date
) -> tuple[str, str | None]:
    """캐릭터 전투력 정보 이미지 생성 및 메시지 반환"""

    logger.info(
        "get_character_power_info start: "
        f"uuid={uuid} "
        f"name={name} "
        f"period={period} "
        f"date={target_date}"
    )

    data: list[CharacterData] = get_character_data(uuid, period, target_date)

    if not data:
        logger.warning("get_character_power_info no data: " f"uuid={uuid} name={name}")

        return f"{name}님의 캐릭터 정보가 없어요. 다시 확인해주세요.", None

    period_new: int = len(data)
    text_day: str = (
        "지금"
        if target_date == misc.get_today()
        else target_date.strftime("%Y년 %m월 %d일")
    )

    rank: int | None = _find_rank_position(uuid, target_date, metric="power")
    text_rank: str = f"\n전투력 랭킹은 {rank}위에요." if rank is not None else ""

    # 기간이 1이라면 (등록 직후 데이터가 없을 때)
    if period_new == 1:
        return (
            f"{text_day} {name}님의 전투력은 {int(data[0].power):,}이에요." + text_rank,
            None,
        )

    df: pd.DataFrame = _to_time_series_df(data)

    image_path = _render_metric_history_chart(
        df=df,
        value_col="power",
        period=period_new,
        main_label=f"{name}의 전투력",
        main_color="C1",
        fill_color="#FFE6A7",
        fill_alpha=0.9,
        point_label_formatter=_format_power_point_label,
        extra_series=None,
    )

    current_power = df["power"].iat[-1]
    power_change = df["power"].iat[-1] - df["power"].iat[0]  # type: ignore
    avg_daily_change = power_change / period_new  # type: ignore

    text_changed: str = (
        f"{period_new}일간 총 {int(round(power_change)):+,}, "  # type: ignore
        f"매일 평균 {int(round(avg_daily_change)):+,} 변동했어요."  # type: ignore
    )
    msg = f"{text_day} {name}님의 전투력은 {current_power:,}이고, {text_changed}{text_rank}"

    logger.info(
        "get_character_power_info complete: "
        f"uuid={uuid} "
        f"name={name} "
        f"points={len(data)} "
        f"image={image_path}"
    )

    return msg, image_path


def calc_exp_change(l0: float, l1: float, period: int) -> tuple[float, int, int]:
    """
    레벨 변화량과 기간을 기반으로
    평균 경험치 변화량, 다음 레벨업까지 필요한 일수, 최대 레벨업까지 필요한 일수
    를 계산하는 함수
    """

    exps: list[int] = misc.get_exp_data()

    exp = 0
    for i in range(int(l0), int(l1)):
        exp += exps[i]
    exp += int((l1 % 1) * exps[int(l1)])
    exp -= int((l0 % 1) * exps[int(l0)])

    exp_mean: float = exp / period

    if exp_mean <= 0:
        return exp_mean, 0, 0

    next_lvup: int = int(exps[int(l1)] * (1 - (l1 % 1)) / exp_mean) + 1

    max_exp: float = sum([i for i in exps[int(l1) :]]) + exps[int(l1)] * (1 - (l1 % 1))

    max_day: int = int(max_exp / exp_mean) + 1

    return exp_mean, next_lvup, max_day


def get_charater_rank_history(
    uuid: str,
    name: str,
    period: int,
    target_date: datetime.date,
    rank_type: str = "level",
) -> tuple[str, str | None]:
    """캐릭터 랭킹 정보 이미지 생성 및 메시지 반환"""

    logger.info(
        "get_charater_rank_history start: "
        f"uuid={uuid} "
        f"name={name} "
        f"period={period} "
        f"date={target_date} "
        f"rank_type={rank_type}"
    )

    metric: str = rank_type
    rank_title = "전투력 랭킹" if metric == "power" else "레벨 랭킹"

    today = misc.get_today()
    current_data: list[CharacterData] = (
        gri.get_current_rank_data(metric=metric) if target_date == today else []
    )

    start_date: datetime.date = target_date - datetime.timedelta(days=period - 1)
    target_date_text: str = target_date.strftime("%Y년 %m월 %d일")

    data: list[dict] = []
    if metric == "level":
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

        first_rank_date: datetime.date | None = (
            min(rank_by_date) if rank_by_date else None
        )
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
    else:
        first_rank_date: datetime.date | None = None
        for d in range(period):
            date_value = start_date + datetime.timedelta(days=d)
            if target_date == today and date_value == target_date:
                continue

            day_rank: int | None = None
            day_ranks = gri.get_rank_data(date_value, metric=metric)
            for i, row in enumerate(day_ranks, start=1):
                if row.uuid == uuid:
                    day_rank = i
                    break

            if first_rank_date is None:
                if day_rank is None:
                    continue
                first_rank_date = date_value

            data.append(
                {
                    "rank": day_rank,
                    "date": date_value.strftime("%Y-%m-%d"),
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
            f"date={target_date} "
            f"rank_type={metric}"
        )

        return f"{target_date_text} {name}님의 {rank_title} 정보가 없어요.", None

    # 실제 데이터로 기간 계산
    period = len(data)

    # 기간이 1이라면 (등록 직후 데이터가 없을 때)
    if period == 1:
        text_day: str = "지금" if target_date == today else target_date_text
        cur_rank = data[0]["rank"]
        text_rank: str = (
            f"{name}님의 {rank_title}은 "
            f"{f'{cur_rank}위에요.' if cur_rank and cur_rank < 101 else '순위에 등록되어있지 않아요.'}"
        )
        return f"{text_day} {text_rank}", None

    # 이미지 생성
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    plt.figure(figsize=(10, 4))
    smooth_coeff = 10

    label: str = f"{name}의 {rank_title} 히스토리"

    x_new, y_smooth = _compute_smooth_curve(df, "rank")

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

    _fill_smoothed_area(
        start_date=df["date"].iloc[0],
        x_new=x_new,
        y_smooth=y_smooth,
        segment_count=len(df) - 1,
        color="#A0DEFF",
        alpha=1,
        baseline=101,
    )

    ax = plt.gca()

    tick_indices = _configure_date_axis(ax, df, max_ticks=8)

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

    _style_minimal_axes(ax)
    plt.legend()
    image_path = _save_and_close_chart(dpi=250)

    msg: str = f"{period}일 동안의 {name}님의 {rank_title} 변화를 보여드릴게요."

    logger.info(
        "get_charater_rank_history complete: "
        f"uuid={uuid} "
        f"name={name} "
        f"period={period} "
        f"image={image_path} "
        f"rank_type={metric}"
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

        data.append(
            CharacterData(
                uuid=uuid,
                level=item["Level"],
                date=date,
                power=item["Power"],
            )
        )

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
    print(
        get_character_power_info(
            "ef45c670d0a0426693e1f00831319c32", "ProDays", 30, today
        )
    )
    # print(
    #     get_character_level_info(
    #         "ef45c670d0a0426693e1f00831319c32", "ProDays", 30, today
    #     )
    # )
    # print(get_character_data("steve", 1, 7, today))
    # print(get_similar_character_avg(7, today, 1))

    pass
