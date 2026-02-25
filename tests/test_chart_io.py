"""Tests for chart IO helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from scripts.main.shared.chart import chart_io
from tests.support import bootstrap  # noqa: F401


class ChartIoTest(unittest.TestCase):
    def test_get_chart_image_path_linux(self) -> None:
        fake_uuid = SimpleNamespace(hex="abc123")
        with mock.patch(
            "scripts.main.shared.chart.chart_io.platform.system", return_value="Linux"
        ):
            with mock.patch(
                "scripts.main.shared.chart.chart_io.uuid.uuid4", return_value=fake_uuid
            ):
                path = chart_io.get_chart_image_path("img.png")
        self.assertEqual(path, "/tmp/img_abc123.png")

    def test_get_chart_image_path_non_linux_uses_convert_path(self) -> None:
        fake_uuid = SimpleNamespace(hex="xyz")
        with mock.patch(
            "scripts.main.shared.chart.chart_io.platform.system", return_value="Windows"
        ):
            with mock.patch(
                "scripts.main.shared.chart.chart_io.uuid.uuid4", return_value=fake_uuid
            ):
                with mock.patch(
                    "scripts.main.shared.chart.chart_io.convert_path",
                    return_value="converted.png",
                ) as convert_mock:
                    path = chart_io.get_chart_image_path("img")
        self.assertEqual(path, "converted.png")
        convert_mock.assert_called_once_with("img_xyz.png")

    def test_save_and_close_chart_calls_plt(self) -> None:
        plt = mock.Mock()
        with mock.patch(
            "scripts.main.shared.chart.chart_io.get_chart_image_path",
            return_value="/tmp/test.png",
        ):
            result = chart_io.save_and_close_chart(plt, dpi=123, filename="x.png")
        self.assertEqual(result, "/tmp/test.png")
        plt.savefig.assert_called_once_with(
            "/tmp/test.png", dpi=123, bbox_inches="tight"
        )
        plt.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
