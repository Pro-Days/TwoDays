import requests
import os


url = f"https://discord.com/api/v10/applications/{os.getenv("DISCORD_APP_ID")}/guilds/{os.getenv("DISCORD_GUILD_ID")}/commands"

# This is an example USER command, with a type of 2
json = {"name": "name", "description": "description", "type": 1}

# For authorization, you can use either your bot token
headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

r = requests.post(url, headers=headers, json=json)
print(r.json())


# {"name": "stop", "description": "종료", "type": 1}
# {"name": "ip", "description": "ip 주소", "type": 1}
# {"name": "user_count", "description": "유저 수", "type": 1}
# {"name": "server_list", "description": "서버 목록", "type": 1}
# {"name": "cmd", "description": "명령어 목록", "type": 1}
