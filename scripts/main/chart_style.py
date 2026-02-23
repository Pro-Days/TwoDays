from __future__ import annotations

import platform

import matplotlib
from path_utils import convert_path


def setup_agg_backend() -> None:
    # Lambda/서버 환경에서 화면 장치 없이 저장 가능하도록 고정
    matplotlib.use("Agg")


def apply_default_chart_style(plt, fm) -> str:
    # 차트 모듈마다 중복되던 스타일/폰트 초기화를 한 곳으로 모음
    plt.style.use("seaborn-v0_8-pastel")

    # 폰트 경로 설정 (Linux와 Windows에서 다르게 처리)
    # TODO: 폰트 파일을 프로젝트 내에 포함시키거나, 환경 변수에 경로를 설정하는 방식 고려
    if platform.system() == "Linux":
        font_path: str = "/opt/NanumSquareRoundEB.ttf"

    else:
        font_path = convert_path("assets\\fonts\\NanumSquareRoundEB.ttf")

    fm.fontManager.addfont(font_path)
    # 폰트 등록 후 rcParams를 갱신해야 한글이 모든 차트에서 일관되게 표시됨
    prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = prop.get_name()

    return font_path
