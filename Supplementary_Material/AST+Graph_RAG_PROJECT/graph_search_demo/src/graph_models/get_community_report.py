import json
import time
import asyncio
import networkx as nx
from services.llm_community_report_chain import llm_community_report_chain
from utils.utils import num_tokens_from_string, get_graph_node_content, get_community_node_content
from constants import EdgeType

from utils.generate_new_community import (
    read_json_file,
    get_useful_information_of_code_graph,
    get_useful_information_of_ast_graph,
    construct_base_edge_power_graph,
    filter_fox_entity,
    add_edge_power_information_by_llm,
    add_leidan_information_edge,
    add_fold_information_edge_with_file_level,
    exact_community_from_edge_power_graph,
    deduplication_community_information,
    assess_community_relevance_score,
    update_community_information,
    save_to_json,
    desolve_leidan,
)

MAX_TOKEN = 100 * 1000


async def worker(semaphore, prompt_input, community_reports):
    async with semaphore:
        result = await llm_community_report_chain(prompt_input)
        # print("=============================",prompt_input["id"])
        community_reports[prompt_input["id"]]["reports"] = result

def get_description_message(edge_type, Edge_Information, source_node, target_node):
    edge_description = ""
    if edge_type == EdgeType.DEPENDENT:
        edge_description = f"{source_node} depends on {target_node}"
    elif edge_type == EdgeType.EXTENDS:
        edge_description = f"{source_node} extends from {target_node}"
    if source_node in Edge_Information:
        for edge_info in Edge_Information[source_node]:
            if edge_info["Name"] == target_node:
                edge_description += (
                    f", the correlation score between {source_node} and {target_node} is {edge_info['RelatedScore']}. The reason for this score is: {edge_info['ScoreReason']}"
                )
                break
    # print(edge_description)
    return edge_description

def judge_fox_front_entity(entity_name):
    return entity_name[:3].upper() == "FOX"

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
        # await worker(semaphore, prompt, community_reports)



async def get_community_report(
    data_path, graph_path, community_path, save_path, concurrent_num
):
    """
    使用 LLM 生成社区报告
        graph_path: code graph path
        community_path: raw community information path
        save_path: path to save community report
        concurrent_num: concurrent number to send llm requests
    """
    Edge_Information = {}
    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)
        for node in data:
            if "DependentEdgeInformation" not in node:
                Edge_Information[node["Name"]] = []
            else:
                Edge_Information[node["Name"]] = node["DependentEdgeInformation"]
     
    with open(graph_path, "r") as f:
        graph = nx.node_link_graph(json.load(f))

    community_reports = {}
    prompt_inputs = []
    with open(community_path, "r", encoding="utf-8") as file:
        data = json.load(file)
        for community in data:
            community_id = community["community_id"]
            nodes = community["nodes"]
            edges = community["edges"]
            prompt_input = "Entity Info:\n\nentity,description\n"
            num_tokens = num_tokens_from_string(prompt_input)
            for node in nodes:
                current_node = graph.nodes[node]
                if judge_fox_front_entity(current_node["name"]):
                    continue
                new_context = f"{current_node['name']}, {get_community_node_content(current_node)}\n"
                current_tokens = num_tokens_from_string(new_context)
                if num_tokens + current_tokens >= MAX_TOKEN:
                    break
                prompt_input += new_context
                num_tokens += current_tokens
            message_description = "Relationships:\n\nsource,target,description (The description may include correlation score (ranging from 0 to 10))\n"
            current_tokens = num_tokens_from_string(message_description)
            if num_tokens + current_tokens < MAX_TOKEN:
                prompt_input += message_description
                num_tokens += current_tokens
                for edge in edges:
                    edge_description = ""
                    source_node = graph.nodes[edge[0]]["name"]
                    target_node = graph.nodes[edge[1]]["name"]
                    if judge_fox_front_entity(source_node) or judge_fox_front_entity(target_node):
                        continue
                    edge_type = graph.edges[edge]["type"]
                    edge_description = get_description_message(edge_type, Edge_Information, source_node, target_node)
                    current_tokens = num_tokens_from_string(edge_description)
                    if num_tokens + current_tokens >= MAX_TOKEN:
                        break
                    prompt_input += (
                        f"{source_node},{target_node},{edge_description}\n"
                    )
                    num_tokens += current_tokens

            community_reports[community_id] = {}
            community_reports[community_id]["level"] = community["level"]
            community_reports[community_id]["nodes"] = nodes
            community_reports[community_id]["edges"] = edges
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

    with open(save_path, "w") as f:
        json.dump(community_reports, f, indent=4, ensure_ascii=False)

    print(f"Successfully save llm-generated community reports to {save_path} !")


