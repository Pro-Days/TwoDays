import requests
import os


cmd_id = ""

# global commands
url = "https://discord.com/api/v10/applications/{os.getenv('DISCORD_APP_ID')}/commands/" + cmd_id

# guild commands
url = (
    f"https://discord.com/api/v10/applications/{os.getenv('DISCORD_APP_ID')}/guilds/{os.getenv('DISCORD_GUILD_ID')}/commands/"
    + cmd_id
)

# For authorization, you can use either your bot token
headers = {"Authorization": f"Bot {os.getenv("DISCORD_TOKEN")}"}


r = requests.delete(url, headers=headers)
