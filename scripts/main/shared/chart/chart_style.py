from __future__ import annotations

import matplotlib

from scripts.main.shared.utils.path_utils import get_font_path


def setup_agg_backend() -> None:
    # Lambda/서버 환경에서 화면 장치 없이 저장 가능하도록 고정
    matplotlib.use("Agg")


def apply_default_chart_style(plt, fm) -> str:
    # 차트 모듈마다 중복되던 스타일/폰트 초기화를 한 곳으로 모음
    plt.style.use("seaborn-v0_8-pastel")

    font_path: str = get_font_path()

    fm.fontManager.addfont(font_path)
    # 폰트 등록 후 rcParams를 갱신해야 한글이 모든 차트에서 일관되게 표시됨
    prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = prop.get_name()

    return font_path
