import requests
import os


def upload_log(data):
    url = os.environ.get("http_feedback_log_url", None)
    if not url:
        return None
    try:
        # 发送 POST 请求
        response = requests.post(url, json=data)
        if response.status_code == 200:
            data = response.json()["data"]
            if "id" in data:
                return data["id"]
    except Exception as e:
        print(e)
    return None
