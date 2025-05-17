import misc
import random
import datetime
import platform
import numpy as np
import pandas as pd
from decimal import Decimal

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm

import misc
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


def get_current_character_data(name, days_before=0):

    data = [
        {"job": "검호", "level": Decimal(1.0)},
        {"job": "검호", "level": Decimal(1.0)},
        {"job": "검호", "level": Decimal(1.0)},
        {"job": "검호", "level": Decimal(1.0)},
        {"job": "검호", "level": Decimal(1.0)},
    ]

    today = misc.get_today(days_before)
    base_date = datetime.date(2025, 1, 1)

    delta_days = (today - base_date).days

    name = misc.get_name(name=name)
    if name is None:
        return None

    for i, d in enumerate(data):
        random.seed(sum(ord(c) for c in name.lower()) + i + 1)
        coef = random.uniform(0.3, 0.7)

        for _ in range(delta_days):
            d["level"] += Decimal(
                round(
                    40
                    / (d["level"] ** Decimal(0.5))
                    / (i + 2)
                    * Decimal(coef + random.uniform(-0.3, 0.3)),
                    4,
                )
            )

    return data


def get_character_info(name, slot, period, today):
    if slot is None:
        slot = misc.get_main_slot(name)

    data = get_character_data(name, slot, period, today)
    name = misc.get_name(name)

    default = slot == 1

    if data == None:
        return (
            (
                f"{name}님의 "
                + (f"{slot}번" if not default else "")
                + " 캐릭터 정보가 없어요. 다시 확인해주세요."
            ),
            None,
        )

    period = len(data["date"])

    if period == 1:  # 등록 직후 데이터가 없을 때
        current_level = data["level"][0]

        rank = None
        if today == misc.get_today():
            ranks = gri.get_current_rank_data()
            for i, j in enumerate(ranks):
                if (
                    j["name"] == name
                    and -0.1 < j["level"] - current_level < 0.1
                    and misc.convert_job(j["job"]) == data["job"][0]
                ):
                    rank = i + 1
                    break
        else:
            ranks = gri.get_rank_data(today)

            if ranks is None:
                rank = None
            else:
                for i, j in enumerate(ranks):
                    if (
                        j["name"] == name
                        and -0.1 < j["level"] - current_level < 0.1
                        and j["job"] == data["job"][0]
                    ):
                        rank = j["rank"]
                        break

        text_day = (
            "지금" if today == misc.get_today() else today.strftime("%Y년 %m월 %d일")
        )
        text_rank = f"\n레벨 랭킹은 {rank}위에요." if rank is not None else ""

        return f"{text_day} {name}님의 레벨은 {current_level}이에요." + text_rank, None

    all_character_avg = get_all_character_avg(period, today)

    if today == misc.get_today():
        similar_character_avg = (
            get_similar_character_avg(period, today, data["level"][-2])
            if period > 1
            else None
        )
    else:
        similar_character_avg = get_similar_character_avg(
            period, today, data["level"][-1]
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
    labels = {
        "default": (
            f"{name}의 캐릭터 레벨" if default else f"{name}의 {slot}번 캐릭터 레벨"
        ),
    }
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
        marker="o" if period <= 30 else ".",
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
            marker="o" if period <= 30 else ".",
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
            marker="o" if period <= 30 else ".",
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
    date_format = mdates.DateFormatter("%m월 %d일")
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
            f'Lv.{int(df["level"].iloc[i])}  {(df["level"].iloc[i] % 1) * 100:.2f}%',
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
        image_path = misc.convert_path("\\tmp\\image.png")
    else:
        image_path = "image.png"

    plt.savefig(image_path, dpi=300, bbox_inches="tight")
    plt.close()

    current_level = df["level"].iat[-1]
    l0 = df["level"].iat[0]
    l1 = df["level"].iat[-1]
    level_change = l1 - l0

    exp_change, next_lvup, max_lv_day = calc_exp_change(float(l0), float(l1), period)

    rank = None
    if today == misc.get_today():
        ranks = gri.get_current_rank_data()
        for i, j in enumerate(ranks):
            if (
                j["name"] == name
                and int(j["level"]) == int(current_level)
                and misc.convert_job(j["job"]) == df["job"].iat[-1]
            ):
                rank = i + 1
                break
    else:
        ranks = gri.get_rank_data(today)

        if ranks is None:
            rank = None
        else:
            for i, j in enumerate(ranks):
                if (
                    j["name"] == name
                    and int(j["level"]) == int(current_level)
                    and j["job"] == df["job"].iat[-1]
                ):
                    rank = j["rank"]
                    break

    text_day = "지금" if today == misc.get_today() else today.strftime("%Y년 %m월 %d일")
    text_slot = f"{slot}번 캐릭터 " if not default else ""
    text_changed = (
        f"{period}일간 {level_change:.2f}레벨 상승하셨어요!" if period != 1 else ""
    )
    text_rank = f"\n레벨 랭킹은 {rank}위에요." if rank is not None else ""
    # exp_change, next_lvup, max_lv_day
    text_exp = f"\n일일 평균 획득 경험치는 {exp_change}이고, 약 {next_lvup}일 후에 레벨업을 할 것 같아요.\n만렙까지는 약 {max_lv_day}일 남았어요."

    msg = f"{text_day} {name}님의 {text_slot}레벨은 {current_level:.2f}이고, {text_changed}{text_exp}{text_rank}"

    return msg, image_path


def calc_exp_change(l0, l1, period):
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

    return exp, next_lvup, max_day


def get_charater_rank_history(name, period, today):
    name = misc.get_name(name)

    if name is None:
        return f"{name}님의 랭킹 정보가 없어요.", None

    current_data = gri.get_current_rank_data() if today == misc.get_today() else None

    _id = misc.get_id(name=name)

    start_date = today - datetime.timedelta(days=period - 1)
    today_text = today.strftime("%Y년 %m월 %d일")
    today = today.strftime("%Y-%m-%d")
    start_date = start_date.strftime("%Y-%m-%d")

    data = dm.read_data(
        "Ranks",
        index="id-date-index",
        condition_dict={"id": _id, "date": [start_date, today]},
    )

    if data is None:
        data = []

    for i, j in enumerate(data):
        del data[i]["level"]
        del data[i]["job"]
        del data[i]["id"]

        for i1, j1 in enumerate(data.copy()):
            if j["date"] == j1["date"] and j["rank"] > j1["rank"]:
                del data[i]
                break

    for i, j in enumerate(data):
        data[i]["rank"] = 101 - int(j["rank"])

    if current_data is not None:
        for i, j in enumerate(current_data):  # job level name
            if j["name"].lower() == name.lower():
                data.append(
                    {
                        "rank": 100 - i,
                        "date": today,
                    }
                )
                break

    period = len(set([i["date"] for i in data]))

    if period == 0:
        return f"{name}님의 랭킹 정보가 없어요.", None

    elif period == 1:  # 등록 직후 데이터가 없을 때
        text_day = (
            "지금" if today == misc.get_today().strftime("%Y-%m-%d") else today_text
        )
        text_rank = f"{name}님의 랭킹은 {101 - data[0]['rank']}위에요."
        return f"{text_day} {text_rank}", None

    # 이미지 생성
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    plt.figure(figsize=(10, 4))
    smooth_coeff = 10

    label = f"{name}의 랭킹 히스토리"

    x = np.arange(len(df["date"]))
    y = np.array(df["rank"].values, dtype=float)

    x_new = np.linspace(
        x.min(), x.max(), len(df["date"]) * smooth_coeff - smooth_coeff + 1
    )

    y_smooth = misc.pchip_interpolate(x, y, x_new)

    plt.plot(
        df["date"],
        df["rank"],
        color="C0",
        marker="o" if period <= 50 else ".",
        label=label,
        linestyle="",
    )
    plt.plot(
        df["date"][0] + pd.to_timedelta(x_new, unit="D"),
        y_smooth,
        color="C0",
    )

    plt.ylim(df["rank"].min() - 5, df["rank"].max() + 5)

    for i in range(len(df) - 1):
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
            f'{101 - df["rank"].iloc[i]}위',
            (df["date"].iloc[i], df["rank"].iloc[i]),
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

    msg = f"{period}일 동안의 {name}님의 랭킹 변화를 보여드릴게요."

    return msg, image_path


def get_character_data(name, slot, period, today):
    """
    data = {'date': ['2025-01-01'], 'level': [Decimal('97')], 'job': [Decimal('1')]}
    """

    start_date = today - datetime.timedelta(days=period - 1)

    today = today.strftime("%Y-%m-%d")
    start_date = start_date.strftime("%Y-%m-%d")

    _id = misc.get_id(name)

    db_data = dm.read_data(
        "DailyData", None, {"id": _id, "date-slot": [f"{start_date}#0", f"{today}#4"]}
    )

    data = {"date": [], "level": [], "job": []}
    if db_data:
        for i in db_data:
            date, _slot = i["date-slot"].split("#")
            _slot = int(_slot) + 1

            if _slot == slot:
                data["date"].append(date)
                data["level"].append(i["level"])
                data["job"].append(int(i["job"]))

    if today == misc.get_today().strftime("%Y-%m-%d"):
        today_data = get_current_character_data(name)

        if today_data is not None:
            data["date"].append(today)
            data["level"].append(today_data[slot - 1]["level"])
            data["job"].append(misc.convert_job(today_data[slot - 1]["job"]))

    return data if len(data["date"]) != 0 else None


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

        dates[date].append(i["level"])

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
    level_range = 5

    for i in db_data:
        date, slot = i["date-slot"].split("#")
        slot = int(slot)

        todayR = misc.get_today()

        if today == todayR.strftime("%Y-%m-%d"):
            if (
                date == (todayR - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                and (-level_range <= i["level"] - level <= level_range)
                and not (i["id"], slot) in chars
            ):
                chars.append((i["id"], slot))

        else:
            if (
                date == today
                and (-level_range <= i["level"] - level <= level_range)
                and not (i["id"], slot) in chars
            ):  # 레벨 범위 이후에 수정
                chars.append((i["id"], slot))

    dates = {}
    for i in db_data:
        date, slot = i["date-slot"].split("#")

        if not date in dates.keys():
            dates[date] = []

        if (i["id"], int(slot)) in chars:
            dates[date].append(i["level"])

    for date in sorted(dates.keys()):
        if dates[date]:
            data["date"].append(date)
            data["level"].append(sum(dates[date]) / len(dates[date]))

    return data


if __name__ == "__main__":
    # today = datetime.datetime.strptime("2025-03-29", "%Y-%m-%d").date()
    today = misc.get_today()

    # print(get_charater_rank_history("prodays", 5, today))
    print(get_character_info("prodays", None, 1, today))
    # print(get_current_character_data("ProDays"))
    # print(get_character_data("steve", 1, 7, today))

    pass
