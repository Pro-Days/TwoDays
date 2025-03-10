import os
import requests


url = f"https://discord.com/api/v10/applications/{os.getenv("DISCORD_APP_ID")}/commands"

# SUB_COMMAND	    1
# SUB_COMMAND_GROUP	2
# STRING	        3
# INTEGER	        4	    Any integer between -2^53 and 2^53
# BOOLEAN	        5
# USER	            6
# CHANNEL	        7	    Includes all channel types + categories
# ROLE	            8
# MENTIONABLE	    9	    Includes users and roles
# NUMBER	        10	    Any double between -2^53 and 2^53
# ATTACHMENT	    11	    attachment object

# json = {
#     "name": "blep",
#     "type": 1,
#     "description": "A Test Command",
#     "options": [
#         {
#             "name": "animal",
#             "description": "The type of animal",
#             "type": 3,
#             "required": True,
#             "choices": [
#                 {"name": "Dog", "value": "animal_dog"},
#                 {"name": "Cat", "value": "animal_cat"},
#                 {"name": "Penguin", "value": "animal_penguin"},
#             ],
#         },
#         {
#             "name": "only_smol",
#             "description": "Whether to show only baby animals",
#             "type": 5,
#             "required": False,
#         },
#     ],
# }

json = {
    "name": "등록",
    "type": 1,
    "description": "일일 정보를 저장하는 캐릭터 목록에 캐릭터를 추가합니다. 캐릭터 정보 검색을 이용할 수 있게됩니다.",
    "options": [
        {
            "name": "닉네임",
            "description": "캐릭터 닉네임",
            "type": 3,
            "required": True,
        },
        {
            "name": "슬롯",
            "description": "메인 캐릭터 (본캐) 슬롯 번호 (1~5)",
            "type": 4,
            "required": False,
        },
    ],
}

# For authorization, you can use either your bot token
headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

r = requests.post(url, headers=headers, json=json)
print(r.json())


## cmd list
{
    "name": "랭킹",
    "type": 1,
    "integration_types": [0, 1],
    "description": "캐릭터 레벨 랭킹을 보여줍니다.",
    "options": [
        {"name": "페이지", "description": "페이지 번호 (1~10)", "type": 4, "required": False},
        {
            "name": "날짜",
            "description": "캐릭터 정보를 조회할 기준 날짜 (YYYY-MM-DD, 어제, 2일전, 저번주, ...)",  # choices 추가
            "type": 3,
            "required": False,
        },
    ],
}
{
    "name": "검색",
    "type": 1,
    "integration_types": [0, 1],
    "description": "캐릭터의 정보를 보여줍니다.",
    "options": [
        {
            "name": "닉네임",
            "description": "캐릭터 닉네임",
            "type": 3,
            "required": True,
        },
        {
            "name": "슬롯",
            "description": "캐릭터 슬롯 번호 (1~5)",
            "type": 4,
            "required": False,
        },
        {
            "name": "기간",
            "description": "캐릭터 정보를 조회할 기간 (1~365)",
            "type": 4,
            "required": False,
        },
        {
            "name": "날짜",
            "description": "캐릭터 정보를 조회할 기준 날짜 (YYYY-MM-DD, 어제, 2일전, 저번주, ...)",
            "type": 3,
            "required": False,
        },
    ],
}
{
    "name": "등록",
    "type": 1,
    "integration_types": [0, 1],
    "description": "일일 정보를 저장하는 캐릭터 목록에 캐릭터를 추가합니다. 캐릭터 정보 검색을 이용할 수 있게됩니다.",
    "options": [
        {
            "name": "닉네임",
            "description": "캐릭터 닉네임",
            "type": 3,
            "required": True,
        },
        {
            "name": "슬롯",
            "description": "메인 캐릭터 (본캐) 슬롯 번호 (1~5)",
            "type": 4,
            "required": False,
        },
    ],
}
