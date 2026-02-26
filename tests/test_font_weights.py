"""Font weight tests for image charts."""

from __future__ import annotations

import datetime
import importlib
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd


def test_get_rank_info_uses_text_stroke(monkeypatch) -> None:
    font_path = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "fonts"
        / "PretendardVariable.ttf"
    )
    monkeypatch.setenv("FONT_PATH", str(font_path))

    gri = importlib.import_module("scripts.main.features.get_rank_info")
    importlib.reload(gri)

    text_calls: list[dict] = []

    class DummyDraw:
        def text(self, xy, text, fill=None, font=None, **kwargs):
            text_calls.append(kwargs)

        def rectangle(self, *args, **kwargs) -> None:
            return None

        def line(self, *args, **kwargs) -> None:
            return None

    class DummyImage:
        def paste(self, *args, **kwargs) -> None:
            return None

        def save(self, *args, **kwargs) -> None:
            return None

    def fake_download_image(url, num, list_name, output_dir) -> None:
        list_name[num] = None

    class DummyThread:
        def __init__(self, target, args) -> None:
            self._target = target
            self._args = args

        def start(self) -> None:
            self._target(*self._args)

        def join(self) -> None:
            return None

    dummy_draw = DummyDraw()

    monkeypatch.setattr(gri.ImageDraw, "Draw", lambda image: dummy_draw)
    monkeypatch.setattr(gri.Image, "new", lambda *args, **kwargs: DummyImage())
    monkeypatch.setattr(gri.ImageFont, "truetype", lambda *args, **kwargs: object())
    monkeypatch.setattr(gri, "download_image", fake_download_image)
    monkeypatch.setattr(gri.threading, "Thread", DummyThread)
    monkeypatch.setattr(gri, "get_chart_image_path", lambda *args, **kwargs: "dummy")

    target_date = datetime.date(2025, 1, 1)

    monkeypatch.setattr(gri, "get_today", lambda: target_date)
    monkeypatch.setattr(
        gri,
        "get_current_rank_data",
        lambda *args, **kwargs: [
            gri.MetricRankEntry(
                uuid="uuid",
                metric="level",
                value=Decimal("10"),
            )
        ],
    )
    monkeypatch.setattr(gri, "get_name_from_uuid", lambda uuid: "Player")
    monkeypatch.setattr(
        gri.data_manager.manager,
        "get_user_snapshot",
        lambda *args, **kwargs: None,
    )

    gri.get_rank_info(1, 1, target_date, metric="level")

    assert text_calls
    assert all(call.get("stroke_width") == 1 for call in text_calls)
    assert all(call.get("stroke_fill") == "black" for call in text_calls)


def test_get_rank_history_uses_fontweight(monkeypatch) -> None:
    font_path = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "fonts"
        / "PretendardVariable.ttf"
    )
    monkeypatch.setenv("FONT_PATH", str(font_path))

    gri = importlib.import_module("scripts.main.features.get_rank_info")
    importlib.reload(gri)

    text_calls: list[dict] = []

    def fake_text(*args, **kwargs):
        text_calls.append(kwargs)

    monkeypatch.setattr(gri.plt, "text", fake_text)
    monkeypatch.setattr(gri.plt, "savefig", lambda *args, **kwargs: None)
    monkeypatch.setattr(gri.plt, "close", lambda *args, **kwargs: None)
    monkeypatch.setattr(gri, "get_chart_image_path", lambda *args, **kwargs: "dummy")
    monkeypatch.setattr(
        gri,
        "get_rank_data",
        lambda *args, **kwargs: [
            gri.MetricRankEntry(
                uuid="uuid",
                metric="level",
                value=Decimal("10"),
            )
        ],
    )
    monkeypatch.setattr(gri, "get_name_from_uuid", lambda uuid: "Player")

    target_date = datetime.date(2025, 1, 2)

    monkeypatch.setattr(gri, "get_today", lambda: datetime.date(2025, 1, 3))

    gri.get_rank_history(1, 1, 1, target_date, metric="level")

    assert text_calls
    assert all(call.get("fontweight") == "black" for call in text_calls)


def test_metric_history_chart_uses_fontweight(monkeypatch) -> None:
    font_path = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "fonts"
        / "PretendardVariable.ttf"
    )
    monkeypatch.setenv("FONT_PATH", str(font_path))

    gci = importlib.import_module("scripts.main.features.get_character_info")
    importlib.reload(gci)

    annotate_calls: list[dict] = []

    def fake_annotate(*args, **kwargs) -> None:
        annotate_calls.append(kwargs)

    monkeypatch.setattr(gci.plt, "annotate", fake_annotate)
    monkeypatch.setattr(
        gci,
        "_plot_smoothed_series",
        lambda *args, **kwargs: (np.array([0.0, 1.0]), np.array([1.0, 2.0])),
    )
    monkeypatch.setattr(gci, "_apply_relative_ylim", lambda *args, **kwargs: None)
    monkeypatch.setattr(gci, "_fill_smoothed_area", lambda *args, **kwargs: None)
    monkeypatch.setattr(gci, "_configure_date_axis", lambda *args, **kwargs: [0])
    monkeypatch.setattr(gci, "_style_minimal_axes", lambda *args, **kwargs: None)
    monkeypatch.setattr(gci, "_save_and_close_chart", lambda *args, **kwargs: "dummy")

    df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2025-01-01")],
            "level": [10.5],
        }
    )

    gci._render_metric_history_chart(
        df=df,
        value_col="level",
        period=1,
        main_label="레벨",
        main_color="#123456",
        fill_color="#abcdef",
        fill_alpha=0.4,
        point_label_formatter=gci._format_level_point_label,
    )

    assert annotate_calls
    assert all(call.get("fontweight") == "semibold" for call in annotate_calls)


def test_rank_history_chart_uses_fontweight(monkeypatch) -> None:
    font_path = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "fonts"
        / "PretendardVariable.ttf"
    )
    monkeypatch.setenv("FONT_PATH", str(font_path))

    gci = importlib.import_module("scripts.main.features.get_character_info")
    importlib.reload(gci)

    annotate_calls: list[dict] = []

    def fake_annotate(*args, **kwargs) -> None:
        annotate_calls.append(kwargs)

    monkeypatch.setattr(gci.plt, "annotate", fake_annotate)
    monkeypatch.setattr(
        gci,
        "_compute_smooth_curve",
        lambda *args, **kwargs: (np.array([0.0, 1.0]), np.array([1.0, 2.0])),
    )
    monkeypatch.setattr(gci, "_fill_smoothed_area", lambda *args, **kwargs: None)
    monkeypatch.setattr(gci, "_configure_date_axis", lambda *args, **kwargs: [])
    monkeypatch.setattr(gci, "_build_tick_indices", lambda *args, **kwargs: [0])
    monkeypatch.setattr(gci, "_style_minimal_axes", lambda *args, **kwargs: None)
    monkeypatch.setattr(gci, "_save_and_close_chart", lambda *args, **kwargs: "dummy")

    df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")],
            "rank": [1, 2],
        }
    )

    gci._render_rank_history_chart(df=df, period=2, label="랭킹")

    assert annotate_calls
    assert all(call.get("fontweight") == "semibold" for call in annotate_calls)
