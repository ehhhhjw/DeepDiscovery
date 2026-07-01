import os
import json
import re
import time
import tiktoken
import queue
import itertools
import asyncio
import networkx as nx
from typing import List
from collections import defaultdict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from tenacity import retry, stop_after_attempt, wait_fixed
from langchain_core.pydantic_v1 import BaseModel, Field
from prompts.new_community import (
    COMMUNITY_REPORT_PROMPT
)
from services.model_config import report_model

from constants import (
    DEPENDENCE_POWER,
    CALL_POWER,
    EXTEND_POWER,
    CHILDREN_POWER,
    PAGELIST_POWER,
    LEIDAN_POWER_LIST,
    FOLDER_POWER_LIST,
    QA_RERANK_POWER_LIST,
    QA_COMMUNITY_POWER,
    COMMIT_POWER,
    MAX_FOLD_FILE_NUM,
    MAX_COMMIT_FILE_NUM,
    FILTER_THRESHOLD,
    MIN_COMMUNITY_SIZE,
    DOMAIN_KNOWLEDGE_POWER,
    DEGRADATION_SCOPE,
    DEGRADATION_WEIGHT,
    FILTER_NODE_MODULE,
    SUITABLE_EXTENSION,
    MAX_RETRY_ATTEMPTS,
    WAIT_SECONDS,
    EdgeType,
)

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


def desolve_leidan(leidan_message_information):
    leidan_map = {}
    for node in leidan_message_information:
        node_temp = {}
        node_temp["level"] = node["level"]
        node_temp["nodes"] = node["nodes"]
        node_temp["edges"] = node["edges"]
        leidan_map[node["community_id"]] = node_temp
    return leidan_map
# 判断实体名是否以FOX开头
def judge_fox_front_entity(entity_name):
    return entity_name[:3].upper() == "FOX"

# 提取code_graph中有用的信息，并记录name到id的映射
# node_name_to_id_MP存储了非埋点的Name到ID的映射
# all_node_name_to_id_MP存储了所有节点的Name到ID的映射
def get_useful_information_of_code_graph(code_graph_information):
    code_graph_information_nodes = code_graph_information["nodes"]
    node_name_to_id_MP = {}
    all_node_name_to_id_MP = {}
    the_useful_information = {}
    for one_node in code_graph_information_nodes:
        all_node_name_to_id_MP[one_node["name"]] = one_node["id"]
        # # 如果要保留埋点信息，就将下面两行代码注释掉
        # if one_node["isLog"] == 1:
        #     continue
        if judge_fox_front_entity(one_node["name"]):
            continue
        one_useful_info = {}
        one_useful_info["name"] = one_node["name"]
        one_useful_info["type"] = one_node["type"]
        one_useful_info["pageList"] = one_node["pageList"]
        one_useful_info["community_id"] = one_node["community_id"]
        one_useful_info["id"] = one_node["id"]
        one_useful_info["report"] = one_node["report"]
        the_useful_information["id"] = one_useful_info
        node_name_to_id_MP[one_useful_info["name"]] = one_useful_info["id"]
    
    return the_useful_information, node_name_to_id_MP, all_node_name_to_id_MP
    

# 提取ast_graph中有用的信息
def get_useful_information_of_ast_graph(ast_graph_information):
    Import_Edge_Information = {}
    Method_Edge_Information = {}
    G = nx.DiGraph()
    data = ast_graph_information
    node_map = {}
    for node in data:
        import_node_edge = []
        method_node_edge = []
        if node["Name"] not in node_map:
            id = len(node_map)
            node_map[node["Name"]] = id
            for _ in ["Report", "Comment", "Description", "FileContent"]:
                if _ not in node:
                    node[_] = ""
            G.add_node(
                id,
                name=node["Name"],
                isLog=node["IsUtLog"],
                report=node["Report"],
                comment=node["Comment"],
                description=node["Description"],
                path=node["Root"],
                type=node["Type"],
                pageList=node["RootPage"],
                file_content=node["FileContent"],
                is_leaf=False,
                community_id=[],
            )
        if "DependentEdgeInformation" in node:
            for target in node["DependentEdgeInformation"]:
                import_node_edge.append(target)
        for child in node["Children"]:
            if "RelatedScore" in child:
                target_temp = {}
                target_temp["Name"] = node["Name"] + "." + child["Name"]
                target_temp["RelatedScore"] = child["RelatedScore"]
                target_temp["ScoreReason"] = child["ScoreReason"]
                method_node_edge.append(target_temp)
            child["Name"] = node["Name"] + "." + child["Name"]
            if child["Name"] not in node_map:
                id = len(node_map)
                node_map[child["Name"]] = id
                for _ in ["Report", "Comment", "Code"]:
                    if _ not in child:
                        child[_] = ""
                code_comment = ""
                if "codeComment" in child:
                    code_comment = "\n".join(
                        [
                            comment.lstrip("/ ").strip()
                            for comment in child["codeComment"]
                        ]
                    )
                G.add_node(
                    id,
                    name=child["Name"],
                    isLog=child["IsUtLog"],
                    report=child["Report"],
                    comment=child["Comment"],
                    description=child["Code"],
                    path=node["Root"],
                    type=child["Type"],
                    pageList=child["RootPage"],
                    code_comment=code_comment,
                    is_leaf=True,
                    community_id=[],
                )
        Import_Edge_Information[node["Name"]] = import_node_edge
        Method_Edge_Information[node["Name"]] = method_node_edge

    for s in data:
        # class - class, class - method/object/function/others
        source_node = node_map[s["Name"]]
        child_nodes = [
            {"id": node_map[c["Name"]], "type": EdgeType.CHILD}
            for c in s["Children"]
            if c["Name"] in node_map
        ]
        dependent_nodes = [
            {"id": node_map[c], "type": EdgeType.DEPENDENT}
            for c in s["Dependent"]
            if c in node_map
        ]
        extends_nodes = [
            {"id": node_map[c], "type": EdgeType.EXTENDS}
            for c in s["Extends"]
            if c in node_map
        ]
        target_nodes = child_nodes + dependent_nodes + extends_nodes
        for t in target_nodes:
            G.add_edge(source_node, t["id"], type=t["type"])
        # function calls function (from other files)
        for child_node in s["Children"]:
            if child_node["Name"] not in node_map:
                continue
            child_node_id = node_map[child_node["Name"]]
            for outer_node in child_node["Call"]:
                outer_node_name = (
                    outer_node["file"]
                    + "."
                    + (outer_node["name"] or "null")
                )
                if outer_node_name not in node_map:
                    continue
                outer_node_id = node_map[outer_node_name]
                G.add_edge(child_node_id, outer_node_id, type=EdgeType.CALL)
    return G, Import_Edge_Information, Method_Edge_Information

