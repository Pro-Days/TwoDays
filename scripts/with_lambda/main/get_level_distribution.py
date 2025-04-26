import datetime
import platform

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm

import misc
import data_manager

plt.style.use("seaborn-v0_8-pastel")
if platform.system() == "Linux":
    font_path = "/opt/NanumSquareRoundEB.ttf"
else:
    font_path = misc.convert_path("assets\\fonts\\NanumSquareRoundEB.ttf")
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = prop.get_name()

matplotlib.use("Agg")


def get_level_distribution(today):
    today_text = today.strftime("%Y-%m-%d")

    datas = [
        data_manager.scan_data("DailyData", filter_dict={"date-slot": f"{today_text}#{i}"}) for i in range(5)
    ]

    data = []
    for i in range(5):
        data.extend(datas[i])

    for i in range(len(data)):
        data[i] = float(data[i]["level"])

    data.sort()

    # 히스토그램 그리기
    plt.figure(figsize=(10, 6))
    bins = 120  # Fixed number of bins
    n, bins, patches = plt.hist(data, bins=bins, range=(0, 300), alpha=1.0, color="skyblue")

    # Add labels and title
    plt.xlabel("레벨", fontsize=12)

    ylabel_text = "\n".join("플레이어수")
    plt.ylabel(ylabel_text, fontsize=12, rotation=0, labelpad=10)
    ax = plt.gca()
    ax.yaxis.set_label_coords(-0.035, 0.43)  # ylabel 위치

    # ytick을 정수로만 표시
    plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.xlim(0, 300)

    plt.grid(axis="y", alpha=0.3)

    os_name = platform.system()
    if os_name == "Linux":
        image_path = "/tmp/level_distribution.png"
    else:
        image_path = misc.convert_path("image.png")

    plt.tight_layout()
    plt.savefig(image_path, dpi=300, bbox_inches="tight")
    plt.close()

    msg = f"{today.strftime('%Y년 %m월 %d일')} 기준 등록된 플레이어의 레벨 분포를 보여드릴게요.\n이 이미지는 서버의 모든 플레이어의 정보를 포함하지 않아요."
    return msg, image_path


if __name__ == "__main__":
    # today = datetime.datetime.strptime("2025-02-15", "%Y-%m-%d").date()
    today = misc.get_today() - datetime.timedelta(days=1)

    print(get_level_distribution(today))
    # print(get_rank_info(1, today))
    # print(get_current_rank_data())
    # print(get_prev_player_rank(50, "2025-01-01"))
    # print(get_rank_data(datetime.date(2025, 2, 1)))
    pass
