import os
import misc
import random
import datetime
import platform
import numpy as np
import pandas as pd

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm

import data_manager as dm
import get_rank_info as gri

plt.style.use("seaborn-v0_8-pastel")
if platform.system() == "Linux":
    font_path = "/opt/NanumSquareRoundEB.ttf"
else:
    font_path = misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf")
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = prop.get_name()

matplotlib.use("Agg")


def get_current_character_data(name):
    data = [
        {"job": "검호", "level": "200"},
        {"job": "검호", "level": "200"},
        {"job": "검호", "level": "200"},
        {"job": "검호", "level": "200"},
        {"job": "검호", "level": "200"},
    ]

    today = misc.get_today()
    base_date = datetime.date(2025, 2, 1)

    delta_days = (today - base_date).days + 1

    random.seed(delta_days + sum(ord(c) for c in name))

    for d in data:
        d["level"] = str(int(d["level"]) + delta_days * 3 + random.randint(0, 3))

    return data


def get_character_info(name, slot, period, default, today):
    data, period = get_character_data(name, slot, period, today)
    name = misc.get_name(name)

    if data == None:
        if default:
            return f"{name}님의 캐릭터 정보가 없어요. 다시 확인해주세요.", None
        return f"{name}님의 {slot}번 캐릭터 정보가 없어요. 다시 확인해주세요.", None

    all_character_avg = get_all_character_avg(period, today)

    if today == misc.get_today():
        similar_character_avg = get_similar_character_avg(period, today, data["level"][-2])
    else:
        similar_character_avg = get_similar_character_avg(period, today, data["level"][-1])

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    y_min = df["level"].min()
    y_max = df["level"].max()
    y_range = y_max - y_min

    df_avg = pd.DataFrame(all_character_avg)
    display_avg = len(df_avg) > 1 and not (
        (df_avg["level"].max() < y_min - 0.1 * y_range) or (df_avg["level"].min() > y_max + 0.3 * y_range)
    )
    if display_avg:
        df_avg["date"] = pd.to_datetime(df_avg["date"])

    df_sim = pd.DataFrame(similar_character_avg)
    display_sim = len(df_sim) > 1 and not (
        (df_sim["level"].max() < y_min - 0.1 * y_range) or (df_sim["level"].min() > y_max + 0.3 * y_range)
    )
    if display_sim:
        df_sim["date"] = pd.to_datetime(df_sim["date"])

    plt.figure(figsize=(10, 4))
    smooth_coeff = 10

    labels = {
        "default": (f"{name}의 캐릭터 레벨" if default else f"{name}의 {slot}번 캐릭터 레벨"),
    }
    if display_avg:
        labels["avg"] = "등록된 전체 캐릭터의 평균 레벨"
    if display_sim:
        labels["sim"] = "유사한 레벨의 캐릭터의 평균 레벨"

    if period == 1:
        plt.plot("date", "level", data=df, color="C0", marker="o", label=labels["default"])

        if display_avg:
            plt.plot("date", "level", data=df_avg, color="C2", marker="o", label=labels["avg"])

    else:
        x = np.arange(len(df["date"]))
        y = df["level"].values

        x_new = np.linspace(x.min(), x.max(), len(df["date"]) * smooth_coeff - smooth_coeff + 1)

        y_smooth = pchip_interpolate(x, y, x_new)

        plt.plot(df["date"], df["level"], color="C0", marker="o", label=labels["default"], linestyle="")
        plt.plot(
            df["date"][0] + pd.to_timedelta(x_new, unit="D"),
            y_smooth,
            color="C0",
        )

        if display_avg:
            x_avg = np.arange(len(df_avg["date"]))
            y_avg = df_avg["level"].values

            x_new_avg = np.linspace(
                x_avg.min(), x_avg.max(), len(df_avg["date"]) * smooth_coeff - smooth_coeff + 1
            )

            y_smooth_avg = pchip_interpolate(x_avg, y_avg, x_new_avg)

            plt.plot(
                df_avg["date"],
                df_avg["level"],
                color="C2",
                marker="o",
                label=labels["avg"],
                linestyle="",
            )
            plt.plot(
                df_avg["date"][0] + pd.to_timedelta(x_new_avg, unit="D"),
                y_smooth_avg,
                color="C2",
            )

        if display_sim:
            x_sim = np.arange(len(df_sim["date"]))
            y_sim = df_sim["level"].values

            x_new_sim = np.linspace(
                x_sim.min(), x_sim.max(), len(df_sim["date"]) * smooth_coeff - smooth_coeff + 1
            )

            y_smooth_sim = pchip_interpolate(x_sim, y_sim, x_new_sim)

            plt.plot(
                df_sim["date"],
                df_sim["level"],
                color="C3",
                marker="o",
                label=labels["sim"],
                linestyle="",
            )
            plt.plot(
                df_sim["date"][0] + pd.to_timedelta(x_new_sim, unit="D"),
                y_smooth_sim,
                color="C3",
            )

    if y_min == y_max:
        plt.ylim(y_max - 1, y_max + 1)
    else:
        plt.ylim(y_min - 0.1 * y_range, y_max + 0.3 * y_range)

    for i in range(len(df) - 1):
        plt.fill_between(
            df["date"][0]
            + pd.to_timedelta(x_new[i * smooth_coeff : i * smooth_coeff + smooth_coeff + 1], unit="D"),
            y_smooth[i * smooth_coeff : i * smooth_coeff + smooth_coeff + 1],
            color="#A0DEFF",
            alpha=1,
        )
        # df["date"][0] + pd.to_timedelta(x_new, unit="D"), y_smooth
        # 0~4, 3~7, 6~10, 9~13, 12~16

    ax = plt.gca()

    # Set date format on x-axis
    date_format = mdates.DateFormatter("%m월 %d일")
    ax.xaxis.set_major_formatter(date_format)
    if period != 1:
        # 표시할 x축 날짜 직접 계산
        n_ticks = min(8, len(df))  # 최대 tick 개수
        tick_interval = max(1, (len(df) - 1) // (n_ticks - 1))  # 간격 계산
        tick_indices = range(len(df) - 1, -1, -tick_interval)  # 마지막 데이터부터 역순으로

        # 실제 데이터 포인트의 날짜만 선택
        ticks = [mdates.date2num(df["date"].iloc[i]) for i in tick_indices]
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
                f'Lv.{df["level"].iloc[i]}',
                (df["date"].iloc[i], df["level"].iloc[i]),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
            )
    else:
        tick = [
            mdates.date2num(df["date"].iloc[0] - pd.Timedelta(days=1)),
            mdates.date2num(df["date"].iloc[0]),
            mdates.date2num(df["date"].iloc[0] + pd.Timedelta(days=1)),
        ]
        ax.xaxis.set_major_locator(ticker.FixedLocator(tick))
        plt.xlim(
            df["date"].iloc[0] - pd.Timedelta(days=1.03),
            df["date"].iloc[0] + pd.Timedelta(days=1.03),
        )
        plt.annotate(
            f'Lv.{df["level"].iloc[0]}',
            (df["date"].iloc[0], df["level"].iloc[0]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    # ax.spines["bottom"].set_visible(False)

    plt.yticks([])
    plt.legend(loc="upper left")

    os_name = platform.system()
    if os_name == "Linux":
        image_path = misc.convert_path("\\tmp\\image.png")
    else:
        image_path = "image.png"

    plt.savefig(image_path, dpi=300, bbox_inches="tight")
    plt.close()

    current_level = df["level"].iat[-1]
    level_change = df["level"].iat[-1] - df["level"].iat[0]

    rank = None
    if today == misc.get_today():
        ranks = gri.get_current_rank_data()
        for i, j in enumerate(ranks):
            if (
                j["name"] == name
                and int(j["level"]) == current_level
                and misc.convert_job(j["job"]) == df["job"].iat[-1]
            ):
                rank = i + 1
                break
    else:
        ranks = gri.get_rank_data(today)
        for i, j in enumerate(ranks):
            if j["name"] == name and j["level"] == current_level and j["job"] == df["job"].iat[-1]:
                rank = j["rank"]
                break

    text_day = "지금" if today == misc.get_today() else today.strftime("%Y년 %m월 %d일")
    text_slot = f"{slot}번 캐릭터 " if not default else ""
    text_changed = f"{period}일간 {level_change}레벨 상승하셨어요!\n" if period != 1 else ""
    text_rank = f"레벨 랭킹은 {rank}위에요." if rank is not None else "레벨 랭킹에는 아직 등록되지 않았어요."

    msg = f"{text_day} {name}님의 {text_slot}레벨은 {current_level}이고, {text_changed}{text_rank}"

    return msg, image_path


def get_character_data(name, slot, period, today):
    """
    data = {'date': ['2025-01-01'], 'level': [Decimal('97')], 'job': [Decimal('1')]}
    """

    if period != 1:
        start_date = today - datetime.timedelta(days=period - 1)

        today = today.strftime("%Y-%m-%d")
        start_date = start_date.strftime("%Y-%m-%d")

        _id = misc.get_id(name)

        db_data = dm.read_data("DailyData", None, {"id": _id, "date-slot": [f"{start_date}#0", f"{today}#4"]})

    data = {"date": [], "level": [], "job": []}
    if period != 1 and db_data:
        for i in db_data:
            date, _slot = i["date-slot"].split("#")
            _slot = int(_slot) + 1

            if _slot == slot:
                data["date"].append(date)
                data["level"].append(int(i["level"]))
                data["job"].append(int(i["job"]))

    if today == misc.get_today().strftime("%Y-%m-%d"):
        today_data = get_current_character_data(name)

        data["date"].append(today)
        data["level"].append(int(today_data[slot - 1]["level"]))
        data["job"].append(misc.convert_job(today_data[slot - 1]["job"]))

    return data if len(data["date"]) != 0 else None, len(data["date"])


def get_all_character_avg(period, today):
    data = {"date": [], "level": []}

    start_date = today - datetime.timedelta(days=period - 1)

    today = today.strftime("%Y-%m-%d")
    start_date = start_date.strftime("%Y-%m-%d")

    db_data = dm.scan_data(
        "DailyData",
        index="date-slot-level-index",
        filter_dict={"date-slot": [f"{start_date}#0", f"{today}#4"]},
    )

    if not db_data:
        return None

    dates = {}

    for i in db_data:
        date, _ = i["date-slot"].split("#")

        if not date in dates.keys():
            dates[date] = []

        dates[date].append(int(i["level"]))

    for date in sorted(dates.keys()):
        data["date"].append(date)
        data["level"].append(sum(dates[date]) / len(dates[date]))

    return data


def get_similar_character_avg(period, today, level):
    data = {"date": [], "level": []}

    start_date = today - datetime.timedelta(days=period - 1)

    today = today.strftime("%Y-%m-%d")
    start_date = start_date.strftime("%Y-%m-%d")

    db_data = dm.scan_data(
        "DailyData",
        index="date-slot-level-index",
        filter_dict={
            "date-slot": [f"{start_date}#0", f"{today}#4"],
        },
    )

    if not db_data:
        return None

    chars = []

    for i in db_data:
        date, slot = i["date-slot"].split("#")
        slot = int(slot)

        todayR = misc.get_today()

        if today == todayR.strftime("%Y-%m-%d"):
            if (
                date == (todayR - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                and (level - 1 <= i["level"] <= level + 1)
                and not (i["id"], slot) in chars
            ):
                chars.append((i["id"], slot))

        else:
            if (
                date == today and (level - 1 <= i["level"] <= level + 1) and not (i["id"], slot) in chars
            ):  # 레벨 범위 이후에 수정
                chars.append((i["id"], slot))

    dates = {}
    for i in db_data:
        date, slot = i["date-slot"].split("#")

        if not date in dates.keys():
            dates[date] = []

        if (i["id"], int(slot)) in chars:
            dates[date].append(int(i["level"]))

    for date in sorted(dates.keys()):
        data["date"].append(date)
        data["level"].append(sum(dates[date]) / len(dates[date]))

    return data


def pchip_slopes(x, y):
    """
    (x, y)가 주어졌을 때, 각 x[i]에서의 접선 기울기 m[i]를
    Fritsch-Carlson 방법에 따라 계산하여 반환합니다.
    """
    n = len(x)
    m = np.zeros(n)

    # 1) h, delta 계산
    h = np.diff(x)  # 길이 n-1
    delta = np.diff(y) / h  # 길이 n-1

    # 내부 점(1 ~ n-2)에 대한 기울기 계산
    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] > 0:  # 부호가 같을 때만 보정
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])
        else:
            # 만약 delta[i-1]과 delta[i] 부호가 다르거나
            # 하나라도 0이면 모노토닉 유지 위해 기울기 0
            m[i] = 0.0

    # 양 끝점 기울기 (여기서는 간단히 1차 근사로 계산)
    m[0] = delta[0]
    m[-1] = delta[-1]

    return m


def pchip_interpolate(x, y, x_new):
    """
    x, y 데이터를 PCHIP 방식으로 보간하여,
    새로 주어진 x_new에서의 보간값을 반환합니다.
    """
    # 길이 확인
    if len(x) != len(y):
        raise ValueError("x와 y의 길이가 달라요!")
    if np.any(np.diff(x) <= 0):
        raise ValueError("x는 오름차순으로 정렬되어 있어야 합니다.")

    # 각 점에서의 기울기 계산
    m = pchip_slopes(x, y)

    # 보간결과를 담을 배열
    y_new = np.zeros_like(x_new, dtype=float)

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
            idx = np.searchsorted(x, xn) - 1

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


if __name__ == "__main__":
    today = datetime.datetime.strptime("2025-03-13", "%Y-%m-%d").date()

    print(get_character_info("prodays", 3, 7, False, today))

    # print(get_character_data("ProDays", 1, 7, day))

    # print(get_all_character_avg(4))

    # print(get_current_character_data("ProDays"))

    pass
