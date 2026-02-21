import datetime
import platform

import data_manager
import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import misc

plt.style.use("seaborn-v0_8-pastel")
if platform.system() == "Linux":
    font_path = "/opt/NanumSquareRoundEB.ttf"
else:
    font_path = misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf")
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = prop.get_name()

matplotlib.use("Agg")


def get_level_distribution(target_date: datetime.date) -> tuple[str, str]:
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

    os_name = platform.system()
    if os_name == "Linux":
        image_path = "/tmp/level_distribution.png"
    else:
        image_path = misc.convert_path("image.png")

    plt.tight_layout()
    plt.savefig(image_path, dpi=250, bbox_inches="tight")
    plt.close()

    msg = f"{target_date.strftime('%Y년 %m월 %d일')} 기준 등록된 플레이어의 레벨 분포를 보여드릴게요.\n부캐릭터를 포함해서 총 {len(data)}개의 캐릭터가 등록되어있어요.\n이 이미지는 서버의 모든 플레이어의 정보를 포함하지 않아요."
    return msg, image_path


if __name__ == "__main__":
    # today = datetime.datetime.strptime("2025-02-15", "%Y-%m-%d").date()
    today = misc.get_today() - datetime.timedelta(days=1)

    print(get_level_distribution(today))
    pass
