import os
import time
import random
import datetime
import platform
import requests
import threading
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm

import misc
import data_manager
import register_player

plt.style.use("seaborn-v0_8-pastel")
if platform.system() == "Linux":
    font_path = "/opt/NanumSquareRoundEB.ttf"
else:
    font_path = misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf")
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = prop.get_name()

matplotlib.use("Agg")


def download_image(url, num, list_name):
    response = requests.get(url)

    os_name = platform.system()
    if os_name == "Linux":
        head_path = misc.convert_path(f"\\tmp\\player_heads\\player{num}.png")
    else:
        head_path = misc.convert_path(f"assets\\player_heads\\player{num}.png")

    with open(head_path, "wb") as file:
        file.write(response.content)
    list_name[num] = head_path


def get_rank_data(day, page=0):
    data = data_manager.read_data("Ranks", condition_dict={"date": day.strftime("%Y-%m-%d")})

    for i, j in enumerate(data):
        data[i]["rank"] = int(j["rank"])
        data[i]["id"] = int(j["id"])
        data[i]["job"] = int(j["job"])
        data[i]["level"] = int(j["level"])
        data[i]["name"] = misc.get_name(id=j["id"])

    return data if page == 0 else data[page * 10 - 10 : page * 10]


def get_current_rank_data(page=0) -> dict:
    """
    현재 전체 캐릭터 랭킹 데이터 반환
    {"name": "ProDays", "job": "검호", "level": "100"}
    """

    data = [
        {"level": "200", "job": "검호", "name": "ProDays"},
        {"level": "199", "job": "검호", "name": "Aventurine_0"},
        {"level": "198", "job": "매화", "name": "heekp"},
        {"level": "197", "job": "매화", "name": "krosh0127"},
        {"level": "196", "job": "살수", "name": "_IIN"},
        {"level": "195", "job": "살수", "name": "YOUKONG"},
        {"level": "194", "job": "검호", "name": "ino2423"},
        {"level": "193", "job": "매화", "name": "Route88"},
        {"level": "192", "job": "검호", "name": "ljinsoo"},
        {"level": "191", "job": "살수", "name": "ggameee"},
        {"level": "190", "job": "살수", "name": "Lemong_0"},
        {"level": "189", "job": "매화", "name": "1yeons"},
        {"level": "188", "job": "도제", "name": "sungchanmom"},
        {"level": "187", "job": "술사", "name": "tmdwns0818"},
        {"level": "186", "job": "도사", "name": "poro_rany"},
        {"level": "185", "job": "도제", "name": "Master_Rakan_"},
        {"level": "184", "job": "도제", "name": "Protect_Choco"},
        {"level": "183", "job": "빙궁", "name": "LGJ20000"},
        {"level": "182", "job": "도사", "name": "1mkr"},
        {"level": "181", "job": "귀궁", "name": "Kozi0518"},
        {"level": "180", "job": "술사", "name": "roadhyeon03"},
        {"level": "179", "job": "술사", "name": "aaqq2005y"},
        {"level": "178", "job": "술사", "name": "spemdnjs"},
        {"level": "177", "job": "도제", "name": "Moncler02"},
        {"level": "176", "job": "도사", "name": "Welcome_Pasta"},
        {"level": "175", "job": "도사", "name": "world_3034"},
        {"level": "174", "job": "빙궁", "name": "ArtBeat"},
        {"level": "173", "job": "빙궁", "name": "TinySlayers"},
        {"level": "172", "job": "귀궁", "name": "neoreow"},
        {"level": "171", "job": "빙궁", "name": "d_capo"},
    ]

    today = misc.get_today()
    base_date = datetime.date(2025, 2, 1)

    delta_days = (today - base_date).days + 1

    random.seed(delta_days)

    for d in data:
        d["level"] = str(int(d["level"]) + delta_days * 3 + random.randint(0, 3))

    data = sorted(data, key=lambda x: int(x["level"]), reverse=True)

    return data[page * 10 - 10 : page * 10] if page != 0 else data


