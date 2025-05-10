import os
import math
import random
import datetime
import platform
import requests
import threading
import pandas as pd
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects  # Added import for path effects

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
    data = data_manager.read_data(
        "Ranks", condition_dict={"date": day.strftime("%Y-%m-%d")}
    )

    for i, j in enumerate(data):
        data[i]["rank"] = int(j["rank"])
        data[i]["id"] = int(j["id"])
        data[i]["job"] = int(j["job"])
        data[i]["level"] = j["level"]
        data[i]["name"] = misc.get_name(id=j["id"])

    return data if page == 0 else data[page * 10 - 10 : page * 10]


def get_current_rank_data(page=0) -> dict:
    """
    현재 전체 캐릭터 랭킹 데이터 반환
    {"name": "ProDays", "job": "검호", "level": "100"}
    """

    today = misc.get_today() - datetime.timedelta(days=1)
    today_str = today.strftime("%Y-%m-%d")
    base_date = datetime.date(2025, 1, 1)

    delta_days = (today - base_date).days

    players = register_player.get_registered_players()
    data = []

    for player in players:

        playerdata = data_manager.read_data(
            "DailyData",
            None,
            {"id": player["id"], "date-slot": [f"{today_str}#0", f"{today_str}#4"]},
        )
        if playerdata is None:
            continue
        data.append(playerdata[0])

    rankdata = []

    for d in data:
        name = misc.get_name(id=d["id"])
        random.seed(sum(ord(c) for c in name.lower()) + 1)
        coef = random.uniform(0.3, 0.7)

        level = Decimal(d["level"])

        for _ in range(delta_days):
            random.uniform(-0.3, 0.3)

        level += Decimal(
            round(
                20
                / (level ** Decimal(0.5))
                * Decimal(coef + random.uniform(-0.3, 0.3)),
                4,
            )
        )

        rankdata.append(
            {
                "name": name,
                "job": misc.convert_job(d["job"]),
                "level": level,
            }
        )

    rankdata = sorted(rankdata, key=lambda x: x["level"], reverse=True)

    return rankdata[page * 10 - 10 : page * 10] if page != 0 else rankdata


