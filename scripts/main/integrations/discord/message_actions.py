"""디스코드 메시지 작업 API."""

from __future__ import annotations

import os

from scripts.main.integrations.discord.discord_client import (
    DISCORD_HTTP_TIMEOUT,
    DiscordHttpResult,
    delete_json,
)


def delete_message(channel_id: str, message_id: str) -> DiscordHttpResult:
    token: str | None = os.getenv("DISCORD_TOKEN")

    if not token:
        raise ValueError("DISCORD_TOKEN must be set in environment variables.")

    url: str = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    headers: dict[str, str] = {"Authorization": f"Bot {token}"}

    return delete_json(
        url,
        headers=headers,
        timeout=DISCORD_HTTP_TIMEOUT,
    )
