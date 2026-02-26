from __future__ import annotations

import os
import platform
from typing import TYPE_CHECKING

from scripts.main.shared.utils.log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)

FONT_PATH_ENV_VAR: str = "FONT_PATH"


def convert_path(path: str) -> str:
    """
    운영 체제에 따라 경로를 변환함
    윈도우에서는 백슬래시를 사용하고, 유닉스에서는 슬래시를 사용
    """

    if platform.system() == "Windows":
        system_path: str = path.replace("/", "\\")

    else:
        system_path = path.replace("\\", "/")

    converted: str = os.path.normpath(system_path)

    logger.debug("convert_path: " f"input={path} " f"output={converted}")

    return converted


def get_font_path() -> str:
    """폰트 경로 환경 변수를 읽어 정규화된 경로를 반환한다."""

    env_font_path: str | None = os.getenv(FONT_PATH_ENV_VAR)
    if env_font_path:
        font_path: str = os.path.normpath(env_font_path)
        logger.debug(
            "get_font_path: "
            f"source=env "
            f"env_var={FONT_PATH_ENV_VAR} "
            f"path={font_path}"
        )

        return font_path

    message: str = (
        "FONT_PATH environment variable is required for font loading. "
        f"env_var={FONT_PATH_ENV_VAR}"
    )
    logger.error(
        "get_font_path failed: " f"reason=missing_env " f"env_var={FONT_PATH_ENV_VAR}"
    )
    raise RuntimeError(message)