# 构建基础的边图信息，初始化节点
def construct_base_edge_power_graph(code_graph_information):
    base_edge_power_graph = {}

    code_graph_information_nodes = code_graph_information["nodes"]
    for one_node in code_graph_information_nodes:
        # # 如果要保留埋点信息，就将下面两行代码注释掉
        # if one_node["isLog"] == 1:
        #     continue
        one_point_edge_power_graph = {}
        this_node_id = one_node["id"]
        one_point_edge_power_graph["name"] = one_node["name"]
        one_point_edge_power_graph["type"] = one_node["type"]
        one_point_edge_power_graph["edgeList"] = {}
        base_edge_power_graph[this_node_id] = one_point_edge_power_graph
    
    return base_edge_power_graph

# 添加Dependent边权信息
def add_dependent_edge(one_entity_dependent, one_entity_id, node_name_to_id_MP, edge_power_graph):
    for one_dependent in one_entity_dependent:
        one_dependent_name = one_dependent
        if one_dependent_name not in node_name_to_id_MP:
            continue
        one_dependent_id = node_name_to_id_MP[one_dependent_name]
        if one_dependent_id in edge_power_graph[one_entity_id]["edgeList"]:
            edge_power_graph[one_entity_id]["edgeList"][one_dependent_id]["totalPower"] += DEPENDENCE_POWER
            edge_power_graph[one_entity_id]["edgeList"][one_dependent_id]["powerList"].append(DEPENDENCE_POWER)
            edge_power_graph[one_entity_id]["edgeList"][one_dependent_id]["relationList"].append("DEPENDENCE")
        else:
            one_dependent_edge = {}
            one_dependent_edge["name"] = one_dependent_name
            one_dependent_edge["totalPower"] = DEPENDENCE_POWER
            one_dependent_edge["powerList"] = [DEPENDENCE_POWER]
            one_dependent_edge["relationList"] = ["DEPENDENCE"]
            edge_power_graph[one_entity_id]["edgeList"][one_dependent_id] = one_dependent_edge

# 添加Extend边权信息
def add_extend_edge(one_entity_extend, one_entity_id, node_name_to_id_MP, edge_power_graph):
    for one_extend in one_entity_extend:
        one_extend_name = one_extend
        if one_extend_name not in node_name_to_id_MP:
            continue
        one_extend_id = node_name_to_id_MP[one_extend_name]
        if one_extend_id in edge_power_graph[one_entity_id]["edgeList"]:
            edge_power_graph[one_entity_id]["edgeList"][one_extend_id]["totalPower"] += EXTEND_POWER
            edge_power_graph[one_entity_id]["edgeList"][one_extend_id]["powerList"].append(EXTEND_POWER)
            edge_power_graph[one_entity_id]["edgeList"][one_extend_id]["relationList"].append("EXTEND")
        else:
            one_extend_edge = {}
            one_extend_edge["name"] = one_extend_name
            one_extend_edge["totalPower"] = EXTEND_POWER
            one_extend_edge["powerList"] = [EXTEND_POWER]
            one_extend_edge["relationList"] = ["EXTEND"]
            edge_power_graph[one_entity_id]["edgeList"][one_extend_id] = one_extend_edge
    
# 添加Children边权信息, 类指向方法与方法指向类
def add_children_edge(one_entity_children, one_entity_id, one_entity_name, node_name_to_id_MP, edge_power_graph):
    for one_child in one_entity_children:
        one_child_name = one_entity_name + "." + one_child["Name"]
        if one_child_name not in node_name_to_id_MP:
            continue
        one_child_id = node_name_to_id_MP[one_child_name]
        if one_child_id in edge_power_graph[one_entity_id]["edgeList"]:
            edge_power_graph[one_entity_id]["edgeList"][one_child_id]["totalPower"] += CHILDREN_POWER
            edge_power_graph[one_entity_id]["edgeList"][one_child_id]["powerList"].append(CHILDREN_POWER)
            edge_power_graph[one_entity_id]["edgeList"][one_child_id]["relationList"].append("CHILDREN")
        else:
            one_child_edge = {}
            one_child_edge["name"] = one_child_name
            one_child_edge["totalPower"] = CHILDREN_POWER
            one_child_edge["powerList"] = [CHILDREN_POWER]
            one_child_edge["relationList"] = ["CHILDREN"]
            edge_power_graph[one_entity_id]["edgeList"][one_child_id] = one_child_edge

        if one_entity_id in edge_power_graph[one_child_id]["edgeList"]:
            edge_power_graph[one_child_id]["edgeList"][one_entity_id]["totalPower"] += CHILDREN_POWER
            edge_power_graph[one_child_id]["edgeList"][one_entity_id]["powerList"].append(CHILDREN_POWER)
            edge_power_graph[one_child_id]["edgeList"][one_entity_id]["relationList"].append("FATHER")
        else:
            one_father_edge = {}
            one_father_edge["name"] = one_entity_name
            one_father_edge["totalPower"] = CHILDREN_POWER
            one_father_edge["powerList"] = [CHILDREN_POWER]
            one_father_edge["relationList"] = ["FATHER"]
            edge_power_graph[one_child_id]["edgeList"][one_entity_id] = one_father_edge
    
