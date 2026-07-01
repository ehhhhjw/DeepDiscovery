import os
import sys
import json
import tiktoken
import queue
from constants import (
    NODE_CONTENT_KEYS,
    EXTRACT_CONTENT_KEYS,
    MAX_RELATION_MESSAGE_NUM,
    SearchType,
    FindType,
    EdgeType,
    LOG_DIR_PATH,
)


# 写文本到日志
def write_text_to_log(output_str, path):
    # 先创建创建日志文件夹，防止报错
    LOG_DIR_PATH.mkdir(parents=True, exist_ok=True)
    with open(f"{LOG_DIR_PATH}/{path}", "w") as file:
        file.write(output_str)


def save_json_to_file(data, file_path, fields="", cls=None):
    # 获取文件夹路径
    folder_path = os.path.dirname(file_path)

    # 如果文件夹不存在，则创建它
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    _data = data
    if fields:
        _fields = fields.split(",")
        # 只保留 fields 中指定的字段
        _data = {field: data[field] for field in _fields if field in data}
    # 写入 JSON 数据到文件
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_data, f, indent=4, ensure_ascii=False, cls=cls)


def read_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file {file_path}: {e}")
        return None


def num_tokens_from_string(string):
    """
    使用 tiktoken 预估 tokens 数
    """
    encoding = tiktoken.encoding_for_model("gpt-4o")
    num_tokens = len(encoding.encode(string))
    return num_tokens


def truncate_to_tokens(string, max_tokens=8000):
    """
    截断字符串，确保其 token 数量不超过 max_tokens
    """
    encoding = tiktoken.encoding_for_model("text-embedding-3-large")
    tokens = encoding.encode(string)

    # 截取前 max_tokens 个 token
    truncated_tokens = tokens[:max_tokens]
    # 解码回字符串
    truncated_string = encoding.decode(truncated_tokens)

    return truncated_string


def get_graph_node_content_with_class_code(node, type=SearchType.CODE):
    res = ""
    for c in NODE_CONTENT_KEYS:
        if c == "code_comment" or c == "name" or c not in node:
            continue
        if not node[c]: # 如果这个字段中的信息为空，则不加
            continue
        # class 召回的时候，源代码也召回
        if c == "description" and not node["is_leaf"]:
            if "file_content" in node and len(node["file_content"]) > 0:
                res += "code" + ": " + node["file_content"] + "\n\n"
                continue
        res += c + ": " + node[c] + "\n"
    return res


def get_community_node_content(node, type=SearchType.CODE):
    res = ""
    for c in NODE_CONTENT_KEYS:
        if c == "code_comment" or c == "name" or c not in node:
            continue
        # class 不填充 description
        if (
            c == "description"
            and type == SearchType.CODE
            and "is_leaf" in node
            and node["is_leaf"] == False
        ):
            continue
        if c == "description":  # 如果是代码片段，名字改一下
            if not node[c]: # 如果这个字段中的信息为空，则不加
                continue
            if type == SearchType.CODE:
                continue
            else:
                res += "    Description" + ": " + node[c] + "\n"
        else:
            if not node[c]: # 如果这个字段中的信息为空，则不加
                continue
            if type == SearchType.CODE:
                res += c + ": " + node[c] + "\n"
            else:
                res += "    " + c + ": " + node[c] + "\n"
    return res

def get_graph_node_content(node, type=SearchType.CODE):
    res = ""
    for c in NODE_CONTENT_KEYS:
        if c == "code_comment" or c == "name" or c not in node:
            continue
        # class 不填充 description
        if (
            c == "description"
            and type == SearchType.CODE
            and "is_leaf" in node
            and node["is_leaf"] == False
        ):
            continue
        if c == "description":  # 如果是代码片段，名字改一下
            if not node[c]: # 如果这个字段中的信息为空，则不加
                continue
            if type == SearchType.CODE:
                res += "Code Snippet" + ": " + node[c] + "\n"
            else:
                res += "    Description" + ": " + node[c] + "\n"
        else:
            if not node[c]: # 如果这个字段中的信息为空，则不加
                continue
            if type == SearchType.CODE:
                res += c + ": " + node[c] + "\n"
            else:
                res += "    " + c + ": " + node[c] + "\n"
    return res



def get_graph_node_content_without_description(node, type=SearchType.CODE):
    res = ""
    for c in NODE_CONTENT_KEYS:
        if c == "code_comment" or c == "name" or c not in node:
            continue
        # class 不填充 description
        if (
            c == "description"
            and type == SearchType.CODE
            and "is_leaf" in node
            and node["is_leaf"] == False
        ):
            continue
        if c == "description":  # 如果是代码片段，名字改一下
            continue
            if not node[c]: # 如果这个字段中的信息为空，则不加
                continue
            if type == SearchType.CODE:
                res += "Code Snippet" + ": " + node[c] + "\n"
            else:
                res += "    Description" + ": " + node[c] + "\n"
        else:
            if not node[c]: # 如果这个字段中的信息为空，则不加
                continue
            if type == SearchType.CODE:
                res += c + ": " + node[c] + "\n"
            else:
                res += "    " + c + ": " + node[c] + "\n"
    return res

