from tree_sitter import Language, Parser
import os
import json
from const import Target_Fold_Path, File_Comment_Path
from utils import (
    list_files_recursively,
    get_file_name_without_extension,
    save_to_json,
    get_file_name,
    get_file_extension,
    check_node_modules,
)

# 加载已编译的语言库
Language.build_library(
    "build/my-languages.so",
    [
        f"{os.getcwd()}/tree_sitter/tree-sitter-javascript",
    ],
)

JS_LANGUAGE = Language("build/my-languages.so", "javascript")

# 初始化解析器
parser = Parser()
parser.set_language(JS_LANGUAGE)


FileFuncDir = {}


# 读取JavaScript文件内容
def read_source_code(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().encode()


# 解析JavaScript代码
def parse_code(code):
    return parser.parse(code)


def extract_code_note(funcInformationDir, is_in_class, node, source_code):

    if node.type == "comment":
        entity_info = {}
        function_name = node.text.decode("utf-8")
        entity_info["Name"] = function_name
        entity_info["Start_Point"] = node.start_point
        entity_info["End_Point"] = node.end_point
        funcInformationDir.append(entity_info)
        return

    for child in node.children:
        extract_code_note(funcInformationDir, is_in_class, child, source_code)


if __name__ == "__main__":
    all_files = list_files_recursively(Target_Fold_Path)

    FileFuncDir = {}

    for file_path in all_files:
        is_contain_node_module = check_node_modules(file_path)
        if is_contain_node_module == 1:
            continue
        file_extension_name = get_file_extension(file_path)
        if (
            file_extension_name != "js"
            and file_extension_name != "jsx"
            and file_extension_name != "page"
            and file_extension_name != "ts"
            and file_extension_name != "tsx"
        ):
            continue
        # print(file_path)
        funcInformationDir = []
        file_name = get_file_name_without_extension(file_path)
        file_name_with_extension = get_file_name(file_path)
        if file_name == ".DS_Store":
            continue
        source_code = read_source_code(file_path)
        tree = parse_code(source_code)
        root_node = tree.root_node
        extract_code_note(funcInformationDir, 0, root_node, source_code)
        FileFuncDir[file_name_with_extension] = funcInformationDir

    save_to_json(FileFuncDir, File_Comment_Path)
