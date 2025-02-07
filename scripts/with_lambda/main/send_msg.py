import os
import json
import requests
import datetime
from pytz import timezone

import misc

LOG_CHANNEL_ID = os.getenv("DISCORD_LOG_CHANNEL_ID")
ADMIN_ID = os.getenv("DISCORD_ADMIN_ID")


def send(event, msg, image=None, log_type=1, error=None):
    body = json.loads(event["body"])
    interaction_token = body.get("token")

    payload = {"content": msg}

    if image:
        with open(image, "rb") as f:
            file_data = f.read()

        url = f"https://discord.com/api/v10/webhooks/{os.getenv('DISCORD_APP_ID')}/{interaction_token}"
        multipart_data = {
            "payload_json": (None, json.dumps(payload), "application/json"),
            "file": (image, file_data, "application/octet-stream"),
        }

        response = requests.post(url, files=multipart_data)

        print(f"메시지 전송 완료: {response.json()}, {msg.replace('\n', '\\n')}")

        send_log(log_type, event, msg if error == None else error, image)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "메시지 전송 성공", "response": response.json(), "msg": msg}),
        }

    else:
        url = f"https://discord.com/api/v10/webhooks/{os.getenv("DISCORD_APP_ID")}/{interaction_token}/messages/@original"

        headers = {"Content-Type": "application/json"}

        response = requests.patch(url, headers=headers, data=json.dumps(payload))

        print(f"메시지 전송 완료: {response.json()}, {msg.replace('\n', '\\n')}")

        send_log(log_type, event, msg if error == None else error)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "메시지 전송 성공", "response": response.json(), "msg": msg}),
        }


def send_log(log_type, event, msg, image=None):
    """
    log_type: 1 - 명령어 로그
    log_type: 2 - 관리자 명령어 로그
    log_type: 3 - 에러 로그
    """

    body = json.loads(event["body"])

    guild_id = body["guild_id"]
    guild_name = misc.get_guild_name(guild_id)
    channel_id = body["channel"]["id"]
    channel_name = body["channel"]["name"]
    member_id = body["member"]["user"]["id"]
    member_name = body["member"]["user"]["global_name"]
    member_username = body["member"]["user"]["username"]

    if (log_type == 1) or (log_type == 2):

        embed_json = {
            "time": datetime.datetime.now(timezone("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S"),
            "server": f"{guild_name} ({guild_id})",
            "channel": f"{channel_name} ({channel_id})",
            "author": f"{member_name} - {member_username} ({member_id})",
            "cmd": (
                f"{body["data"]["name"]}\n{', '.join([f"{option['name']}: {option['value']}" for option in body['data']['options']])}"
                if "options" in body["data"]
                else body["data"]["name"]
            ),
            "msg": msg,
        }

        if log_type == 1:
            title = "투다이스 어시스턴트 명령어 로그"
            color = 3447003

        elif log_type == 2:
            title = "투다이스 어시스턴트 관리자 명령어 로그"
            color = 10181046

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

    elif log_type == 3:
        embed_json = {
            "time": datetime.datetime.now(timezone("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S"),
            "server": f"{guild_name} ({guild_id})",
            "channel": f"{channel_name} ({channel_id})",
            "author": f"{member_name} - {member_username} ({member_id})",
            "cmd": (
                f"{body["data"]["name"]}\n{', '.join([f"{option['name']}: {option['value']}" for option in body['data']['options']])}"
                if "options" in body["data"]
                else body["data"]["name"]
            ),
            "error": msg,
        }

        title = "투다이스 어시스턴트 명령어 에러 로그"
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

    # 로그 전송
    payload = (
        {"content": "", "embeds": [{"title": title, "color": color, "fields": fields}]}
        if log_type != 3
        else {
            "content": f"<@{ADMIN_ID}>",
            "embeds": [{"title": title, "color": color, "fields": fields}],
        }
    )

    url = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"

    headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}", "Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # 이미지 전송
    if image:
        with open(image, "rb") as f:
            file_data = f.read()

        payload = {
            "content": "",
        }
        headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

        url = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"

        multipart_data = {
            "payload_json": (None, json.dumps(payload), "application/json"),
            "file": (image, file_data, "application/octet-stream"),
        }

        response = requests.post(url, headers=headers, files=multipart_data)

    print(f"로그 전송 완료: {response.json()}, {msg.replace('\n', '\\n')}")
