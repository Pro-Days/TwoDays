from __future__ import annotations

from typing import TYPE_CHECKING, Any

import data_manager
import mojang
from log_utils import get_logger

if TYPE_CHECKING:
    from logging import Logger

logger: Logger = get_logger(__name__)


def get_profile_from_name(name: str) -> tuple[str | None, str | None]:
    """
    닉네임으로 name, UUID 가져오기
    """

    logger.info(f"get_profile_from_name start: name={name}")

    # DB 캐시를 먼저 보고, 없을 때만 외부 API를 호출해 지연과 제한을 줄임
    metadata: dict[str, Any] | None = data_manager.manager.find_user_metadata_by_name(
        name
    )

    if metadata:
        logger.info(f"profile lookup source=metadata: name={name}")

        real_name = metadata["Name"]
        pk: str = metadata["PK"]
        uuid: str | None = data_manager.manager.uuid_from_user_pk(pk)

    else:
        logger.info(f"profile lookup source=mojang: name={name}")

        api = mojang.API(retry_on_ratelimit=True, ratelimit_sleep_time=1)
        uuid: str | None = api.get_uuid(name)
        real_name: str | None = api.get_username(uuid) if uuid else None

        logger.info(
            "mojang profile lookup result: "
            f"input={name} "
            f"resolved_name={real_name} "
            f"uuid={uuid}"
        )

    if not uuid or not real_name:
        logger.warning("failed to resolve profile: " f"name={name}")

        return None, None

    logger.info(
        "resolved profile: "
        f"input={name} "
        f"resolved_name={real_name} "
        f"uuid={uuid}"
    )

    return real_name, uuid


def get_name_from_uuid(uuid: str) -> str | None:
    """
    UUID로 name 가져오기
    """

    logger.debug("get_name_from_uuid start: " f"uuid={uuid}")

    # 이름 조회도 동일하게 메타데이터 캐시 우선 정책을 사용
    metadata: dict[str, Any] | None = data_manager.manager.get_user_metadata(uuid)

    if metadata:
        logger.debug("name found in metadata cache: " f"uuid={uuid}")

        real_name: str | None = metadata["Name"]

    else:
        logger.debug("name not in metadata cache, querying Mojang API: " f"uuid={uuid}")

        api = mojang.API(retry_on_ratelimit=True, ratelimit_sleep_time=1)
        real_name = api.get_username(uuid)

    if not real_name:
        logger.warning("failed to resolve name: " f"uuid={uuid}")

        return None

    logger.debug("resolved name: " f"uuid={uuid} " f"name={real_name}")

    return real_name


def get_profiles_from_mc(names: list[str]) -> dict[str, dict[str, str]]:
    logger.info("get_profile_from_mc start: " f"requested_count={len(names)}")

    api = mojang.API(retry_on_ratelimit=True, ratelimit_sleep_time=1)
    # 10개씩 나눠 조회
    chunk_size = 10
    chunked_list: list[list[str]] = [
        names[i : i + chunk_size] for i in range(0, len(names), chunk_size)
    ]

    profiles: dict[str, dict[str, str]] = {}

    for chunk in chunked_list:
        try:
            uuids: dict[str, str] = api.get_uuids(chunk)
            logger.debug(
                "mojang bulk profile chunk resolved: "
                f"chunk_size={len(chunk)} "
                f"resolved={len(uuids)}"
            )

        except Exception:
            logger.exception("mojang bulk profile chunk failed: " f"chunk={chunk}")

            continue

        # 원본 입력 대소문자를 유지하려고 요청 목록 기준 키로 다시 매핑
        for name, uuid in uuids.items():
            for requested_name in names:
                if name.lower() == requested_name.lower():
                    profiles[requested_name] = {"uuid": uuid, "name": name}

    logger.info("get_profile_from_mc complete: " f"resolved_count={len(profiles)}")

    return profiles