# 添加Call边权信息
# 考虑到在添加方法间的Call边权信息，
#     1. 由于二者类之几乎都存在import关系，因此不用将当前类节点指向目标方法  
#     2. 由于类之间方法都存在类中，并且所有子方法已经链接了类，因此类之间的方法调用将被过滤
def add_call_edge(one_entity_children, one_entity_name, node_name_to_id_MP, edge_power_graph):
    for one_child in one_entity_children:
        one_child_name = one_entity_name + "." + one_child["Name"]
        if one_child_name not in node_name_to_id_MP:
            continue
        one_child_id = node_name_to_id_MP[one_child_name]
        one_children_call = one_child["Call"]
        for one_call in one_children_call:
            if one_call["file"] == one_entity_name: # 类中方法之间的互相调用关系不保留
                continue
            one_call_name = one_call["file"] + "." + one_call["name"]
            if one_call_name not in node_name_to_id_MP:
                continue
            one_call_id = node_name_to_id_MP[one_call_name]
            if one_call_id in edge_power_graph[one_child_id]["edgeList"]:
                edge_power_graph[one_child_id]["edgeList"][one_call_id]["totalPower"] += CALL_POWER
                edge_power_graph[one_child_id]["edgeList"][one_call_id]["powerList"].append(CALL_POWER)
                edge_power_graph[one_child_id]["edgeList"][one_call_id]["relationList"].append("CALL")
            else:
                one_call_edge = {}
                one_call_edge["name"] = one_call_name
                one_call_edge["totalPower"] = CALL_POWER
                one_call_edge["powerList"] = [CALL_POWER]
                one_call_edge["relationList"] = ["CALL"]
                edge_power_graph[one_child_id]["edgeList"][one_call_id] = one_call_edge

# 获取ast_graph图中的边权信息
def add_ast_graph_information_edge(ast_graph_information, node_name_to_id_MP, edge_power_graph):
    for one_entity in ast_graph_information:
        one_entity_name = one_entity["Name"]
        if one_entity_name not in node_name_to_id_MP:
            continue

        one_entity_id = node_name_to_id_MP[one_entity_name]

        one_entity_dependent = one_entity["Dependent"]
        one_entity_extend = one_entity["Extends"]
        one_entity_children = one_entity["Children"]

        add_dependent_edge(one_entity_dependent, one_entity_id, node_name_to_id_MP, edge_power_graph)

        add_extend_edge(one_entity_extend, one_entity_id, node_name_to_id_MP, edge_power_graph)

        add_children_edge(one_entity_children, one_entity_id, one_entity_name, node_name_to_id_MP, edge_power_graph)

        add_call_edge(one_entity_children, one_entity_name, node_name_to_id_MP, edge_power_graph)

# 读取文件夹下的所有文件
def list_files_recursively(folder_path):
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)

    all_files = sorted(all_files)
    return all_files

# 获取某个路径的文件名（包含后缀）
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
# 过滤不符合要求的文件，通过判断路径中是否包含某些字符串来判断
def check_node_modules(file_path):
    # 拆分路径为各个部分
    path_parts = file_path.split(os.sep)
    # 检查路径部分中是否包含 "node_modules"
    for one_node in FILTER_NODE_MODULE:
        if one_node in path_parts:
            return 1
    return 0

# 创建每个文件名到文件路径的映射
def get_filename_mapping_fileroot_dir(all_files_root):
    name_mapping_root = {}
    for this_file_root in all_files_root:
        is_contain_node_module = check_node_modules(this_file_root)
        if is_contain_node_module == 1:
            continue
        this_file_root_name = get_file_name(this_file_root)
        name_mapping_root[this_file_root_name] = this_file_root
    return name_mapping_root

# 获取某个路径的文件名后缀
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

# 获取方法到类名的映射
def get_method_to_class(ast_graph_information):
    method_to_class_dir = {}
    method_call = {}
    class_contain_entity = {}
    class_code = {}
    method_code = {}
    for one_class_information in ast_graph_information:
        one_class_name = one_class_information["Name"]
        one_class_children = one_class_information["Children"]
        child_temp = []
        for one_child in one_class_children:
            child_temp.append(one_child["Name"])
            one_child_name = one_class_name + "." + one_child["Name"]
            method_to_class_dir[one_child_name] = one_class_name
            one_child_call = one_child["Call"]
            call_temp = []
            for one_call in one_child_call:
                one_call_name = one_call["file"] + "." + one_call["name"]
                call_temp.append(one_call_name)
            method_call[one_child_name] = call_temp
            method_code[one_child_name] = one_child["Code"]
        class_contain_entity[one_class_name] = child_temp
        class_code[one_class_name] = one_class_information["FileContent"]
    return method_to_class_dir, method_call, class_contain_entity, class_code, method_code


# 判断是否符合后缀类型要求
def judge_whether_meet_suffix_requirement(file_name_suffix):
    if file_name_suffix in SUITABLE_EXTENSION:
        return True
    else:
        return False
    
# 从一个文件列表all_files中筛选出特定类型的文件，并将符合条件的文件名添加到列表中
def get_meet_required_file_names(all_files_root):
    all_file_names_with_extension = []
    for file_name in all_files_root:
        is_contain_node_module = check_node_modules(file_name)
        if is_contain_node_module == 1:
            continue
        file_name_extension = get_file_extension(file_name)
        if (judge_whether_meet_suffix_requirement(file_name_extension)):
            file_name_with_extension = get_file_name(file_name)
            all_file_names_with_extension.append(file_name_with_extension)
    return all_file_names_with_extension

