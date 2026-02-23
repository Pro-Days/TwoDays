from __future__ import annotations

import datetime
import os
import platform
import threading
from decimal import Decimal
from typing import TYPE_CHECKING

import data_manager
import get_character_info as gci
import matplotlib
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import misc
import pandas as pd
import register_player
import requests
from log_utils import get_logger
from models import CharacterData, RankRow
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)

# 그래프 스타일과 폰트 설정
plt.style.use("seaborn-v0_8-pastel")
if platform.system() == "Linux":
    font_path = "/opt/NanumSquareRoundEB.ttf"
else:
    font_path = misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf")
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = prop.get_name()

matplotlib.use("Agg")


def download_image(url: str, num: int, list_name: list[str]) -> None:
    """
    플레이어 머리 이미지 다운로드
    """

    logger.debug("download_image start: " f"idx={num} " f"url={url}")

    response: requests.Response = requests.get(url)

    os_name: str = platform.system()
    if os_name == "Linux":
        head_path = misc.convert_path(f"\\tmp\\player_heads\\player{num}.png")

    else:
        head_path = misc.convert_path(f"assets\\player_heads\\player{num}.png")

    with open(head_path, "wb") as file:
        file.write(response.content)

    list_name[num] = head_path

    logger.debug(
        "download_image complete: "
        f"idx={num} "
        f"path={head_path} "
        f"status={response.status_code}"
    )


def _get_official_level_rows(
    target_date: datetime.date, limit: int = 100
) -> list[dict]:

    logger.debug(
        "_get_official_level_rows start: " f"date={target_date} " f"limit={limit}"
    )

    rows: list[dict] = []
    last_evaluated_key = None

    while len(rows) < limit:
        page_size = min(100, limit - len(rows))
        page, last_evaluated_key = data_manager.manager.get_official_level_top(
            snapshot_date=target_date,
            limit=page_size,
            exclusive_start_key=last_evaluated_key,
        )
        if not page:
            break

        rows.extend(page)

        logger.debug(
            "_get_official_level_rows page fetched: "
            f"page_items={len(page)} "
            f"total={len(rows)} "
            f"has_next={bool(last_evaluated_key)}"
        )

        if not last_evaluated_key:
            break

    logger.debug("_get_official_level_rows complete: " f"returned={len(rows[:limit])}")

    return rows[:limit]


def _get_internal_power_rows(
    target_date: datetime.date, limit: int = 100
) -> list[dict]:

    logger.debug(
        "_get_internal_power_rows start: " f"date={target_date} " f"limit={limit}"
    )

    rows: list[dict] = []
    last_evaluated_key = None

    while len(rows) < limit:
        page_size = min(100, limit - len(rows))
        page, last_evaluated_key = data_manager.manager.get_internal_power_page(
            snapshot_date=target_date,
            page_size=page_size,
            exclusive_start_key=last_evaluated_key,
        )
        if not page:
            break

        rows.extend(page)

        logger.debug(
            "_get_internal_power_rows page fetched: "
            f"page_items={len(page)} "
            f"total={len(rows)} "
            f"has_next={bool(last_evaluated_key)}"
        )

        if not last_evaluated_key:
            break

    logger.debug("_get_internal_power_rows complete: " f"returned={len(rows[:limit])}")

    return rows[:limit]


def get_rank_data(
    target_date: datetime.date,
    start: int = 1,
    end: int = 100,
    metric: str = "level",
) -> list[CharacterData]:
    """
    특정 날짜의 랭킹 데이터를 가져오는 함수
    """

    logger.info(
        "get_rank_data start: "
        f"date={target_date} "
        f"start={start} "
        f"end={end} "
        f"metric={metric}"
    )

    if metric == "level":
        rows: list[dict] = _get_official_level_rows(target_date, limit=end)
    elif metric == "power":
        rows = _get_internal_power_rows(target_date, limit=end)
    else:
        raise ValueError(f"unsupported rank metric: {metric}")

    if not rows:
        logger.warning(
            "get_rank_data no rows: " f"date={target_date} " f"metric={metric}"
        )
        return []

    rank_data: list[CharacterData] = []

    for item in rows:
        pk = item.get("PK")
        if not isinstance(pk, str):
            continue

        rank_data.append(
            CharacterData(
                uuid=data_manager.manager.uuid_from_user_pk(pk),
                level=item["Level"],
                date=target_date,
                power=item["Power"],
            )
        )

    result = rank_data[start - 1 : end]

    logger.info(
        "get_rank_data complete: "
        f"date={target_date} "
        f"returned={len(result)} "
        f"metric={metric}"
    )

    return result


