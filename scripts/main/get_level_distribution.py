from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import data_manager
from chart_io import save_and_close_chart
from chart_style import apply_default_chart_style, setup_agg_backend
from time_utils import get_today

setup_agg_backend()

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)

# 그래프 스타일과 폰트 설정
apply_default_chart_style(plt, fm)


def get_level_distribution(target_date: datetime.date) -> tuple[str, str]:
    """주어진 날짜에 등록된 플레이어들의 레벨 분포를 히스토그램으로 그려서 이미지로 저장하고, 메시지와 이미지 경로를 반환"""

    logger.info("get_level_distribution start: " f"target_date={target_date}")

    data: list[float] = []
    last_evaluated_key = None
    while True:
        temp_data, last_evaluated_key = data_manager.manager.get_internal_level_page(
            snapshot_date=target_date,
            page_size=200,
            exclusive_start_key=last_evaluated_key,
        )
        if not temp_data:
            break

        data.extend([float(item["Level"]) for item in temp_data if "Level" in item])

        logger.debug(
            "get_level_distribution page fetched: "
            f"page_items={len(temp_data)} "
            f"total_levels={len(data)} "
            f"has_next={bool(last_evaluated_key)}"
        )

        if not last_evaluated_key:
            break

    # 히스토그램 그리기
    plt.figure(figsize=(10, 6))
    bins = 100
    n, bins, patches = plt.hist(
        data, bins=bins, range=(1, 200), alpha=1.0, color="skyblue"
    )

    # Add labels and title
    plt.xlabel("레벨", fontsize=12)

    ylabel_text = "\n".join("플레이어수")
    plt.ylabel(ylabel_text, fontsize=12, rotation=0, labelpad=10)
    ax = plt.gca()
    ax.yaxis.set_label_coords(-0.05, 0.43)  # ylabel 위치

    # ytick을 정수로만 표시
    plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.xlim(1, 200)

    plt.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    image_path: str = save_and_close_chart(
        plt, dpi=250, filename="level_distribution.png"
    )

    msg: str = (
        f"{target_date.strftime('%Y년 %m월 %d일')} 기준 등록된 플레이어의 레벨 분포를 보여드릴게요.\n"
        f"투데이즈에는 총 {len(data)}명의 캐릭터가 등록되어있어요.\n"
        "이 이미지는 서버의 모든 플레이어의 정보를 포함하지 않아요."
    )

    logger.info(
        "get_level_distribution complete: "
        f"target_date={target_date} "
        f"count={len(data)} "
        f"image_path={image_path}"
    )

    return msg, image_path


if __name__ == "__main__":
    # today = datetime.datetime.strptime("2025-02-15", "%Y-%m-%d").date()
    today: datetime.date = get_today() - datetime.timedelta(days=1)

    print(get_level_distribution(today))
    pass