# 读取all_bundle中有用的信息，包括符合要求的节点信息GraphMessage、包含的page页page_list
def read_useable_info_from_all_bundle(data, FileName2RootDIR):
    GraphDir = {}
    page_list = []
    Bundle_name = data.keys()
    for type_index in data[Bundle_name]:
        if type_index == "page":  # 获取所有的page，并且进行存储
            for page_item_name in data[Bundle_name][type_index]:
                page_item = data[Bundle_name][type_index][page_item_name]
                page_list.append(page_item["base"])  # 将获取的page存储到page_list中
        if type_index == "style":  # 过滤掉属于style类型的文件
            continue

        # 下面的代码用来保留五种类型文件之间的调用信息，信息将被存储到GraphDir中
        for file_index in data[Bundle_name][type_index]:
            message_temp = {}
            dependent_list = []
            message_temp["Type"] = type_index
            message_temp["Name"] = file_index

            file_extension_name = get_file_extension(file_index)

            if file_extension_name == "":
                print("need to delete: ",data[Bundle_name][type_index][file_index]["dir"] + "/" + file_index)

            if (not judge_whether_meet_suffix_requirement(file_extension_name)):
                continue

            message_temp["Root"] = (
                data[Bundle_name][type_index][file_index]["dir"] + "/" + file_index
            )
            for dependent_index in range(
                len(data[Bundle_name][type_index][file_index]["dependent"])
            ):
                target_base_name = data[Bundle_name][type_index][file_index][
                    "dependent"
                ][dependent_index]["base"]
                target_base_name_extension = get_file_extension(target_base_name)
                if (target_base_name_extension != "" and (not judge_whether_meet_suffix_requirement(file_extension_name))):
                    continue
                if target_base_name_extension == "": #处理一些没有后缀但符合要求的文件
                    for extension_one in SUITABLE_EXTENSION:
                        the_file_name_temp = target_base_name + extension_one
                        if the_file_name_temp in FileName2RootDIR:
                            target_base_name = the_file_name_temp
                # print(data[Bundle_name][type_index][file_index]["dependent"][dependent_index]['base'],data[Bundle_name][type_index][file_index]["dependent"][dependent_index]['bundleName'])
                dependent_list.append(target_base_name)
            message_temp["Dependent"] = dependent_list

            GraphDir[file_index] = message_temp
    
    return GraphDir, page_list

# 该函数通过层级遍历的方法完成对目标page:page_item相关节点的标记
def bfs_find_this_page_relate_node(node_name, nodes, node_name_to_id_MP, edge_power_graph):
    visited_nodes = []
    output_message = []
    q = queue.Queue()
    q.put(node_name)
    flag = 1
    while flag == 1:
        q2 = queue.Queue()
        while not q.empty():
            temp = q.get()
            visited_nodes.append(temp)
            if temp not in nodes or temp not in node_name_to_id_MP:
                continue
            dependencies = nodes[temp].get("Dependent", [])
            for dependency in dependencies:
                if dependency not in nodes or dependency not in node_name_to_id_MP:
                    continue
                beg_id_temp = node_name_to_id_MP[temp]
                end_id_temp = node_name_to_id_MP[dependency]
                dotInformation = '"' + temp + '"' + " -> " + '"' + dependency + '"\n'
                if dotInformation not in output_message:
                    output_message.append(dotInformation)
                    if end_id_temp in edge_power_graph[beg_id_temp]["edgeList"]:
                        edge_power_graph[beg_id_temp]["edgeList"][end_id_temp]["totalPower"] += PAGELIST_POWER
                        edge_power_graph[beg_id_temp]["edgeList"][end_id_temp]["powerList"].append(PAGELIST_POWER)
                        edge_power_graph[beg_id_temp]["edgeList"][end_id_temp]["relationList"].append("PAGELIST " + node_name)
                    else:
                        one_page_edge = {}
                        one_page_edge["name"] = dependency
                        one_page_edge["totalPower"] = PAGELIST_POWER
                        one_page_edge["powerList"] = [PAGELIST_POWER]
                        one_page_edge["relationList"] = ["PAGELIST " + node_name]
                        edge_power_graph[beg_id_temp]["edgeList"][end_id_temp] = one_page_edge
                    q2.put(dependency)
        while not q2.empty():
            temp = q2.get()
            q.put(temp)
        if q.empty():
            break

# 获取pagelist图中的边权信息
def add_pagelist_information_edge(file_fold_path, all_bundle_path, node_name_to_id_MP, edge_power_graph):
    # 读取文件夹路径下的所有文件
    all_files = list_files_recursively(file_fold_path)

    #创建每个文件名到文件路径的映射
    FileName2RootDIR = get_filename_mapping_fileroot_dir(all_files)

    # 获取所有符合要求的文件名
    file_names_with_extension = get_meet_required_file_names(all_files)

    # 读取all_bundle.json文件
    data = read_json_file(all_bundle_path)

    # 读取all_bundle中有用的信息，包括符合要求的节点信息GraphMessage、包含的page页page_list
    GraphMessage, page_list = read_useable_info_from_all_bundle(data, FileName2RootDIR)

    for page_item in page_list:
        bfs_find_this_page_relate_node(page_item, GraphMessage, node_name_to_id_MP, edge_power_graph)

# 添加leidan中的node边权信息
def add_each_leidan_node(this_leidan_node_information, this_leidan_level, this_leidan_power, node_name_to_id_MP, edge_power_graph):
    node_id_to_name_MP = {v: k for k, v in node_name_to_id_MP.items()}
    combinations = list(itertools.combinations(this_leidan_node_information, 2))
    for combination in combinations:
        entity_one_id = combination[0]
        entity_two_id = combination[1]
        if entity_one_id not in node_id_to_name_MP or entity_two_id not in node_id_to_name_MP:
            continue
        entity_name_one = node_id_to_name_MP[entity_one_id]
        entity_name_two = node_id_to_name_MP[entity_two_id]

        if entity_one_id in edge_power_graph[entity_two_id]["edgeList"]:
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["totalPower"] += this_leidan_power
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["powerList"].append(this_leidan_power)
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["relationList"].append("LEIDAN " + str(this_leidan_level))
        else:
            one_folder_edge = {}
            one_folder_edge["name"] = entity_name_one
            one_folder_edge["totalPower"] = this_leidan_power
            one_folder_edge["powerList"] = [this_leidan_power]
            one_folder_edge["relationList"] = ["LEIDAN " + str(this_leidan_level)]
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id] = one_folder_edge

        if entity_two_id in edge_power_graph[entity_one_id]["edgeList"]:
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["totalPower"] += this_leidan_power
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["powerList"].append(this_leidan_power)
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["relationList"].append("LEIDAN " + str(this_leidan_level))
        else:
            two_folder_edge = {}
            two_folder_edge["name"] = entity_name_two
            two_folder_edge["totalPower"] = this_leidan_power
            two_folder_edge["powerList"] = [this_leidan_power]
            two_folder_edge["relationList"] = ["LEIDAN " + str(this_leidan_level)]
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id] = two_folder_edge

