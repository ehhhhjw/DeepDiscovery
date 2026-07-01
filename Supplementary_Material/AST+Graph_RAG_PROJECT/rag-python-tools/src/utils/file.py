import json
import os
import traceback


def read_file_content(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {path}: {e}")
        # 打印完整的异常堆栈信息
        traceback.print_exc()
        return ""


def save_json_to_file(data, file_path, cls=None):
    # 获取文件夹路径
    folder_path = os.path.dirname(file_path)

    # 如果文件夹不存在，则创建它
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # 写入 JSON 数据到文件
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, cls=cls)
        print(f"data saved to {file_path}")


def read_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        # 打印完整的异常堆栈信息
        traceback.print_exc()
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file {file_path}: {e}")
        # 打印完整的异常堆栈信息
        traceback.print_exc()
        return None