def get_current_rank_data(
    start: int = 1,
    end: int = 100,
    metric: str = "level",
    target_date: datetime.date | None = None,
) -> list[CharacterData]:
    """
    현재 랭킹 데이터를 가져오는 함수
    등록되지 않은 플레이어는 등록시킴
    """

    logger.info(
        "get_current_rank_data start: "
        f"start={start} "
        f"end={end} "
        f"metric={metric} "
        f"target_date={target_date}"
    )

    players: list[dict] = register_player.get_registered_players()

    rank_data: list[CharacterData] = [
        gci.get_current_character_data(player["uuid"], target_date=target_date)
        for player in players
    ]

    if metric == "level":
        rank_data.sort(key=lambda x: x.level, reverse=True)
    elif metric == "power":
        rank_data.sort(key=lambda x: x.power, reverse=True)
    else:
        raise ValueError(f"unsupported rank metric: {metric}")

    result = rank_data[start - 1 : end]
    logger.info(
        "get_current_rank_data complete: "
        f"players={len(players)} "
        f"returned={len(result)} "
        f"metric={metric} "
        f"target_date={target_date}"
    )
    return result


def _to_current_rank_rows(
    start: int = 1,
    end: int = 100,
    metric: str = "level",
    target_date: datetime.date | None = None,
) -> list[RankRow]:
    """
    업데이트 파이프라인용 현재 랭킹 원시 행 반환

    현재 구현은 기존 UUID 기반 current rank 계산을 어댑터로 감싼다.
    향후 실제 크롤링으로 내부만 교체
    """

    rank_data: list[CharacterData] = get_current_rank_data(
        start=start, end=end, metric=metric, target_date=target_date
    )
    rows: list[RankRow] = []

    for idx, row in enumerate(rank_data, start=start):
        name: str = misc.get_name_from_uuid(row.uuid) or row.uuid
        rows.append(
            RankRow(
                name=name,
                rank=Decimal(idx),
                level=row.level if metric == "level" else None,
                power=row.power if metric == "power" else None,
                metric=metric,
            )
        )

    logger.info(
        "_to_current_rank_rows complete: "
        f"start={start} "
        f"end={end} "
        f"metric={metric} "
        f"target_date={target_date} "
        f"returned={len(rows)}"
    )

    return rows


def get_current_level_rank_rows(
    start: int = 1, end: int = 100, target_date: datetime.date | None = None
) -> list[RankRow]:
    """현재 레벨 랭킹 raw rows 반환 (업데이트 파이프라인용)"""

    return _to_current_rank_rows(
        start=start, end=end, metric="level", target_date=target_date
    )


def get_current_power_rank_rows(
    start: int = 1, end: int = 100, target_date: datetime.date | None = None
) -> list[RankRow]:
    """현재 전투력 랭킹 raw rows 반환 (업데이트 파이프라인용)"""

    return _to_current_rank_rows(
        start=start, end=end, metric="power", target_date=target_date
    )