# 过滤fox开头的实体
def filter_fox_entity(leidan_message_information, all_node_name_to_id_MP):
    all_node_id_to_name_MP = {v: k for k, v in all_node_name_to_id_MP.items()}
    for community_id in leidan_message_information:
        this_leidan_message_information = leidan_message_information[community_id]
        this_leidan_node_information = this_leidan_message_information["nodes"]
        this_leidan_node_information = set(this_leidan_node_information)
        new_node_list = []
        for entity_id in this_leidan_node_information:
            if entity_id not in all_node_id_to_name_MP:
                continue
            entity_name = all_node_id_to_name_MP[entity_id]
            if judge_fox_front_entity(entity_name):
                continue
            else:
                new_node_list.append(entity_id)
        leidan_message_information[community_id]["nodes"] = new_node_list

    return leidan_message_information



# 添加leidan图中的边权信息
def add_leidan_information_edge(leidan_message_information, node_name_to_id_MP, edge_power_graph):

    for community_id in leidan_message_information:
        this_leidan_message_information = leidan_message_information[community_id]
        this_leidan_level = this_leidan_message_information["level"]
        
        # 如果leidan的层数大于len(LEIDAN_POWER_LIST)，则取最后一个
        if this_leidan_level >= len(LEIDAN_POWER_LIST):
            this_leidan_level = LEIDAN_POWER_LIST[len(LEIDAN_POWER_LIST) - 1]
        
        this_leidan_power = LEIDAN_POWER_LIST[this_leidan_level]

        # 下面的处理方法是加leidan的nodes边权
        this_leidan_node_information = this_leidan_message_information["nodes"]
        this_leidan_node_information = set(this_leidan_node_information)
        add_each_leidan_node(this_leidan_node_information, this_leidan_level, this_leidan_power, node_name_to_id_MP, edge_power_graph)

# 按大模型的评分来给节点添加边权信息
def add_edge_power_by_llm(source_name, target_name, target_score, node_name_to_id_MP, edge_power_graph):
    if source_name not in node_name_to_id_MP or target_name not in node_name_to_id_MP:
        return
    source_id = node_name_to_id_MP[source_name]
    target_id = node_name_to_id_MP[target_name]
    if target_id in edge_power_graph[source_id]["edgeList"]:
        edge_power_graph[source_id]["edgeList"][target_id]["totalPower"] += float(target_score) * 0.5
        edge_power_graph[source_id]["edgeList"][target_id]["powerList"].append(float(target_score) * 0.5)
        edge_power_graph[source_id]["edgeList"][target_id]["relationList"].append("EDGE_POWER_BY_LLM")
    else:
        one_folder_edge = {}
        one_folder_edge["name"] = target_name
        one_folder_edge["totalPower"] = float(target_score) * 0.5
        one_folder_edge["powerList"] = [float(target_score) * 0.5]
        one_folder_edge["relationList"] = ["EDGE_POWER_BY_LLM"]
        edge_power_graph[source_id]["edgeList"][target_id] = one_folder_edge
    

# 判断str类型的字符是否能转成浮点类型
def can_convert_to_float(string_value):
    try:
        float(string_value)
        return True  # 如果成功转换，则返回 True
    except ValueError:
        return False  # 如果抛出 ValueError，则返回 False

# 添加大模型的边权评分信息
def add_edge_power_information_by_llm(edge_power_information_by_llm, node_name_to_id_MP, edge_power_graph):
    for source_name in edge_power_information_by_llm:
        all_target_edge_information = edge_power_information_by_llm[source_name]
        for one_target_edge_information in all_target_edge_information:

            target_name = one_target_edge_information["Name"]
            target_score = one_target_edge_information["RelatedScore"]
            target_score_reason = one_target_edge_information["ScoreReason"]
            if not can_convert_to_float(target_score):
                continue
            add_edge_power_by_llm(source_name, target_name, target_score, node_name_to_id_MP, edge_power_graph)
def list_files_in_third_level_dirs(root_path, target_step):
    def list_files_recursively(directory):
        """Recursively list non-directory files a given directory."""
        all_files = []
        for dirpath, dirnames, filenames in os.walk(directory):
            all_files.extend(os.path.join(dirpath, fname) for fname in filenames)
        return all_files

    result = {}
    
    # Walk through the directory tree
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Calculate the depth of the current directory
        depth = dirpath[len(root_path):].count(os.sep)
        
        # If the depth is 2, it means we are in a third-level directory (root is depth 0)
        if depth == target_step:
            # Collect non-directory files in the current third-level directory
            current_dir_files = [fname for fname in filenames]
            
            # Recursively collect files from all subdirectories within this third-level directory
            subdir_files = list_files_recursively(dirpath)
            
            if current_dir_files or subdir_files:
                result[dirpath] = current_dir_files + subdir_files
    
    return result

# 给每个符合要求的文件夹添加边的关系
def add_each_file_edge(meet_requirement_file_name, now_step_level_power, now_step, node_name_to_id_MP, edge_power_graph):
    combinations = list(itertools.combinations(meet_requirement_file_name, 2))
    for combination in combinations:
        entity_name_one = combination[0]
        entity_name_two = combination[1]
        if entity_name_one not in node_name_to_id_MP or entity_name_two not in node_name_to_id_MP:
            continue
        entity_one_id = node_name_to_id_MP[entity_name_one]
        entity_two_id = node_name_to_id_MP[entity_name_two]

        if entity_one_id in edge_power_graph[entity_two_id]["edgeList"]:
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["totalPower"] += now_step_level_power
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["powerList"].append(now_step_level_power)
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["relationList"].append("FOLDER " + str(now_step))
        else:
            one_folder_edge = {}
            one_folder_edge["name"] = entity_name_one
            one_folder_edge["totalPower"] = now_step_level_power
            one_folder_edge["powerList"] = [now_step_level_power]
            one_folder_edge["relationList"] = ["FOLDER " + str(now_step)]
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id] = one_folder_edge

        if entity_two_id in edge_power_graph[entity_one_id]["edgeList"]:
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["totalPower"] += now_step_level_power
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["powerList"].append(now_step_level_power)
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["relationList"].append("FOLDER " + str(now_step))
        else:
            two_folder_edge = {}
            two_folder_edge["name"] = entity_name_two
            two_folder_edge["totalPower"] = now_step_level_power
            two_folder_edge["powerList"] = [now_step_level_power]
            two_folder_edge["relationList"] = ["FOLDER " + str(now_step)]
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id] = two_folder_edge


