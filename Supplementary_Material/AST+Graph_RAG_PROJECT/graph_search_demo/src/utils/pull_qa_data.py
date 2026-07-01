import os
import json
import requests
from constants import QADATA_URL


def fetch_json_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功，如果不是，会抛出HTTPError
        json_data = response.json()  # 解析JSON数据
        return json_data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


def pull_latest_data():
    # 如果  example 里内置了 qa.json 优先使用，否则去
    qa_json_path = "./examples/qa/qa.json"
    if os.path.isfile(qa_json_path):
        with open(qa_json_path, "r", encoding="utf-8") as qa_file:
            return json.load(qa_file)
    All_Message = []
    maxid = 0
    while 1:
        this_url = QADATA_URL + str(maxid)
        print(this_url)
        json_data = fetch_json_from_url(this_url)
        if json_data:
            if len(json_data["data"]) == 0:
                break
            else:
                for i in range(len(json_data["data"])):
                    one_message = {}
                    one_message["id"] = json_data["data"][i]["id"]
                    one_message["chat_query"] = json_data["data"][i][
                        "chat_query"
                    ]
                    one_message["chat_answer"] = json_data["data"][i][
                        "chat_answer"
                    ]
                    one_message["gmt_create"] = json_data["data"][i][
                        "gmt_create"
                    ]
                    maxid = max(maxid, one_message["id"])
                    if one_message["chat_answer"] == None:
                        continue
                    All_Message.append(one_message)
        else:
            break
    return All_Message
