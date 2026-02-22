import json
import os
import time

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
except ImportError:
    pass

import misc
import requests

LOG_CHANNEL_ID: str | None = os.getenv("DISCORD_LOG_CHANNEL_ID")
ADMIN_ID: str | None = os.getenv("DISCORD_ADMIN_ID")
DISCORD_TOKEN: str | None = os.getenv("DISCORD_TOKEN")

if not LOG_CHANNEL_ID or not ADMIN_ID or not DISCORD_TOKEN:
    print(LOG_CHANNEL_ID is not None, ADMIN_ID is not None, DISCORD_TOKEN is not None)
    raise ValueError(
        "DISCORD_LOG_CHANNEL_ID, DISCORD_ADMIN_ID, and DISCORD_TOKEN must be set in environment variables."
    )


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
            "body": json.dumps(
                {"message": "메시지 전송 성공", "response": response.json(), "msg": msg}
            ),
        }

    # 이미지 없음
    url = f"https://discord.com/api/v10/webhooks/{os.getenv('DISCORD_APP_ID', None)}/{interaction_token}/messages/@original"

    headers = {"Content-Type": "application/json"}

    response = requests.patch(url, headers=headers, data=json.dumps(payload))

    print(f"메시지 전송 완료: {response.json()}, {msg.replace('\n', '\\n')}")

    send_log(log_type, event, msg if error == None else error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "메시지 전송 성공", "response": response.json(), "msg": msg}
        ),
    }


def send_log(log_type, event, msg="", image=None):
    """
    log_type: 1 - 명령어 로그
    log_type: 2 - 관리자 명령어 로그
    log_type: 3 - 디스코드 에러 로그
    log_type: 4 - 데이터 업데이트 로그
    log_type: 5 - 데이터 업데이트 에러 로그
    log_type: 6 - 플레이어 등록 / 업데이트 로그
    # TODO: enum
    """

    now = f"<t:{int(time.time())}:f>"

    if log_type in [1, 2, 3]:
        body = json.loads(event["body"])
        command_type = body["authorizing_integration_owners"].keys()  # 0: 서버, 1: 유저

        guild_id = body["guild_id"]
        channel_id = body["channel"]["id"]
        member_id = body["member"]["user"]["id"]
        member_name = body["member"]["user"]["global_name"]
        member_username = body["member"]["user"]["username"]

        guild_name = misc.get_guild_name(guild_id)
        channel_name = body["channel"]["name"]

        if (log_type == 1) or (log_type == 2):

            if "0" in command_type:
                embed_json = {
                    "time": now,
                    "type": "서버",
                    "server": f"{guild_name} ({guild_id})",
                    "channel": f"{channel_name} ({channel_id})",
                    "author": f"{member_name} - {member_username} ({member_id})",
                    "cmd": (
                        f"{body["data"]["name"]}\n{body['data']['options']}"
                        if "options" in body["data"]
                        else body["data"]["name"]
                    ),
                    "msg": msg,
                }
            else:
                embed_json = {
                    "time": now,
                    "type": "유저",
                    "server": f"{guild_id}",
                    "channel": f"{channel_id}",
                    "author": f"{member_name} - {member_username} ({member_id})",
                    "cmd": (
                        f"{body["data"]["name"]}\n{body['data']['options']}"
                        if "options" in body["data"]
                        else body["data"]["name"]
                    ),
                    "msg": msg,
                }

            if log_type == 1:
                title = "투데이즈 명령어 로그"
                color = 3447003

            else:  # 2
                title = "투데이즈 관리자 명령어 로그"
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
            if "0" in command_type:
                embed_json = {
                    "time": now,
                    "type": "서버",
                    "server": f"{guild_name} ({guild_id})",
                    "channel": f"{channel_name} ({channel_id})",
                    "author": f"{member_name} - {member_username} ({member_id})",
                    "cmd": (
                        f"{body["data"]["name"]}\n{body['data']['options']}"
                        if "options" in body["data"]
                        else body["data"]["name"]
                    ),
                    "error": msg,
                }
            else:
                embed_json = {
                    "time": now,
                    "type": "유저",
                    "server": f"{guild_id}",
                    "channel": f"{channel_id}",
                    "author": f"{member_name} - {member_username} ({member_id})",
                    "cmd": (
                        f"{body["data"]["name"]}\n{body['data']['options']}"
                        if "options" in body["data"]
                        else body["data"]["name"]
                    ),
                    "error": msg,
                }

            title = "투데이즈 명령어 에러 로그"
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

        else:
            return

    else:
        if log_type == 4:
            embed_json = {
                "time": now,
                "cmd": event["action"],
            }

            title = "투데이즈 데이터 업데이트 로그"
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
                "time": now,
                "cmd": event["action"],
                "error": msg,
            }

            title = "투데이즈 데이터 업데이트 에러 로그"
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
                "time": now,
                "cmd": event["action"],
                "user-type": msg,
            }

            title = "투데이즈 플레이어 등록 / 업데이트 로그"
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

        else:
            return

    # 로그 전송
    payload = {
        "content": "" if log_type in [1, 2, 4] else f"<@{ADMIN_ID}>",
        "embeds": [{"title": title, "color": color, "fields": fields}],
    }

    url = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"

    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # 이미지 전송
    if image:
        with open(image, "rb") as f:
            file_data = f.read()

        payload = {
            "content": "",
        }
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}

        url = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"

        multipart_data = {
            "payload_json": (None, json.dumps(payload), "application/json"),
            "file": (image, file_data, "application/octet-stream"),
        }

        response = requests.post(url, headers=headers, files=multipart_data)

    print(f"로그 전송 완료: {response.json()}, {msg.replace('\n', '\\n')}")