def group_files_by_folder_level(file_paths, level):
    folder_dict = defaultdict(list)

    for path in file_paths:
        parts = path.split(os.path.sep)
        # Ensure the path has enough parts to reach the desired level
        if len(parts) >= level + 1:
            folder_key = os.path.join(*parts[:level + 1])
            folder_dict[folder_key].append(path)
    
    return folder_dict   
# 添加fold图中的边权信息
def add_fold_information_edge_with_file_level(ast_graph_information, node_name_to_id_MP, edge_power_graph):
    all_step = [2, 3, 4]
    begin_index = 0
    begin_head = 'A'
    file_fold_MP = {}
    for now_step in all_step:
        root_path_list = []
        for node in ast_graph_information:
            root_path_list.append(node["Root"])
        now_step_level_files = group_files_by_folder_level(root_path_list, now_step)
        now_step_level_power = FOLDER_POWER_LIST[now_step]
        this_head = chr(ord(begin_head) - 2 + now_step)
        for dirpath, files in now_step_level_files.items():
            begin_index = begin_index + 1
            meet_requirement_file_name = []
            for file in files:
                if check_node_modules(file) == 1:
                    continue
                fileroot_suffix = get_file_extension(file)
                if not judge_whether_meet_suffix_requirement(fileroot_suffix):
                    continue
                if get_file_name(file) in node_name_to_id_MP:
                    this_file_id = node_name_to_id_MP[get_file_name(file)]
                    file_fold_MP[this_file_id] = str(this_head) + str(begin_index)
                meet_requirement_file_name.append(get_file_name(file))
            meet_requirement_file_name = set(meet_requirement_file_name)
            if len(meet_requirement_file_name) <= 1 or len(meet_requirement_file_name) > MAX_FOLD_FILE_NUM:
                continue 

            add_each_file_edge(meet_requirement_file_name, now_step_level_power, now_step, node_name_to_id_MP, edge_power_graph)
    return file_fold_MP
# 给每个符合要求的commit添加边的关系
def add_each_commit_edge(this_commit_message_files_name, node_name_to_id_MP, edge_power_graph):
    combinations = list(itertools.combinations(this_commit_message_files_name, 2))
    for combination in combinations:
        entity_name_one = combination[0]
        entity_name_two = combination[1]
        if entity_name_one not in node_name_to_id_MP or entity_name_two not in node_name_to_id_MP:
            continue
        entity_one_id = node_name_to_id_MP[entity_name_one]
        entity_two_id = node_name_to_id_MP[entity_name_two]

        if entity_one_id in edge_power_graph[entity_two_id]["edgeList"]:
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["totalPower"] += COMMIT_POWER
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["powerList"].append(COMMIT_POWER)
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id]["relationList"].append("COMMIT")
        else:
            one_commit_edge = {}
            one_commit_edge["name"] = entity_name_one
            one_commit_edge["totalPower"] = COMMIT_POWER
            one_commit_edge["powerList"] = [COMMIT_POWER]
            one_commit_edge["relationList"] = ["COMMIT"]
            edge_power_graph[entity_two_id]["edgeList"][entity_one_id] = one_commit_edge

        if entity_two_id in edge_power_graph[entity_one_id]["edgeList"]:
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["totalPower"] += COMMIT_POWER
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["powerList"].append(COMMIT_POWER)
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["relationList"].append("COMMIT")
        else:
            two_commit_edge = {}
            two_commit_edge["name"] = entity_name_two
            two_commit_edge["totalPower"] = COMMIT_POWER
            two_commit_edge["powerList"] = [COMMIT_POWER]
            two_commit_edge["relationList"] = ["COMMIT"]
            edge_power_graph[entity_one_id]["edgeList"][entity_two_id] = two_commit_edge

# 添加commit图中的边权信息
def add_commit_information_edge(commit_message_information, node_name_to_id_MP, edge_power_graph):
    commit_message_information_nodes = commit_message_information["nodes"]
    for one_commit_message_information in commit_message_information_nodes:
        this_commit_message_files = one_commit_message_information["files"]
        this_commit_message_files_name = []
        for this_commit_message in this_commit_message_files:
            this_commit_message_files_name.append(this_commit_message["name"])
        this_commit_message_files_name = set(this_commit_message_files_name)
        if len(this_commit_message_files_name) <= 1 or len(this_commit_message_files_name) > MAX_COMMIT_FILE_NUM:
            continue 
        add_each_commit_edge(this_commit_message_files_name, node_name_to_id_MP, edge_power_graph)

# 根据阈值A进行初步过滤
def split_directed_graph_based_on_threshold(G, A):
    """
    根据给定的阈值分割有向图，保留边的权重大于阈值的边，并生成多个子图
    :param G: 输入的有权重的有向图 (nx.DiGraph)
    :param A: 边权重的阈值
    :return: 包含每个子图中节点的列表
    """
    # 过滤边，保留权重大于A的边
    filtered_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d['weight'] > A]
    
    # 创建一个新的无向图，用于查找连通分量
    filtered_undirected_graph = nx.Graph()
    filtered_undirected_graph.add_edges_from((u, v) for u, v, d in filtered_edges)
    
    # 找出新图中的连通分量
    subgraphs = [list(c) for c in nx.connected_components(filtered_undirected_graph)]
    
    return subgraphs