def get_graph_node_extract_content(node, type):
    res = ""
    for c in EXTRACT_CONTENT_KEYS:
        if c == "code_comment" or c == "name":
            continue
        # class 不填充 description
        if (
            c == "description"
            and type == SearchType.CODE
            and "is_leaf" in node
            and node["is_leaf"] == False
        ):
            continue
        if not node[c]: # 如果这个字段中的信息为空，则不加
            continue
        res += c + ": " + node[c] + "\n"
    return res


def get_qa_graph_node_content(node_metadata):
    question = node_metadata["chat_query"]
    chat_answer = node_metadata["chat_answer"]
    gmt_create = node_metadata["gmt_create"]
    res = f"Q&A TIME: {gmt_create}\nQUESTION: {question}\nANSWER: {chat_answer}"
    return res


# 查询节点
def query_nodes(G, attribute, value):
    return [
        (id, attr)
        for id, attr in G.nodes(data=True)
        if attr.get(attribute) == value
    ]


# 查询边
def query_edges(G, attribute, value):
    return [
        (u, v)
        for u, v, attr in G.edges(data=True)
        if attr.get(attribute) == value
    ]


def get_layer_nodes(target_graph, node_id, find_layer, node_type):
    addition_list = []
    addition_context = ""
    now_step = 1
    q1 = queue.Queue()
    q1.put(node_id)
    node_id_visited = set()
    addition_list.append(node_id)
    the_relation_num = 0
    # 如果是类的话，添加当前节点的extend；如果是方法的话，添加当前节点的所属类
    if node_type == FindType.CLASS:  # 如果是类的话，进行上下层搜索
        edge_list = list(target_graph.out_edges(node_id))
        for edge in edge_list:
            edge_type = target_graph.edges[edge]["type"]
            if edge_type == EdgeType.EXTENDS:
                source_node = target_graph.nodes[edge[0]]["name"]
                target_node = target_graph.nodes[edge[1]]["name"]
                edge_description = "extends from"
                if the_relation_num < MAX_RELATION_MESSAGE_NUM:
                    addition_context += (
                        f"{source_node} {edge_description} {target_node}\n"
                    )
                    the_relation_num = the_relation_num + 1
                if edge[0] != node_id:
                    addition_list.append(edge[0])
                if edge[1] != node_id:
                    addition_list.append(edge[1])
    elif node_type == FindType.METHOD:  # 如果是方法的话，进行下层搜索
        edge_list = list(target_graph.in_edges(node_id))
        for edge in edge_list:
            edge_type = target_graph.edges[edge]["type"]
            if edge_type == EdgeType.CHILD:
                source_node = target_graph.nodes[edge[0]]["name"]
                target_node = target_graph.nodes[edge[1]]["name"]
                edge_description = "has child"
                if the_relation_num < MAX_RELATION_MESSAGE_NUM:
                    addition_context += (
                        f"{source_node} {edge_description} {target_node}\n"
                    )
                    the_relation_num = the_relation_num + 1
                if edge[0] != node_id:
                    addition_list.append(edge[0])
                if edge[1] != node_id:
                    addition_list.append(edge[1])

    # 对于class，进行上下find_layer层的class关系搜索；对于method，进行下find_layer层的call关系搜索
    while now_step <= find_layer:
        q2 = queue.Queue()
        while not q1.empty():
            this_node_id = q1.get()
            if this_node_id not in node_id_visited:
                node_id_visited.add(this_node_id)
                if node_type == FindType.CLASS:  # 如果是类的话，进行上下层搜索
                    edge_list = list(
                        target_graph.in_edges(this_node_id)
                    ) + list(target_graph.out_edges(this_node_id))
                elif (
                    node_type == FindType.METHOD
                ):  # 如果是方法的话，进行下层搜索
                    edge_list = list(target_graph.out_edges(this_node_id))
                for edge in edge_list:
                    edge_type = target_graph.edges[edge]["type"]
                    if EdgeType.CHILD in edge_type:
                        continue
                    source_node = target_graph.nodes[edge[0]]["name"]
                    target_node = target_graph.nodes[edge[1]]["name"]

                    if node_type == FindType.CLASS:
                        if edge_type == EdgeType.DEPENDENT:
                            edge_description = "depends on"
                            if the_relation_num < MAX_RELATION_MESSAGE_NUM:
                                addition_context += f"{source_node} {edge_description} {target_node}\n"
                                the_relation_num = the_relation_num + 1
                            if edge[0] not in node_id_visited:
                                q2.put(edge[0])
                                addition_list.append(edge[0])
                            if edge[1] not in node_id_visited:
                                q2.put(edge[1])
                                addition_list.append(edge[1])
                    elif node_type == FindType.METHOD:
                        if edge_type == EdgeType.CALL:
                            edge_description = "calls"
                            if the_relation_num < MAX_RELATION_MESSAGE_NUM:
                                addition_context += f"{source_node} {edge_description} {target_node}\n"
                                the_relation_num = the_relation_num + 1
                            if edge[0] not in node_id_visited:
                                q2.put(edge[0])
                                addition_list.append(edge[0])
                            if edge[1] not in node_id_visited:
                                q2.put(edge[1])
                                addition_list.append(edge[1])
        while not q2.empty():
            q1.put(q2.get())
        now_step = now_step + 1

    return addition_list, addition_context


