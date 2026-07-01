from tree_sitter import Language, Parser
import os
from collections import OrderedDict
from const import (
    Target_Fold_Path,
    File_Function_Path,
    Output_Json_File_Path,
    Class_info_path,
)
from utils import (
    list_files_recursively,
    get_file_names_without_extension,
    get_file_name_without_extension,
    save_to_json,
    read_json_file,
    get_file_extension,
    check_node_modules,
    get_file_name,
    extract_import,
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


def set_imports(imports, extends):
    imports = [import_item for import_item in imports if import_item]
    # 去重
    unique_extends = list(OrderedDict.fromkeys(extends))

    # 处理 import 中 extends 变量和引入的模块名不一致的问题
    _extends = []
    for extend in unique_extends:
        for import_item in imports:
            if extend in import_item["name"]:
                _extends.append(import_item["file"])
    return _extends

# 提取类注释
def extract_class_info(node, source_code):
    source_code_str = source_code.decode("utf-8")
    source_code_list = source_code_str.split("\n")
    result = []
    class_node = None
    comments = []

    imports = []

    # 如果一个文件中没有 class，收集所有的注释
    all_comments = []
    extends = []  # 继承

    # 处理顶层节点，即包含 class
    for child in node.children:
        if child.type == "import_statement":
            text = source_code[child.start_byte : child.end_byte].decode("utf-8")
            imports.append(extract_import(text))

        # 遇到注释就添加
        if child.type == "comment":
            comments.append(child.text.decode("utf-8"))
            all_comments.append(child.text.decode("utf-8"))

        # 如果遇到 class，提取所有的注释，处理结束
        # export class
        elif child.type == "export_statement":
            c_node = child.child_by_field_name("declaration")
            if c_node and c_node.type == "class_declaration":
                result = [comment for comment in comments]
                # 获取 class 的第一行
                fist_line = source_code_list[child.start_point[0]]
                result.append(fist_line)
                class_node = c_node
                for c_child in c_node.children:
                    if c_child.type == "class_heritage":
                        for item in c_child.children:
                            if item.type == "identifier":
                                extends_class = item.text.decode("utf-8")
                                extends.append(extends_class)
                break
        # class
        elif child.type == "class_declaration":
            result = [comment for comment in comments]
            # 获取 class 的第一行
            result.append(source_code_list[child.start_point[0]])
            class_node = child
            break
        else:
            # 如果遇到其他非 class 节点，重新积累注释
            comments = []

    # 清空 comments，继续记录 method 的注释
    comments = []
    # 处理 method
    if not class_node:
        # 如果文件中没有 class，返回全部的注释
        _extends = set_imports(imports, extends)
        return result, _extends, imports

    class_body = None
    for child in class_node.children:
        if child.type == "class_body":
            class_body = child
    # class 没有内容
    if not class_body:
        _extends = set_imports(imports, extends)
        return result, _extends, imports
    for child in class_body.children:
        # 遇到注释就添加
        if child.type == "comment":
            comments.append(child.text.decode("utf-8"))
        # 如果遇到 method，提取所有的注释，处理结束
        elif child.type == "method_definition":
            result += [f"  {comment}" for comment in comments]
            # 获取 class 的第一行
            method_name_node = child.child_by_field_name("name")
            method_name = source_code[
                method_name_node.start_byte : method_name_node.end_byte
            ].decode("utf-8")

            result.append(f"  {method_name}()" + "{}")
            # first_line = source_code[class_node.start_point : class_node.end_point.row]
            class_node = child
            comments = []
            continue
        else:
            # 如果遇到其他非 class 节点，重新积累注释
            comments = []
            
    _extends = set_imports(imports, extends)
    return result, _extends, imports


def extract_objection_names(funcInformationDir, is_in_class, node, source_code):
    in_class_flag = is_in_class
    if node.type == "class_declaration":
        in_class_flag = 1
    if node.type == 'function_declaration':
        return
    if node.type == "variable_declarator":
        for child in node.children:
            if child.type == "identifier":
                if in_class_flag == 0:
                    entity_info = {}
                    function_name = child.text.decode("utf-8")
                    entity_info["Name"] = function_name
                    entity_info["Type"] = "obj"
                    entity_info["Start_Point"] = node.start_point
                    entity_info["End_Point"] = node.end_point
                    funcInformationDir.append(entity_info)
                    # print(function_name)
                    return

    for child in node.children:
        extract_objection_names(funcInformationDir, in_class_flag, child, source_code)


def extract_function_names(
    funcInformationDir, is_in_class, node, source_code, currentMethod=None, status=0
):
    in_class_flag = is_in_class
    if node.type == "class_declaration":
        in_class_flag = 1
    if node.type == "function_declaration":
        for child in node.children:
            if child.type == "identifier" and is_in_class == 0 and status == 0:
                entity_info = {}
                function_name = child.text.decode("utf-8")
                entity_info["Name"] = function_name
                entity_info["Type"] = "func"
                entity_info["Start_Point"] = node.start_point
                entity_info["End_Point"] = node.end_point
                funcInformationDir.append(entity_info)
                # print(function_name)
                # return
                currentMethod = entity_info
                currentMethod["Call"] = []
                # function_declaration 不需要继续递归执行，但是函数分析需要
                status = 1
                break
    if node.type == "call_expression":
        if currentMethod:
            call_expression_name = node.child_by_field_name("function").text.decode()
            currentMethod["Call"].append(call_expression_name)

    for child in node.children:
        extract_function_names(
            funcInformationDir, in_class_flag, child, source_code, currentMethod, status
        )


def extract_class_method_names(
    funcInformationDir, is_in_class, node, source_code, currentMethod=None, status=0
):
    in_class_flag = is_in_class
    if node.type == "class_declaration":
        in_class_flag = 1

    if node.type == "method_definition":
        for child in node.children:
            if child.type == "property_identifier" and is_in_class == 1 and status == 0:
                entity_info = {}
                function_name = child.text.decode("utf-8")
                entity_info["Name"] = function_name
                entity_info["Type"] = "method"
                entity_info["Start_Point"] = node.start_point
                entity_info["End_Point"] = node.end_point
                funcInformationDir.append(entity_info)
                # print(function_name)
                # return
                currentMethod = entity_info
                currentMethod["Call"] = []
                status = 1
                break
    if node.type == "call_expression":
        if currentMethod:
            call_expression_name = node.child_by_field_name("function").text.decode()
            currentMethod["Call"].append(call_expression_name)

    for child in node.children:
        extract_class_method_names(
            funcInformationDir, in_class_flag, child, source_code, currentMethod, status
        )


def extract_class_field_names(
    funcInformationDir, is_in_class, node, source_code, currentMethod=None, status=0
):
    in_class_flag = is_in_class
    if node.type == "class_declaration":
        in_class_flag = 1
    # print(node.type,node.start_point[0])
    if node.type == "field_definition":
        # print(node.type)
        for child in node.children:
            if child.type == "property_identifier" and is_in_class == 1 and status == 0:
                entity_info = {}
                function_name = child.text.decode("utf-8")
                entity_info["Name"] = function_name
                # print(function_name)
                entity_info["Type"] = "method"
                entity_info["Start_Point"] = node.start_point
                entity_info["End_Point"] = node.end_point
                funcInformationDir.append(entity_info)
                # print(function_name)
                # return
                currentMethod = entity_info
                currentMethod["Call"] = []
                status = 1
                break
    if node.type == "call_expression":
        if currentMethod:
            call_expression_name = node.child_by_field_name("function").text.decode()
            currentMethod["Call"].append(call_expression_name)

    for child in node.children:
        extract_class_field_names(
            funcInformationDir, in_class_flag, child, source_code, currentMethod, status
        )


if __name__ == "__main__":
    all_files = list_files_recursively(Target_Fold_Path)

    file_names = get_file_names_without_extension(all_files)

    # source_code = read_source_code(test_path)
    # tree = parse_code(source_code)
    # root_node = tree.root_node
    # func_list = []
    # extract_objection_names(0, root_node, source_code)
    # extract_function_names(0, root_node, source_code)
    # extract_class_method_names(0, root_node, source_code)
    # print(len(funcInformationDir))
    all_class_info = {}
    for file_path in all_files:
        is_contain_node_module = check_node_modules(file_path)
        if is_contain_node_module == 1:
            continue
        print(file_path)
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
        file_name_without_extension = get_file_name_without_extension(file_path)
        file_name_with_extension = get_file_name(file_path)
        if file_name_without_extension == ".DS_Store":
            continue
        source_code = read_source_code(file_path)
        tree = parse_code(source_code)
        root_node = tree.root_node
        func_list = []

        # 提取类信息
        class_info, class_extends, imports = extract_class_info(root_node, source_code)

        if file_name_with_extension not in all_class_info:
            all_class_info[file_name_with_extension] = {}
        all_class_info[file_name_with_extension]["comment"] = "\n".join(class_info)
        all_class_info[file_name_with_extension]["extends"] = class_extends
        all_class_info[file_name_with_extension]["imports"] = imports

        extract_objection_names(funcInformationDir, 0, root_node, source_code)
        extract_function_names(funcInformationDir, 0, root_node, source_code)
        extract_class_field_names(funcInformationDir, 0, root_node, source_code)
        extract_class_method_names(funcInformationDir, 0, root_node, source_code)

        use_temp = funcInformationDir
        FileFuncDir[file_name_with_extension] = use_temp
        # print(file_name,len(funcInformationDir))

        # print(file_name,len(FileFuncDir[file_name]))

    # print(len(FileFuncDir['ExampleData']))

    # 将注释保存到 json
    target_graph_info_list = read_json_file(Output_Json_File_Path)
    # 将类信息保存到 json
    for target_graph_info_item in target_graph_info_list:
        print("target_graph_info_item[Name]: ", target_graph_info_item["Name"])
        info_item = all_class_info[target_graph_info_item["Name"]]
        if not info_item:
            continue
        target_graph_info_item["Description"] = info_item["comment"]
        target_graph_info_item["Extends"] = info_item["extends"]
        target_graph_info_item["Imports"] = info_item["imports"]

    save_to_json(all_class_info, Class_info_path)
    save_to_json(target_graph_info_list, Output_Json_File_Path)
    save_to_json(FileFuncDir, File_Function_Path)
    # print(file_names)

    # js_file_path = '/path/to/project/result_state/ExampleBaseAgent.txt'
    # main(js_file_path)