# 对社区进行衰退，补充社区信息
def community_add_degradation_edge(subgraphs, G, id):
    communityDir = {}
    community_id = 1
    targetPower = FILTER_THRESHOLD[id] * (1 - DEGRADATION_SCOPE)
    for i, sg in enumerate(subgraphs):
        communityList = []
        q = queue.Queue()
        now_step = 0
        for sg_id in sg:
            communityList.append(sg_id)
            q.put((sg_id, now_step))
        while not q.empty():
            now_node_id, now_step = q.get()
            now_step = now_step + 1
            for target_node_id in G.neighbors(now_node_id):
                if target_node_id in communityList:
                    continue
                if G[now_node_id][target_node_id]["weight"] * pow(DEGRADATION_WEIGHT, now_step) > targetPower:
                    q.put((target_node_id, now_step))
                    communityList.append(target_node_id)
        communityDir[community_id] = sorted(set(communityList))
        community_id = community_id + 1
    return communityDir
        
@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS), wait=wait_fixed(WAIT_SECONDS)
)
async def stream_output(chain, prompt_input):
    res = ""
    async for chunk in chain.astream({"input_text": prompt_input["input"]}):
        res += chunk
    return res

async def llm_community_report_chain(prompt_input):
    prompt = COMMUNITY_REPORT_PROMPT
    print(f"Generate reports for Community {prompt_input['id']} ......")
    parser = StrOutputParser()
    prompt_template = ChatPromptTemplate.from_messages([("user", prompt)])
    chain = prompt_template | report_model | parser
    result = await stream_output(chain, prompt_input)
    print(f"Community {prompt_input['id']} Done!")
    return result

async def worker(semaphore, prompt_input, community_reports):
    async with semaphore:
        result = await llm_community_report_chain(prompt_input)
        community_reports[prompt_input["id"]]["reports"] = result

def num_tokens_from_string(string):
    """
    使用 tiktoken 预估 tokens 数
    """
    encoding = tiktoken.encoding_for_model("gpt-4o")
    num_tokens = len(encoding.encode(string))
    return num_tokens

async def rate_limiter(semaphore, prompt, community_reports, rate_limit_info):
    async with semaphore:
        prompt_tokens = num_tokens_from_string(str(prompt))
        while True:
            current_time = time.time()
            elapsed_time = current_time - rate_limit_info["start_time"]
            if elapsed_time >= 60:
                # 每分钟初始状态重置统计
                rate_limit_info["start_time"] = current_time
                rate_limit_info["consumed_tokens"] = 0
            
            if rate_limit_info["consumed_tokens"] + prompt_tokens <= rate_limit_info["max_tokens_per_minute"]:
                # 可以执行任务，更新统计
                rate_limit_info["consumed_tokens"] += prompt_tokens
                break
            else:
                # 等待一小段时间再检查
                await asyncio.sleep(1)
        result = await llm_community_report_chain(prompt)
        community_reports[prompt["id"]]["reports"] = result


# 使用大模型给每个community打分，并保存
# 使用all_community_message中统计出的社区信息
# 使用the_useful_ast_information中的report信息、ast调用信息、id到name的映射
async def assess_community_relevance_score(id_index, all_community_message, the_useful_ast_information, file_fold_MP, node_name_to_id_MP, edge_power_graph, concurrent_num):
    node_id_to_name_MP = {v: k for k, v in node_name_to_id_MP.items()}
    node_id_to_report = {}
    community_reports = {}
    value_dir = {}
    for node in the_useful_ast_information:
        node_name = the_useful_ast_information.nodes[node]["name"]
        node_report = the_useful_ast_information.nodes[node]["report"]
        if node_name in node_name_to_id_MP:
            node_id_to_report[node_name_to_id_MP[node_name]] = node_report
    print("start assessing community relevance...")
    prompt_inputs = []
    for community_id in all_community_message:
        community_reports[community_id] = {}
        community_reports[community_id]["level"] = id_index
        print(community_reports[community_id]["level"])
        community_reports_id_list = []
        this_community_message_id = all_community_message[community_id]
        for this_node_id in this_community_message_id:
            # community_reports_id_list.append(node_id_to_name_MP[this_node_id]) # nodes中加实体名
            community_reports_id_list.append(this_node_id) # nodes中加实体id
            if file_fold_MP[this_node_id] not in value_dir:
                value_dir[file_fold_MP[this_node_id]] = []
            value_dir[file_fold_MP[this_node_id]].append(this_node_id)
        community_reports[community_id]["nodes"] = community_reports_id_list
        community_reports[community_id]["edges"] = []
        prompt_input = ""
        prompt_input += "List of Entities: \n \nentity \n"
        for this_node_id in this_community_message_id:
            prompt_input += node_id_to_name_MP[this_node_id] + "\n"
        
        combinations = list(itertools.combinations(this_community_message_id, 2))
        
        prompt_input += "\nEntity Relationships: \n \nsource,target,description \n"
        for combination in combinations:
            entity_one_id = combination[0]
            entity_two_id = combination[1]
            List_Temp = [entity_one_id, entity_two_id]
            community_reports[community_id]["edges"].append(List_Temp)
            if not the_useful_ast_information.has_edge(entity_one_id, entity_two_id):
                continue
            
            if the_useful_ast_information[entity_one_id][entity_two_id]["type"] == EdgeType.DEPENDENT:
                edge_description = (
                    f"{node_id_to_name_MP[entity_one_id]} depends on {node_id_to_name_MP[entity_two_id]}\n"
                )
                prompt_input += edge_description
                prompt_input += "\n"
            elif the_useful_ast_information[entity_one_id][entity_two_id]["type"] == EdgeType.EXTENDS:
                edge_description = (
                    f"{node_id_to_name_MP[entity_one_id]} extends from {node_id_to_name_MP[entity_two_id]}\n"
                )
                prompt_input += edge_description
                prompt_input += "\n"
            else:
                1

        prompt_input += "\nFolder Descriptions: \n \nlist of entity,description \n"
        for value_id in value_dir:
            if len(value_dir[value_id]) <= 1:
                continue
            edge_description = "["
            value_flag = 0
            for message in value_dir[value_id]:
                if value_flag == 0:
                    value_flag = 1
                    edge_description += node_id_to_name_MP[message]
                else:
                    edge_description += "," + node_id_to_name_MP[message]
            edge_description += ", these files are in the same folder"


        prompt_input += "\nCorrelation Scores: \n \nsource,target,description \n"
        max_num_Temp  = 1000
        for combination in combinations:
            entity_one_id = combination[0]
            entity_two_id = combination[1]
            List_Temp = [entity_one_id, entity_two_id]
            community_reports[community_id]["edges"].append(List_Temp)
            max_num_Temp = max_num_Temp - 1
            if max_num_Temp <= 0:
                break
            if entity_one_id in edge_power_graph and entity_two_id in edge_power_graph[entity_one_id]["edgeList"]:
                edge_description =node_id_to_name_MP[entity_one_id]+","+node_id_to_name_MP[entity_two_id]+ ",the correlation between " + node_id_to_name_MP[entity_one_id] + " and " +node_id_to_name_MP[entity_two_id] + " is " + str(edge_power_graph[entity_one_id]["edgeList"][entity_two_id]["totalPower"])
                prompt_input += edge_description
                prompt_input += "\n"

        prompt_input += "\nEntity Reports: \n \nentity,description\n"
        for id in this_community_message_id:
            if id not in node_id_to_name_MP or id not in node_id_to_report:
                continue
            edge_description = node_id_to_name_MP[id] + "," + node_id_to_report[id]
            prompt_input += edge_description
            prompt_input += "\n"

        prompt_inputs.append({"id": community_id, "input": prompt_input})

    semaphore = asyncio.Semaphore(concurrent_num)

    # 速率限制信息
    rate_limit_info = {
        "max_tokens_per_minute": 200000,  # 每分钟最大 token 数量
        "start_time": time.time(),  # 开始时间
        "consumed_tokens": 0  # 初始化已消耗的 token 数量
    }

    tasks = [
        asyncio.create_task(rate_limiter(semaphore, prompt, community_reports,rate_limit_info))
        for prompt in prompt_inputs
    ]
    await asyncio.gather(*tasks)
    
    return community_reports

