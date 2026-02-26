"""차트 이미지 저장 경로와 저장 헬퍼를 제공한다."""

from __future__ import annotations

import os
import platform
import uuid

from scripts.main.shared.utils.path_utils import convert_path


def get_chart_image_path(filename: str = "image.png") -> str:
    base_name, ext = os.path.splitext(filename)
    unique_filename: str = f"{base_name}_{uuid.uuid4().hex}{ext or '.png'}"

    # 운영(Linux)과 로컬(Windows) 저장 위치 규칙을 공통화
    if platform.system() == "Linux":
        return f"/tmp/{unique_filename}"

    return convert_path(f"outputs/{unique_filename}")


def save_and_close_chart(plt, dpi: int = 250, filename: str = "image.png") -> str:
    image_path: str = get_chart_image_path(filename)

    # 저장과 close를 같이 묶어 누락으로 인한 메모리 누수/파일 경로 불일치를 줄임
    plt.savefig(image_path, dpi=dpi, bbox_inches="tight")
    plt.close()

    return image_path
