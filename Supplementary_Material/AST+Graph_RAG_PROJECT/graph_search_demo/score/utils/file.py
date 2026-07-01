import json
import os
import traceback


def save_json_to_file(data, file_path):
    # 获取文件夹路径
    folder_path = os.path.dirname(file_path)

    # 如果文件夹不存在，则创建它
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # 写入 JSON 数据到文件
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"data saved to {file_path}")


def read_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        traceback.print_exc()
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file {file_path}: {e}")
        traceback.print_exc()
        return None


def read_file(file_path):
    file_extension = os.path.splitext(file_path)[-1].lower()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_extension == ".json":
                data = json.load(f)
            elif file_extension == ".txt":
                data = f.read()
            # 可以扩展其他文件类型，比如CSV
            # elif file_extension == ".csv":
            #     import csv
            #     reader = csv.reader(f)
            #     data = [row for row in reader]
            else:
                # 对于未知的文件类型，默认作为文本读取
                data = f.read()
            return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None