# 退出程序
def exit_app(message: str = ""):
    print(f"exit app. stage: {message}.")
    sys.exit(0)


def get_graph_doc_node_content_with_file(id, node):
    if not node or node.get("id") != id:
        "Node not found"

    # 获取 entity_type，并提供默认值
    entity_type = node.get("type", "method")
    # 处理 entity_description 使其在一行输出，通过转义符 \n
    entity_description = node.get("description", "").replace("\n", "\\n")
    try:
        if entity_type == "file" and node.get("name", "").endswith(".md"):
            # 当类型是 file 且 name 是文件名时，不进行解析，直接输出文件名
            entity_name = node.get("name", "")
            markdown_content = f"\n### Entity ID: {id}\n    Entity name: {entity_name}\n    Entity Type: {entity_type}\n    Entity Report: {node.get('report', '')}\n    Entity Comment: {node.get('comment', '')}\n    Entity Description: {entity_description}\n"

        else:
            # 当类型不是 file 或 name 不是文件名 时，继续解析 node['name']
            full_name = node.get("name", "")
            part1, part2, entity_name = full_name.split(".", 2)
            part2 = int(part2)  # 确保部分 2 是整数

            # 文件名称
            file_name = f"{part1}.md"

            # 生成指定格式的输出内容，并添加换行和缩进
            markdown_content = f"\n### Entity ID: {id}\n    Entity name: {entity_name}\n    Entity Type: {entity_type}\n    Entity Report: 文件{file_name}的第{part2}个Entity\n    Entity Comment: {node.get('comment', '')}\n    Entity Description: {entity_description}\n"

    except (ValueError, AttributeError):
        # 解析失败时，直接输出文件类型节点的相关信息
        entity_name = node.get("name", "")
        markdown_content = f"\n### Entity ID: {id}\n    Entity name: {entity_name}\n    Entity Type: {entity_type}\n    Entity Report: {node.get('report', '')}\n    Entity Comment: {node.get('comment', '')}\n    Entity Description: {entity_description}\n"

    return markdown_content


def get_graph_doc_node_content_for_rank(id, node, graph_nodes):
    if not node or node.get("id") != id:
        "Node not found"

    # 获取 entity_type，并提供默认值
    entity_type = node.get("type", "method")
    # 处理 entity_description 使其在一行输出，通过转义符 \n
    entity_description = node.get("description", "").replace("\n", "\\n")
    try:
        if entity_type == "file" and node.get("name", "").endswith(".md"):
            # 当类型是 file 且 name 是文件名时，不进行解析，直接输出文件名
            entity_name = node.get("name", "")
            markdown_content = f"\n### Entity ID: {id}\n    Entity name: {entity_name}\n    Entity Type: {entity_type}\n    Entity Report: {node.get('report', '')}\n    Entity Comment: {node.get('comment', '')}\n"

        else:
            # 当类型不是 file 或 name 不是文件名 时，继续解析 node['name']
            full_name = node.get("name", "")
            part1, part2, entity_name = full_name.split(".", 2)
            part2 = int(part2)  # 确保部分 2 是整数

            # 文件名称
            file_name = f"{part1}.md"

            #识别是否acorn组件
            is_acorn = False

            acorn_files = ['290-CLNetwork.md']
            if file_name in acorn_files:
                is_acorn = True
            else:
                for node_id in graph_nodes:
                    node_item = graph_nodes[node_id]
                    node_name = node_item["name"]
                    node_type = node_item["type"]
                    if node_type == "file" and node_name == file_name:
                        node_description = node_item["description"]
                        if node_description.startswith('acorn'):
                            is_acorn = True
                            break
            if is_acorn:
                markdown_content = f"\n### Entity ID: {id}\n    Entity name: {entity_name}\n    Entity Type: {entity_type}\n    Entity Report: Acorn组件{file_name}的第{part2}个Entity\n    Entity Comment: {node.get('comment', '')}\n"
            else:
                # 生成指定格式的输出内容，并添加换行和缩进
                markdown_content = f"\n### Entity ID: {id}\n    Entity name: {entity_name}\n    Entity Type: {entity_type}\n    Entity Report: 文件{file_name}的第{part2}个Entity\n    Entity Comment: {node.get('comment', '')}\n"

    except (ValueError, AttributeError):
        # 解析失败时，直接输出文件类型节点的相关信息
        entity_name = node.get("name", "")
        markdown_content = f"\n### Entity ID: {id}\n    Entity name: {entity_name}\n    Entity Type: {entity_type}\n    Entity Report: {node.get('report', '')}\n    Entity Comment: {node.get('comment', '')}\n"

    return markdown_content

def get_base_params(data):
    arg_list = [
        "is_use_code",
        "is_use_docs",
        "top_k",
        "open_rerank",
        "open_query_split",
        "open_chat"
    ]
    return dict(
        [(key, data.get(key)) for key in arg_list if data.get(key) != None]
    )