def get_rank_info(page, period, today):
    data = {
        "Rank": range(page * 10 - 9, page * 10 + 1),
        "Name": [],
        "Level": [],
        "Job": [],
        "Change": [],
    }

    if today == misc.get_today():
        current_data = get_current_rank_data(page)
    else:
        current_data = get_rank_data(today, page)

    # 실시간 랭킹 데이터를 가져와서 data에 추가
    for i in range(10):
        name = current_data[i]["name"]  # 닉네임 변경 반영한 최신 닉네임
        data["Name"].append(name)
        data["Level"].append(current_data[i]["level"])
        data["Job"].append(current_data[i]["job"])

        user_id = misc.get_id(name=name)

        if user_id is None:  # 1. 등록x -> 등록 2. 닉네임 변경 -> 등록
            register_player.register_player(name)
            user_id = misc.get_id(name=name)

        prev_date = today - datetime.timedelta(days=1)
        prev_date_str = prev_date.strftime("%Y-%m-%d")

        prev_rank = data_manager.read_data("Ranks", "id-date-index", {"id": user_id, "date": prev_date_str})[
            0
        ]["rank"]

        if prev_rank is None:
            data["Change"].append(None)
        else:
            data["Change"].append(prev_rank - (i + page * 10 - 9))

    avatar_images = [""] * 10

    os_name = platform.system()
    if os_name == "Linux":
        head_path = misc.convert_path(f"\\tmp\\player_heads\\player.png")
    else:
        head_path = misc.convert_path(f"assets\\player_heads\\player.png")

    if not os.path.exists(os.path.dirname(head_path)):
        os.makedirs(os.path.dirname(head_path))

    # 10개의 스레드 생성
    threads = []
    for i in range(10):
        url = f"https://mineskin.eu/helm/{data['Name'][i]}/100.png"
        thread = threading.Thread(
            target=download_image,
            args=(url, i, avatar_images),
        )
        threads.append(thread)
        thread.start()

    # 모든 스레드가 완료될 때까지 대기
    for thread in threads:
        thread.join()

    header_text = ["순위", "닉네임", "레벨", "직업", "변동"]
    header_widths = [160, 500, 280, 240, 240]

    header_height = 100
    row_height = 100
    avatar_size = 80
    width, height = sum(header_widths), row_height * 10 + header_height + 8

    gray = (200, 200, 200)
    blue = (160, 200, 255)
    aqua = (190, 230, 255)
    light_blue = (240, 245, 255)

    rank_info_image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(rank_info_image)

    draw.rectangle(
        [
            (0, 0),
            (width, header_height),
        ],
        fill=aqua,
        width=2,
    )

    if os_name == "Linux":
        font = ImageFont.truetype("/opt/NanumSquareRoundEB.ttf", 40)
    else:
        font = ImageFont.truetype(misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf"), 40)

    x_offset = -10
    for i, text in enumerate(header_text):
        if i == 0:
            x = x_offset + 34
        elif i == 1:
            x = x_offset + 110
        elif i == 2:
            x = x_offset + 90
        elif i == 3:
            x = x_offset + 66
        elif i == 4:
            x = x_offset + 68

        draw.text((x + 24, 30), text, fill="black", font=font)
        x_offset += header_widths[i]

    for i in range(len(data["Rank"])):
        row = {
            "Rank": str(data["Rank"][i]),
            "Name": data["Name"][i],
            "Level": str(data["Level"][i]),
            "Job": data["Job"][i] if isinstance(data["Job"][i], str) else misc.convert_job(data["Job"][i]),
            "Change": data["Change"][i],
        }

        y_offset = header_height + i * row_height
        text_y_offset = y_offset + 32
        x_offset = 0

        if i % 2 != 0:
            draw.rectangle(
                [
                    (0, y_offset),
                    (sum(header_widths), y_offset + row_height),
                ],
                fill=light_blue,
                width=2,
            )

        if len(str(row["Rank"])) == 1:
            draw.text(
                (x_offset + 72, text_y_offset),
                str(row["Rank"]),
                fill="black",
                font=font,
            )
        else:
            draw.text(
                (x_offset + 58, text_y_offset),
                str(row["Rank"]),
                fill="black",
                font=font,
            )
        x_offset += header_widths[0]

        avatar_image = Image.open(avatar_images[i])
        avatar_image = avatar_image.resize((avatar_size, avatar_size))
        rank_info_image.paste(avatar_image, (x_offset + 12, y_offset + 12))
        draw.text((x_offset + 124, text_y_offset), row["Name"], fill="black", font=font)
        x_offset += header_widths[1]

        draw.text(
            (x_offset + 140 - len(row["Level"]) * 12, text_y_offset), row["Level"], fill="black", font=font
        )
        x_offset += header_widths[2]

        draw.text((x_offset + 84, text_y_offset), row["Job"], fill="black", font=font)
        x_offset += header_widths[3]

        if row["Change"] is not None:
            change = int(row["Change"])
        else:
            change = None

        if change is None:
            draw.text(
                (x_offset + 74, text_y_offset),
                "New",
                fill="green",
                font=font,
            )

        elif change == 0:
            draw.text((x_offset + 110, text_y_offset), "-", fill="black", font=font)

        elif change > 0:
            if change >= 10:
                draw.text(
                    (x_offset + 66, text_y_offset),
                    "+" + str(change),
                    fill="red",
                    font=font,
                )

            else:
                draw.text(
                    (x_offset + 82, text_y_offset),
                    "+" + str(change),
                    fill="red",
                    font=font,
                )

        elif change < 0:
            if change <= -10:
                draw.text(
                    (x_offset + 76, text_y_offset),
                    str(change),
                    fill="blue",
                    font=font,
                )

            else:
                draw.text(
                    (x_offset + 88, text_y_offset),
                    str(change),
                    fill="blue",
                    font=font,
                )

        draw.line(
            [(header_widths[0], y_offset), (header_widths[0], y_offset + row_height)],
            fill=gray,
            width=1,
        )
        draw.line(
            [
                (header_widths[0] + header_widths[1], y_offset),
                (header_widths[0] + header_widths[1], y_offset + row_height),
            ],
            fill=gray,
            width=1,
        )
        draw.line(
            [
                (header_widths[0] + header_widths[1] + header_widths[2], y_offset),
                (
                    header_widths[0] + header_widths[1] + header_widths[2],
                    y_offset + row_height,
                ),
            ],
            fill=gray,
            width=1,
        )
        draw.line(
            [
                (
                    header_widths[0] + header_widths[1] + header_widths[2] + header_widths[3],
                    y_offset,
                ),
                (
                    header_widths[0] + header_widths[1] + header_widths[2] + header_widths[3],
                    y_offset + row_height,
                ),
            ],
            fill=gray,
            width=1,
        )

        draw.line(
            [
                (0, y_offset),
                (width, y_offset),
            ],
            fill=gray,
            width=1,
        )

    draw.line(
        [
            (0, 4),
            (width, 4),
        ],
        fill=blue,
        width=8,
    )
    draw.line(
        [
            (0, height - 4),
            (width, height - 4),
        ],
        fill=blue,
        width=8,
    )
    draw.line(
        [
            (4, 0),
            (4, height),
        ],
        fill=blue,
        width=8,
    )
    draw.line(
        [
            (width - 4, 0),
            (width - 4, height),
        ],
        fill=blue,
        width=8,
    )

    # 이미지 저장
    os_name = platform.system()
    if os_name == "Linux":
        image_path = misc.convert_path("\\tmp\\image.png")
    else:
        image_path = "image.png"

    rank_info_image.save(image_path)

    text_day = "지금" if today == misc.get_today() else today.strftime("%Y년 %m월 %d일")
    text_page = "을" if page == 1 else f" {page}페이지를"

    msg = f"{text_day} 한월 RPG의 캐릭터 랭킹{text_page} 보여드릴게요."

    return msg, image_path


def get_rank_history(name, period, today):
    current_data = get_current_rank_data() if today == misc.get_today() else None

    _id = misc.get_id(name=name)

    start_date = today - datetime.timedelta(days=period - 1)
    today = today.strftime("%Y-%m-%d")
    start_date = start_date.strftime("%Y-%m-%d")

    data = data_manager.read_data(
        "Ranks", index="id-date-index", condition_dict={"id": _id, "date": [start_date, today]}
    )

    for i, j in enumerate(data):
        data[i]["rank"] = 101 - int(j["rank"])

        del data[i]["level"]
        del data[i]["job"]
        del data[i]["id"]

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

    # 이미지 생성
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    plt.figure(figsize=(10, 4))
    smooth_coeff = 10

    label = f"{name}의 랭킹 히스토리"

    if period == 1:
        plt.plot("date", "rank", data=df, color="C0", marker="o", label=label)

    else:
        x = np.arange(len(df["date"]))
        y = df["rank"].values

        x_new = np.linspace(x.min(), x.max(), len(df["date"]) * smooth_coeff - smooth_coeff + 1)

        y_smooth = misc.pchip_interpolate(x, y, x_new)

        plt.plot(df["date"], df["rank"], color="C0", marker="o", label=label, linestyle="")
        plt.plot(
            df["date"][0] + pd.to_timedelta(x_new, unit="D"),
            y_smooth,
            color="C0",
        )

    plt.ylim(df["rank"].min() - 5, df["rank"].max() + 5)

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
                f'{101 - df["rank"].iloc[i]}위',
                (df["date"].iloc[i], df["rank"].iloc[i]),
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
            f'{101 - df["rank"].iloc[0]}위',
            (df["date"].iloc[0], df["rank"].iloc[0]),
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

    msg = f""

    return msg, image_path


if __name__ == "__main__":
    # today = datetime.datetime.strptime("2025-02-12", "%Y-%m-%d").date()
    today = misc.get_today()

    # print(get_rank_info(1, 7, today))
    print(get_rank_history("krosh0127", 20, today))
    # print(get_current_rank_data())
    # print(get_prev_player_rank(50, "2025-01-01"))
    # print(get_rank_data(datetime.date(2025, 2, 1)))
    pass