async def get_new_community_report(
    data_path, graph_path, community_path, save_path, edge_power_graph_save_path, concurrent_num
):
    """
    使用 Leidan、文件夹、大模型判断的边权分构建边权图，生成新的社区报告
        graph_path: code graph path
        community_path: raw community information path
        save_path: path to save community report
        concurrent_num: concurrent number to send llm requests
    """
    ast_graph_information = read_json_file(data_path)
    code_graph_information = read_json_file(graph_path)
    leidan_message_information = read_json_file(community_path)
    leidan_message_information = desolve_leidan(leidan_message_information)
    # commit_message_information = read_json_file(commit_message_path)

    the_useful_graph_information, node_name_to_id_MP, all_node_name_to_id_MP = get_useful_information_of_code_graph(code_graph_information)
    the_useful_ast_information, import_edge_power_information_by_llm, method_edge_power_information_by_llm = get_useful_information_of_ast_graph(ast_graph_information)
    # 构建基础的边图信息，初始化节点
    edge_power_graph = construct_base_edge_power_graph(code_graph_information)

    # 过滤社区中fox开头的实体点，其中，fox开头的实体点在graphs search中的社区报告生成过程已经过滤了
    leidan_message_information = filter_fox_entity(leidan_message_information, all_node_name_to_id_MP)
    # 添加大模型的边权评分信息
    add_edge_power_information_by_llm(import_edge_power_information_by_llm, node_name_to_id_MP, edge_power_graph)

    # # 获取ast_graph图中的边权信息
    # add_ast_graph_information_edge(ast_graph_information, node_name_to_id_MP, edge_power_graph)

    # # 获取pagelist图中的边权信息
    # add_pagelist_information_edge(ast_graph_information, node_name_to_id_MP, edge_power_graph)

    # 添加leidan图中的边权信息
    add_leidan_information_edge(leidan_message_information, node_name_to_id_MP, edge_power_graph)

    # 添加文件夹中的边权信息
    file_fold_MP = add_fold_information_edge_with_file_level(ast_graph_information, node_name_to_id_MP, edge_power_graph) 
    
    # # 添加commit图中的边权信息
    # add_commit_information_edge(commit_message_information, node_name_to_id_MP, edge_power_graph)

    # 根据边权图提取社区信息
    all_community_message = exact_community_from_edge_power_graph(edge_power_graph, node_name_to_id_MP)
    

    # 给生成的新社区去重
    all_community_message = deduplication_community_information(all_community_message)
    
    
    # 使用大模型给每个community打分，并保存
    all_new_community_report = []
    for id in all_community_message:
        new_community_report = await assess_community_relevance_score(id, all_community_message[id], the_useful_ast_information, file_fold_MP, node_name_to_id_MP, edge_power_graph, concurrent_num)
        all_new_community_report.append(new_community_report)

    # 存储新的社区信息文件（all_new_community_report），以及图节点文件（code_graph_information）
    update_community_information(save_path, graph_path, all_new_community_report, code_graph_information)
    
    save_to_json(edge_power_graph, edge_power_graph_save_path)
