####  用来获取文件夹下中每个文件的class对应的description

import os
import json
import queue
import re

import os


# 读取文件夹下的所有文件
def list_files_recursively(folder_path):
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    return all_files

# 读取文件的文件名
def get_file_name_without_extension(file_path):
    base_name = os.path.basename(file_path)
    name_without_extension = os.path.splitext(base_name)[0]
    return name_without_extension

def write_string_to_file(file_name, content):
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(content)

def find_description(file_path, class_identifier):
    # class_identifier = '@class ExampleAgentConfig'
    description_identifier = '@description'
    
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        
    for i, line in enumerate(lines):
        if class_identifier in line:
            # Check the next lines for the description
            for j in range(i + 1, len(lines)):
                if description_identifier in lines[j]:
                    description_line = lines[j].replace('*', '').strip()
                    cleaned_description = description_line.replace('@description ', '')
                    return cleaned_description
    return None


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
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
    except json.JSONDecodeError:
        print("文件内容不是有效的JSON格式: {file_path}")
    except Exception as e:
        print(f"读取文件时发生错误: {e}")


def extract_functions_from_js(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        js_code = f.read()

    # 正则表达式匹配函数
    regex = r"/\*\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/|function\s+\w+\s*\([^)]*\)\s*\{[^}]*\}|([a-zA-Z_$][0-9a-zA-Z_$]*)\s*:\s*function\s*\([^)]*\)\s{[^}]*\}|[a-zA-Z_$][0-9a-zA-Z_$]*\s*\(\)[^}]*\}"

    matches = re.findall(regex, js_code)
    
    functions = []

    for match in matches:
        match_content = match[0].strip()
        if match_content.startswith('/**'):
            current_comment = match_content
        else:
            function_name = re.search(r"(get\s+|set\s+)?(?P<name>[a-zA-Z0-9_]+)\s*(\([a-zA-Z0-9_, ]*\))", match_content)
            if function_name:
                function_name = function_name.group('name') + function_name.group(3)
                report = re.search(r"@returns {(\w+)} - (.+)", current_comment)
                report_text = report.group(2) if report else ''
                functions.append({"Name": function_name, "Report": report_text})
    
    return functions


if __name__ == "__main__":
    target_graph_path="/path/to/project/Output/target_graph_information.json"
    Note_Fold_Path = '/path/to/project/result_state_note/result_state_new'  # 替换为您的文件夹路径
    Description_Fold_Path='/path/to/project/Output/result_state_description'

    
    data = read_json_file(target_graph_path)
    print(data)


    all_files = list_files_recursively(Note_Fold_Path)


    for file_path_son in all_files:
        file_name=''
        suffix=''
        if '/' in file_path_son:
            file_name = file_path_son.split('/')[-1]
            if '.' in file_path_son:
                suffix = file_path_son.split('.')[-1]
                if suffix != 'txt':
                    continue
                else:
                    output_file_path=Description_Fold_Path+'/'+file_name
                    class_name=get_file_name_without_extension(file_path_son)
                    description_message=find_description(file_path_son,'@class ')

                    Output_Description_Fold_Path=Description_Fold_Path+"/"+file_name
                    # write_string_to_file(Output_Description_Fold_Path,description_message)


    # # 输出结果
    # print(json.dumps(function_details, indent=4, ensure_ascii=False))