def get_rank_info(page, today):
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

        prev_rank = data_manager.read_data(
            "Ranks", "id-date-index", {"id": user_id, "date": prev_date_str}
        )[0]["rank"]

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
        font = ImageFont.truetype(
            misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf"), 40
        )

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
            "Level": f"{data['Level'][i]:.1f}",
            "Job": (
                data["Job"][i]
                if isinstance(data["Job"][i], str)
                else misc.convert_job(data["Job"][i])
            ),
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
            (x_offset + 140 - len(row["Level"]) * 12, text_y_offset),
            row["Level"],
            fill="black",
            font=font,
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
                    header_widths[0]
                    + header_widths[1]
                    + header_widths[2]
                    + header_widths[3],
                    y_offset,
                ),
                (
                    header_widths[0]
                    + header_widths[1]
                    + header_widths[2]
                    + header_widths[3],
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

    msg = f"{text_day} 캐릭터 랭킹{text_page} 보여드릴게요."

    return msg, image_path


def get_rank_history(page, period, today):
    current_data = get_current_rank_data() if today == misc.get_today() else None

    start_date = today - datetime.timedelta(days=period - 1)
    today = today.strftime("%Y-%m-%d")
    start_date = start_date.strftime("%Y-%m-%d")

    data = data_manager.scan_data(
        "Ranks",
        filter_dict={"date": [start_date, today], "rank": [page * 10 - 9, page * 10]},
    )

    for i, j in enumerate(data):
        data[i]["rank"] = int(j["rank"])
        data[i]["id"] = int(j["id"])

        del data[i]["level"]
        del data[i]["job"]

    if current_data is not None:
        for i, j in enumerate(current_data):  # job level name
            if page * 10 - 10 <= i < page * 10:
                data.append(
                    {
                        "date": today,
                        "rank": i + 1,
                        "id": misc.get_id(name=j["name"]),
                    }
                )

    period = len(set([i["date"] for i in data]))

    data = sorted(data, key=lambda x: x["date"])

    # 이미지 생성
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    # plt.figure(figsize=(10 * math.log10(period), 6))
    plt.figure(figsize=(period * 0.5 if period >= 15 else period * 0.3 + 3, 6))

    # Define a custom color palette for better distinction between lines
    colors = [
        "#fb9a99",
        "#80b1d3",
        "#fdd462",
        "#f65a8c",
        "#a5de94",
        "#bc80bd",
        "#ff7f00",
        "#1f78b4",
        "#33a02c",
        "#ff2222",
        "#436e6f",
        "#c56477",
        "#ac7f0f",
    ]

    # Get unique player IDs
    player_ids = df["id"].unique()

    # 가장 최근 날짜의 데이터 찾기
    latest_date = df["date"].max()

    # 각 플레이어의 최근 순위 찾기 (높은 순위를 나중에 그려 위에 표시되도록)
    player_latest_ranks = {}
    for player_id in player_ids:
        player_data = df[df["id"] == player_id]
        # 해당 ID의 가장 최근 날짜 데이터 찾기
        player_latest = player_data[player_data["date"] == player_data["date"].max()]
        if not player_latest.empty:
            player_latest_ranks[player_id] = player_latest["rank"].iloc[0]
        else:
            player_latest_ranks[player_id] = 999  # 데이터가 없는 경우 낮은 우선순위

    # 최근 순위 기준으로 오름차순 정렬 (낮은 순위 먼저, 높은 순위 나중에 그려서 위에 표시)
    sorted_player_ids = sorted(
        player_ids, key=lambda pid: player_latest_ranks[pid], reverse=True
    )

    # 텍스트 라벨의 위치를 추적하기 위한 딕셔너리
    # key: (date, rank) 좌표, value: 해당 좌표에 이미 텍스트가 있는지 여부
    text_positions = {}

    # Plot each player's data with a specific color, 최근 순위가 높은 플레이어가 가장 나중에 그려져 위에 표시됨
    for i, player_id in enumerate(sorted_player_ids):
        group = df[df["id"] == player_id]
        color_idx = i % len(colors)  # Cycle through colors if more players than colors
        player_name = misc.get_name(id=int(player_id))  # 플레이어 이름 가져오기

        # 데이터 프레임에서 날짜를 정렬하여 날짜 간격을 확인
        sorted_group = group.sort_values(by="date")

        # 연속된 데이터 포인트를 찾아서 그룹화하기
        date_groups = []
        current_group = []

        # 날짜 순으로 처리
        for idx, row in sorted_group.iterrows():
            if not current_group:
                # 첫 데이터 포인트 추가
                current_group.append(row)
            else:
                # 연속된 데이터인지 확인
                last_date = current_group[-1]["date"]
                current_date = row["date"]
                date_diff = (current_date - last_date).days

                # 하루 간격이면 같은 그룹에 추가
                if date_diff == 1:
                    current_group.append(row)
                else:
                    # 간격이 1일보다 크면 새 그룹 시작
                    if len(current_group) > 0:
                        date_groups.append(current_group)
                    current_group = [row]

        # 마지막 그룹 추가
        if current_group:
            date_groups.append(current_group)

        # 각 연속된 날짜 그룹마다 별도의 선으로 그리기
        for group_idx, group_data in enumerate(date_groups):
            if len(group_data) > 0:
                group_df = pd.DataFrame(group_data)

                # 단일 데이터 포인트인지 확인 (선이 아니라 점)
                is_single_point = len(group_df) == 1
                zorder = 100 - player_latest_ranks[player_id]

                if not is_single_point:
                    # 선 그리기 (마커 없이)
                    (line,) = plt.plot(
                        group_df["date"],
                        group_df["rank"],
                        marker="",  # 선에는 마커 표시 안함
                        color=colors[color_idx],
                        linewidth=4,
                        zorder=zorder,  # 순위가 높을수록(숫자가 작을수록) zorder 값이 커짐
                    )

                    # 그림자 효과 추가 (선 아래에 그림자)
                    line.set_path_effects(
                        [
                            path_effects.SimpleLineShadow(),
                            path_effects.Normal(),
                        ]
                    )

                # 마지막 데이터 포인트에만 마커 표시
                plt.plot(
                    [group_df["date"].iloc[-1]],  # 마지막 데이터 포인트의 날짜
                    [group_df["rank"].iloc[-1]],  # 마지막 데이터 포인트의 순위
                    marker="o",
                    markersize=10,
                    color=colors[color_idx],
                    linestyle="",  # 선은 표시 안함
                    zorder=zorder + 1,  # 선보다 위에 표시
                )

                # 각 그룹(선 또는 단일 점)의 마지막 데이터 포인트 정보
                last_date = group_df["date"].iloc[-1]
                last_rank = group_df["rank"].iloc[-1]

                # 날짜와 순위를 이용해 위치 키를 생성
                position_key = (mdates.date2num(last_date), last_rank)

                # 가장 최근 날짜 데이터의 경우 우측에 표시 (겹침 없음, 항상 오른쪽에)
                if last_date == latest_date:
                    plt.text(
                        last_date
                        + pd.Timedelta(days=0.5),  # 마지막 날짜보다 조금 오른쪽
                        last_rank,
                        player_name,
                        color="black",
                        fontweight="bold",
                        fontsize=10,
                        va="center",
                        zorder=1000,  # 마커보다 위에 표시
                    )
                else:
                    # 최근 데이터가 아닌 모든 그룹(끊어진 선이나 단일 점)의 마지막 포인트 텍스트 위치 조정
                    # 근처에 다른 텍스트가 있는지 확인
                    nearby_occupied = False

                    # 순위 기준으로 근처 (±0.5 이내) 텍스트 위치 확인
                    for existing_date, existing_rank in text_positions.keys():
                        # 날짜가 가까운 포인트 중
                        date_diff = abs(mdates.date2num(last_date) - existing_date)
                        if date_diff < 2.0:  # 날짜가 가까운 경우 (2일 이내)
                            # 순위도 가까운 경우
                            if abs(last_rank - existing_rank) < 0.7:
                                nearby_occupied = True
                                break

                    if nearby_occupied:
                        # 다른 텍스트가 이미 있다면, 포인트 아래에 텍스트 표시
                        plt.text(
                            last_date,  # 마지막 데이터 위치
                            last_rank + 0.4,  # 데이터 포인트보다 약간 아래에
                            player_name,
                            color="black",
                            fontweight="bold",
                            fontsize=10,
                            ha="center",
                            zorder=1000,  # 마커보다 위에 표시
                        )
                    else:
                        # 주변에 다른 텍스트가 없다면, 포인트 위에 텍스트 표시 (기존 방식)
                        plt.text(
                            last_date,  # 마지막 데이터 위치
                            last_rank - 0.2,  # 데이터 포인트보다 약간 위에
                            player_name,
                            color="black",
                            fontweight="bold",
                            fontsize=10,
                            ha="center",
                            zorder=1000,  # 마커보다 위에 표시
                        )

                    # 이 위치에 텍스트를 배치했음을 기록
                    text_positions[position_key] = True

    ax = plt.gca()
    date_format = mdates.DateFormatter("%m월 %d일")
    ax.xaxis.set_major_formatter(date_format)

    # 표시할 x축 날짜 직접 계산
    tick_indices = range(len(df["date"].unique()) - 1, -1, -3)  # 역순으로

    # 실제 데이터 포인트의 날짜만 선택
    ticks = [mdates.date2num(df["date"].unique()[i]) for i in tick_indices]
    ax.xaxis.set_major_locator(ticker.FixedLocator(ticks))

    # x축 범위를 데이터 범위로 제한 (여백 추가)
    plt.xlim(
        df["date"].iloc[0] - pd.Timedelta(days=1),
        df["date"].iloc[-1]
        + pd.Timedelta(days=0.5),  # 우측 여백 늘림 (닉네임 표시 공간)
    )
    plt.ylim(page * 10 + 1, page * 10 - 10)

    # 범례 제거 (닉네임을 직접 선 위에 표시하므로 범례가 필요 없음)

    plt.yticks(range(page * 10 - 9, page * 10 + 1))

    # 회색 격자선 추가
    plt.grid(axis="both", linestyle="--", alpha=0.5)

    # 테두리 제거
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    # ax.spines["bottom"].set_visible(False)

    os_name = platform.system()
    if os_name == "Linux":
        image_path = "/tmp/image.png"
    else:
        image_path = "image.png"
    plt.savefig(image_path, dpi=300, bbox_inches="tight")
    plt.close()

    msg = f"{period}일 동안의 {'' if page == 1 else f'{page}페이지 '}랭킹 히스토리를 보여드릴게요."
    return msg, image_path


if __name__ == "__main__":
    # today = datetime.datetime.strptime("2025-02-15", "%Y-%m-%d").date()
    today = misc.get_today()

    print(get_rank_history(1, 50, today))
    # print(get_rank_info(1, today))
    # print(get_current_rank_data())
    # print(get_prev_player_rank(50, "2025-01-01"))
    # print(get_rank_data(datetime.date(2025, 2, 1)))
    pass
