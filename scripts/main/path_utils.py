from __future__ import annotations

import os
import platform
from typing import TYPE_CHECKING

from log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)


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