# 根据边权图提取社区信息
def exact_community_from_edge_power_graph(edge_power_graph, node_name_to_id_MP):
    node_id_to_name_MP = {v: k for k, v in node_name_to_id_MP.items()}
    print("start generating community...")
    G = nx.Graph()
    for this_entity_id in edge_power_graph:
        G.add_node(this_entity_id)
    
    for this_entity_id in edge_power_graph:
        this_entity_id_edgeList = edge_power_graph[this_entity_id]["edgeList"]
        for target_entity_id in this_entity_id_edgeList:
            G.add_edge(this_entity_id, target_entity_id)
            G[this_entity_id][target_entity_id]["weight"] = this_entity_id_edgeList[target_entity_id]["totalPower"]

    New_community_message = {}
    for id in range(len(FILTER_THRESHOLD)):
        subgraphs = split_directed_graph_based_on_threshold(G, FILTER_THRESHOLD[id])

        # 这个函数是一个开关，是否给社区加衰退点
        all_community_message = community_add_degradation_edge(subgraphs, G, id)
        New_community_message[id] = all_community_message


    # total_num = 0
    # begin_index = 1
    # this_path = "/path/to/data.json"
    # this_path += str(DEGRADATION_SCOPE) + "_" + str(DEGRADATION_WEIGHT) + "/community_info_thresholds_"
    # this_path = this_path + str(FILTER_THRESHOLD) + "_" + str(MAX_FOLD_FILE_NUM) + ".txt"
    # with open(this_path, 'w') as f:
    #     for id in New_community_message:
    #         all_community_message = New_community_message[id]
    #         for key in all_community_message:
    #             if len(all_community_message[key]) == 1:
    #                 continue
    #             total_num = total_num + len(all_community_message[key])
    #             f.write(f"Len of Subgraph {begin_index} nodes: {len(all_community_message[key])}")
    #             f.write("\n")
    #             for sg_id in all_community_message[key]:
    #                 f.write(node_id_to_name_MP[sg_id])
    #                 f.write("\n")
    #             f.write("=============================")
    #             f.write("\n")
    #             begin_index = begin_index + 1
    #     print(total_num)

    return New_community_message


# 给新生成的社区去重
def deduplication_community_information(all_community_message):
    new_map_dic = {}
    new_all_community_message = {}
    for id in all_community_message:
        new_all_community_message[id] = {}
        for index in all_community_message[id]:
            new_list_tuple = tuple(all_community_message[id][index])
            new_map_dic[new_list_tuple] = id

    for id in all_community_message:
        for index in all_community_message[id]:
            new_list_tuple = tuple(all_community_message[id][index])
            if id == new_map_dic[new_list_tuple] and len(all_community_message[id][index]) >= MIN_COMMUNITY_SIZE[id]:
                new_all_community_message[id][index] = all_community_message[id][index]
    
    return new_all_community_message
# 根据生成的结果更新community
def update_community_information(new_community_path, new_code_graph_path, all_new_community_report, code_graph_information):
    num_id = 0
    maxid_nodes_MP = {}
    leidan_message_information = {}
    for id in range(len(all_new_community_report)):
        new_community_report = all_new_community_report[id]
        for community_id in new_community_report:
            leidan_message_information[num_id] = new_community_report[community_id]
            maxid_nodes_MP[num_id] = new_community_report[community_id]["nodes"]
            num_id = num_id + 1

    for one_node in code_graph_information["nodes"]:
        one_node_id = one_node["id"]
        one_node_community_id = []
        for community_id in maxid_nodes_MP:
            if one_node_id in maxid_nodes_MP[community_id] and community_id not in one_node_community_id:
                one_node_community_id.append(community_id)
        one_node["community_id"] = one_node_community_id

    

    save_to_json(leidan_message_information, new_community_path)
    save_to_json(code_graph_information, new_code_graph_path)


    