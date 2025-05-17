import os
import requests


url = f"https://discord.com/api/v10/applications/{os.getenv("DISCORD_APP_ID")}/commands"

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

json_objects = {
    "랭킹": {
        "name": "랭킹",
        "type": 1,
        "integration_types": [0, 1],
        "description": "캐릭터 레벨 랭킹을 보여줍니다.",
        "options": [
            {
                "name": "페이지",
                "description": "페이지 번호 (1~10)",
                "type": 4,
                "required": False,
                "min_value": 1,
                "max_value": 10,
            },
            {
                "name": "기간",
                "description": "랭킹을 조회할 기간 (2~)",
                "type": 4,
                "required": False,
                "min_value": 2,
            },
            {
                "name": "날짜",
                "description": "캐릭터 정보를 조회할 기준 날짜 (YYYY-MM-DD, MM-DD, DD, -1, ...)",
                "type": 3,
                "required": False,
            },
            {
                "name": "나만보기",
                "description": "답변 메시지가 다른사람에게 보이지 않도록 합니다.",
                "type": 5,
                "required": False,
            },
        ],
    },
    "검색": {
        "name": "검색",
        "type": 1,
        "description": "캐릭터 정보를 검색합니다.",
        "integration_types": [0, 1],
        "options": [
            {
                "name": "랭킹",
                "description": "랭킹 히스토리",
                "type": 1,
                "options": [
                    {
                        "name": "닉네임",
                        "description": "캐릭터 닉네임",
                        "type": 3,
                        "required": True,
                    },
                    {
                        "name": "기간",
                        "description": "캐릭터 정보를 조회할 기간 (2~)",
                        "type": 4,
                        "required": False,
                        "min_value": 2,
                    },
                    {
                        "name": "날짜",
                        "description": "캐릭터 정보를 조회할 기준 날짜 (YYYY-MM-DD, MM-DD, DD, -1, ...)",
                        "type": 3,
                        "required": False,
                    },
                    {
                        "name": "나만보기",
                        "description": "답변 메시지가 다른사람에게 보이지 않도록 합니다.",
                        "type": 5,
                        "required": False,
                    },
                ],
            },
            {
                "name": "레벨",
                "description": "레벨 히스토리",
                "type": 1,
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
                        "min_value": 1,
                        "max_value": 5,
                    },
                    {
                        "name": "기간",
                        "description": "캐릭터 정보를 조회할 기간 (2~)",
                        "type": 4,
                        "required": False,
                        "min_value": 2,
                    },
                    {
                        "name": "날짜",
                        "description": "캐릭터 정보를 조회할 기준 날짜 (YYYY-MM-DD, MM-DD, DD, -1, ...)",
                        "type": 3,
                        "required": False,
                    },
                    {
                        "name": "나만보기",
                        "description": "답변 메시지가 다른사람에게 보이지 않도록 합니다.",
                        "type": 5,
                        "required": False,
                    },
                ],
            },
        ],
    },
    "등록": {
        "name": "등록",
        "type": 1,
        "integration_types": [0, 1],
        "description": "일일 정보를 저장하는 캐릭터 목록에 캐릭터를 추가합니다.",
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
                "min_value": 1,
                "max_value": 5,
            },
            {
                "name": "나만보기",
                "description": "답변 메시지가 다른사람에게 보이지 않도록 합니다.",
                "type": 5,
                "required": False,
            },
        ],
    },
}

# For authorization, you can use either your bot token
headers = {"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}

for obj in json_objects.values():
    r = requests.post(url, headers=headers, json=obj)
    print(r.json())

# r = requests.post(url, headers=headers, json=json_objects["검색"])
# print(r.json())