def get_rank_info(start: int, end: int, target_date: datetime.date, metric: str):

    logger.info(
        "get_rank_info start: "
        f"start={start} "
        f"end={end} "
        f"date={target_date} "
        f"metric={metric}"
    )

    if target_date == misc.get_today():
        current_data: list[CharacterData] = get_current_rank_data(
            start, end, metric=metric
        )

    else:
        current_data = get_rank_data(target_date, start, end, metric=metric)

    if not current_data:

        logger.warning(
            "get_rank_info no data: "
            f"start={start} "
            f"end={end} "
            f"date={target_date} "
            f"metric={metric}"
        )

        return None, None

    rank_count: int = min(end - start + 1, len(current_data))
    rank_metric_text: str = "전투력" if metric == "power" else "레벨"
    rank_field: str = "Power_Rank" if metric == "power" else "Level_Rank"

    data: dict[str, list] = {
        "Rank": list(range(start, start + rank_count)),
        "Name": [],
        "Value": [],
        "Change": [],
    }

    prev_date: datetime.date = target_date - datetime.timedelta(days=1)

    # 실시간 랭킹 데이터를 가져와서 data에 추가
    for i in range(rank_count):
        uuid: str = current_data[i].uuid
        name: str | None = misc.get_name_from_uuid(uuid=uuid)

        if name is None:
            name = "알 수 없음"

        data["Name"].append(name)
        current_value: Decimal = (
            current_data[i].power if metric == "power" else current_data[i].level
        )
        data["Value"].append(current_value)

        prev_snapshot: dict | None = data_manager.manager.get_user_snapshot(
            uuid=uuid, snapshot_date=prev_date
        )

        if not prev_snapshot or rank_field not in prev_snapshot:
            data["Change"].append(None)

        else:
            diff: int = int(prev_snapshot[rank_field]) - (i + start)
            data["Change"].append(diff)

    # 랭킹에 해당하는 플레이어의 머리 이미지 다운로드
    avatar_images: list[str] = [""] * rank_count

    os_name: str = platform.system()
    if os_name == "Linux":
        head_path: str = misc.convert_path(f"\\tmp\\player_heads\\player.png")
    else:
        head_path = misc.convert_path(f"assets\\player_heads\\player.png")

    if not os.path.exists(os.path.dirname(head_path)):
        os.makedirs(os.path.dirname(head_path))

    # rank_count개의 스레드 생성
    threads: list[threading.Thread] = []
    for i in range(rank_count):
        url: str = f"https://mineskin.eu/helm/{data['Name'][i]}/100.png"
        thread = threading.Thread(
            target=download_image,
            args=(url, i, avatar_images),
        )
        threads.append(thread)
        thread.start()

    # 모든 스레드가 완료될 때까지 대기
    for thread in threads:
        thread.join()

    header_text = ["순위", "닉네임", rank_metric_text, "변동"]
    header_widths = [160, 560, 360, 240] if metric == "power" else [160, 580, 280, 240]

    header_height = 100
    row_height = 100
    avatar_size = 80
    width, height = sum(header_widths), row_height * rank_count + header_height + 8

    gray = (200, 200, 200)
    blue = (160, 200, 255)
    aqua = (190, 230, 255)
    light_blue = (240, 245, 255)

    rank_info_image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(rank_info_image)

    draw.rectangle(
        [(0, 0), (width, header_height)],
        fill=aqua,
        width=2,
    )

    if os_name == "Linux":
        font = ImageFont.truetype("/opt/NanumSquareRoundEB.ttf", 40)
    else:
        font = ImageFont.truetype(
            misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf"), 40
        )

    x_offset: int = -10
    x_list: list[int] = [34, 110, 90, 68]
    for i, text in enumerate(header_text):
        draw.text((x_offset + x_list[i] + 24, 30), text, fill="black", font=font)
        x_offset += header_widths[i]

    for i in range(rank_count):
        raw_value = data["Value"][i]
        value_text = (
            f"{int(raw_value):,}"
            if metric == "power"
            else f"Lv.{int(raw_value)} {raw_value % 1 * 100:.2f}%"
        )
        row = {
            "Rank": str(data["Rank"][i]),
            "Name": data["Name"][i],
            "Value": value_text,
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

        # 랭킹 글자수에 따라 위치 조정
        x = x_offset + 86 - len(str(row["Rank"])) * 14
        draw.text(
            (x, text_y_offset),
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
            (x_offset + 140 - len(row["Value"]) * 12, text_y_offset),
            row["Value"],
            fill="black",
            font=font,
        )
        x_offset += header_widths[2]

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
        image_path = "/tmp/image.png"
    else:
        image_path = "image.png"

    rank_info_image.save(image_path)

    text_day = (
        "지금"
        if target_date == misc.get_today()
        else target_date.strftime("%Y년 %m월 %d일")
    )

    msg = f"{text_day} {start}~{end}위 캐릭터 {rank_metric_text} 랭킹을 보여드릴게요."

    logger.info(
        "get_rank_info complete: "
        f"start={start} "
        f"end={end} "
        f"date={target_date} "
        f"metric={metric} "
        f"image={image_path}"
    )

    return msg, image_path


def get_rank_history(
    start: int,
    end: int,
    period: int,
    target_date: datetime.date,
    metric: str,
) -> tuple:

    logger.info(
        "get_rank_history start: "
        f"start={start} "
        f"end={end} "
        f"period={period} "
        f"date={target_date} "
        f"metric={metric}"
    )

    today: datetime.date = misc.get_today()
    current_data: list[CharacterData] = (
        get_current_rank_data(metric=metric) if target_date == today else []
    )

    rank_count: int = end - start + 1

    start_date: datetime.date = target_date - datetime.timedelta(days=period - 1)
    data: list[dict] = []

    for offset in range(period):
        day = start_date + datetime.timedelta(days=offset)
        day_str = day.strftime("%Y-%m-%d")

        if day == target_date and target_date == today:
            day_data = current_data[start - 1 : end]
        else:
            day_data = get_rank_data(day, start, end, metric=metric)

        for i, row in enumerate(day_data):
            data.append(
                {
                    "date": day_str,
                    "rank": i + start,
                    "uuid": row.uuid,
                }
            )

    if not data:
        logger.warning(
            "get_rank_history no data: "
            f"start={start} "
            f"end={end} "
            f"period={period} "
            f"date={target_date} "
            f"metric={metric}"
        )
        return None, None

    # 실제 데이터로 기간 계산
    period = len(set([i["date"] for i in data]))

    data = sorted(data, key=lambda x: x["date"])

    # 이미지 생성
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    # plt.figure(figsize=(10 * math.log10(period), 6))
    plt.figure(
        figsize=(period * 0.5 if period >= 15 else period * 0.3 + 3, 0.6 * rank_count)
    )

    # 색상 리스트
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

    # 중복 없는 uuid 리스트 생성
    player_uuids = df["uuid"].unique()

    # 가장 최근 날짜의 데이터 찾기
    latest_date = df["date"].max()

    # 각 플레이어 조합의 최근 순위 찾기 (높은 순위를 나중에 그려 위에 표시되도록)
    player_latest_ranks = {}
    for player_uuid in player_uuids:
        player_data = df[df["uuid"] == player_uuid]
        # 해당 ID와 슬롯의 가장 최근 날짜 데이터 찾기
        player_latest = player_data[player_data["date"] == player_data["date"].max()]
        if not player_latest.empty:
            player_latest_ranks[player_uuid] = player_latest["rank"].iloc[0]
        else:
            player_latest_ranks[player_uuid] = (
                999  # 데이터가 없는 경우 낮은 우선순위    # 최근 순위 기준으로 오름차순 정렬 (낮은 순위 먼저, 높은 순위 나중에 그려서 위에 표시)
            )
    sorted_player_uuids = sorted(
        player_uuids, key=lambda psid: player_latest_ranks[psid], reverse=True
    )

    # 텍스트 라벨의 위치를 추적하기 위한 딕셔너리
    # key: (date, rank) 좌표, value: 해당 좌표에 이미 텍스트가 있는지 여부
    text_positions = {}
    # 최근 순위가 높은 플레이어가 가장 나중에 그려져 위에 표시됨
    for i, player_uuid in enumerate(sorted_player_uuids):
        group = df[df["uuid"] == player_uuid]
        color_idx: int = i % len(colors)

        player_name = misc.get_name_from_uuid(uuid=player_uuid)

        if player_name is None:
            continue

        player_label = player_name

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
        for group_data in date_groups:
            if len(group_data) > 0:
                group_df = pd.DataFrame(
                    group_data
                )  # 단일 데이터 포인트인지 확인 (선이 아니라 점)
                is_single_point = len(group_df) == 1
                zorder = 100 - player_latest_ranks[player_uuid]

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
                position_key = (
                    mdates.date2num(last_date),
                    last_rank,
                )  # 가장 최근 날짜 데이터의 경우 우측에 표시 (겹침 없음, 항상 오른쪽에)
                if last_date == latest_date:
                    plt.text(
                        last_date
                        + pd.Timedelta(days=0.5),  # 마지막 날짜보다 조금 오른쪽
                        last_rank,
                        player_label,
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
                            player_label,
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
                            player_label,
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
    ticks = [float(mdates.date2num(df["date"].unique()[i])) for i in tick_indices]
    ax.xaxis.set_major_locator(ticker.FixedLocator(ticks))

    # x축 범위를 데이터 범위로 제한 (여백 추가)
    plt.xlim(
        df["date"].iloc[0] - pd.Timedelta(days=1),
        df["date"].iloc[-1]
        + pd.Timedelta(days=0.5),  # 우측 여백 늘림 (닉네임 표시 공간)
    )
    plt.ylim(end + 1, start - 1)

    # 범례 제거 (닉네임을 직접 선 위에 표시하므로 범례가 필요 없음)

    plt.yticks(range(start, end + 1))

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
    plt.savefig(image_path, dpi=200, bbox_inches="tight")
    plt.close()

    rank_metric_text: str = "전투력" if metric == "power" else "레벨"
    msg = (
        f"{period}일 동안의 {start}~{end}위 {rank_metric_text} 랭킹 히스토리를 "
        "보여드릴게요."
    )

    logger.info(
        "get_rank_history complete: "
        f"start={start} "
        f"end={end} "
        f"period={period} "
        f"target_date={target_date} "
        f"metric={metric} "
        f"image={image_path} "
        f"rows={len(data)}"
    )

    return msg, image_path


if __name__ == "__main__":
    # today = datetime.datetime.strptime("2025-05-16", "%Y-%m-%d").date()
    today = misc.get_today()

    # print(get_rank_history([1, 30], 10, today))
    # print(get_rank_info(1, 30, today))
    # print(get_current_rank_data())
    # print(get_prev_player_rank(50, "2025-01-01"))
    # print(get_rank_data(datetime.date(2025, 2, 1)))
    pass
