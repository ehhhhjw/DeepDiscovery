import os
import json
import re


# 读取文件夹下的所有文件
def list_files_recursively(folder_path):
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    return all_files


# 读取文件夹下所有文件的文件名
def get_file_names_without_extension(file_paths):
    file_names = []
    for file_path in file_paths:
        # 获取文件名（包含扩展名）
        base_name = os.path.basename(file_path)
        # 去除扩展名
        name_without_extension = os.path.splitext(base_name)[0]
        file_names.append(name_without_extension)
    return file_names


# 读取文件的文件名
def get_file_name_without_extension(file_path):
    base_name = os.path.basename(file_path)
    name_without_extension = os.path.splitext(base_name)[0]
    return name_without_extension


# 读取json文件
def read_json_file(file_path):
    """
    读取并解析JSON文件。

    参数:
    file_path (str): JSON文件的路径。

    返回:
    dict: 解析后的数据，以字典形式返回。
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
    except json.JSONDecodeError:
        print("文件内容不是有效的JSON格式: {file_path}")
    except Exception as e:
        print(f"读取文件时发生错误: {e}")


# 将数据保存为json格式
def save_to_json(data, file_path):
    """
    将数据保存到JSON文件。

    参数:
    data (dict 或 list): 要保存的数据。
    file_path (str): 保存数据的文件路径。
    """
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"数据已成功保存到 {file_path}")
    except Exception as e:
        print(f"保存到JSON文件时发生错误: {e}")


def get_file_extension(file_path):
    """
    Given a file path, return the file extension.

    Parameters:
    file_path (str): The path to the file.

    Returns:
    str: The file extension.
    """
    # 使用 os.path.splitext 分离文件路径和扩展名
    _, extension = os.path.splitext(file_path)
    # 去掉扩展名前面的点
    return extension[1:]


def get_file_name(file_path):
    """
    Given a file path, return the file name with extension.

       Parameters:
       file_path (str): The path to the file.

       Returns:
       str: The file name with extension.
    """
    # 使用 os.path.basename 获取文件名和扩展名
    file_name = os.path.basename(file_path)
    return file_name


def check_node_modules(file_path):
    # 拆分路径为各个部分
    path_parts = file_path.split(os.sep)

    # 检查路径部分中是否包含 "node_modules"
    if "node_modules" in path_parts:
        return 1
    elif "output" in path_parts:
        return 1
    elif ".ast_data" in path_parts:
        return 1
    elif ".venv" in path_parts:
        return 1
    elif ".vscode" in path_parts:
        return 1
    elif "DotTrans" in path_parts:
        return 1
    elif "tree_sitter" in path_parts:
        return 1
    else:
        return 0


def extract_lines_from_file(file_path, start_line, end_line):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

        # Ensure the line numbers are within the of the file
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            print("Invalid line number range.")
            return

        # Extract the lines between the specified line numbers (inclusive)
        extracted_lines = lines[start_line - 1 : end_line]
        return extracted_lines

# 正则解析 import
def extract_import(import_str):
    # 匹配带有花括号和默认导入的导入语句
    import_with_braces_and_default_pattern = re.compile(
        r'^import\s+([\w]+)\s*,?\s*\{?\s*([\w\s,]*)\s*\}?\s*from\s+(?:"([^"]+)"|\'([^\']+)\')\s*;?$'
    )
    # 匹配带有花括号的导入
    import_with_braces_pattern = re.compile(
        r'^import\s+\{?\s*([\w\s,]*)\s*\}?\s*from\s+(?:"([^"]+)"|\'([^\']+)\')\s*;?$'
    )
    # 匹配不包含花括号的简单导入语句 => import "abs.js"
    import_no_braces_pattern = re.compile(r'^import\s+(?:"([^"]+)"|\'([^\']+)\')\s*;?$')
    # 匹配星号导入语句 => import * as AJX from 'xxx.js'
    import_star_pattern = re.compile(r'^import\s+\*\s+as\s+([\w]+)\s+from\s+(?:"([^"]+)"|\'([^\']+)\')\s*;?$')

    # 尝试使用星号导入匹配
    star_match = import_star_pattern.match(import_str)
    if star_match:
        alias = star_match.group(1)
        path = star_match.group(2) or star_match.group(3)
        file_name = path.split("/")[-1]
        result = {"path": path, "file": file_name, "name": [alias]}
    else:
        # 尝试使用新正则匹配带有默认导入和花括号的语法
        default_with_braces_match = import_with_braces_and_default_pattern.match(import_str)
        if default_with_braces_match:
            default_import = default_with_braces_match.group(1)
            named_imports = [n.strip() for n in default_with_braces_match.group(2).split(",") if n.strip()]
            path = default_with_braces_match.group(3) or default_with_braces_match.group(4)
            file_name = path.split("/")[-1]
            result = {"path": path, "file": file_name, "name": [default_import] + named_imports}
        else:
            # 处理简单导入
            simple_match = import_no_braces_pattern.match(import_str)
            if simple_match:
                path = simple_match.group(1) or simple_match.group(2)
                file_name = path.split("/")[-1]
                result = {"path": path, "file": file_name, "name": []}
            else:
                # 如果简单导入不匹配，则使用原有逻辑匹配带有花括号的导入
                match = import_with_braces_pattern.match(import_str)
                if match:
                    path = match.group(2) or match.group(3)
                    names = [n.strip() for n in match.group(1).split(",") if n.strip()]
                    file_name = path.split("/")[-1]
                    result = {"path": path, "file": file_name, "name": names}
                else:
                    # 如果两者都不匹配
                    result = None

    if result:
        result["name"] = [n.split(" as ")[1] if " as " in n else n for n in result["name"]]
    return result

# 测试函数
# print(
#     extract_import('import { getName } from "utils";')
# )
# print(
#     extract_import('import someDefault from "module";')
# )
# print(
#     extract_import('import { foo, bar as baz2 } from "lib/utils";')
# )
# print(extract_import('import ABC from "cde.js"'))
# print(extract_import('import BaseState from "abc/ExampleBaseState.js";'))
# print(extract_import('import "abs.js"'))
# print(extract_import('import * as AJX from "@framework/FOXRax.js";'))
# print(extract_import("import AiVoiceActivityLogUtil, { PageId, AiVoiceActivityActionId } from 'AiVoiceActivityLogUtil.js';"))
# print(extract_import("""import {
#  BaseState,
#  BaseState2
# } from "abc/ExampleBaseState.js";
# """))
# print(1, extract_import("""import {
#  BaseState,
#  BaseState2
# } from 'abc/ExampleBaseState.js';
# """))
