import os
import json
import requests
import datetime

LOG_CHANNEL_ID = os.getenv("DISCORD_LOG_CHANNEL_ID")
ADMIN_ID = os.getenv("DISCORD_ADMIN_ID")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")


def send_log(log_type, event, msg):
    """
    log_type: 4 - 데이터 업데이트 로그
    log_type: 5 - 데이터 업데이트 에러 로그
    log_type: 6 - 등록, 업데이트
    """

    now = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=9)

    if log_type == 4:
        embed_json = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "cmd": event["action"],
        }

        title = "투다이스 어시스턴트 데이터 업데이트 로그"
        color = 3447003

        fields = []
        for key, value in embed_json.items():
            if value != None:
                fields.append(
                    {
                        "name": key,
                        "value": value,
                        "inline": False,
                    }
                )

    elif log_type == 5:
        embed_json = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "cmd": event["action"],
            "error": msg,
        }

        title = "투다이스 어시스턴트 데이터 업데이트 에러 로그"
        color = 15548997

        fields = []
        for key, value in embed_json.items():
            if value != None:
                fields.append(
                    {
                        "name": key,
                        "value": value,
                        "inline": False,
                    }
                )

    elif log_type == 6:
        embed_json = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "cmd": event["action"],
            "error": msg,
        }

        title = "투다이스 어시스턴트 플레이어 등록 / 업데이트 로그"
        color = 3447003

        fields = []
        for key, value in embed_json.items():
            if value != None:
                fields.append(
                    {
                        "name": key,
                        "value": value,
                        "inline": False,
                    }
                )

    # 로그 전송
    payload = {
        "content": "" if log_type == 4 else f"<@{ADMIN_ID}>",
        "embeds": [{"title": title, "color": color, "fields": fields}],
    }

    url = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"

    headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    print(f"로그 전송 완료: {response.json()}, {msg.replace('\n', '\\n')}")
