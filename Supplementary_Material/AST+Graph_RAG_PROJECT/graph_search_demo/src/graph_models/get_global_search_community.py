import json
import asyncio
import networkx as nx
from constants import DRIVE_PAGE_MAP, DRIVE_MODULE_MAP
from utils import num_tokens_from_string
from services.llm_community_report_chain import llm_community_report_chain


MAX_TOKEN = 100 * 1000


async def worker(semaphore, prompt_input, community_reports):
    async with semaphore:
        result = await llm_community_report_chain(
            prompt_input, community_type="global"
        )
        community_reports[prompt_input["id"]]["reports"] = result


def merge_leiden_community(community_reports, leiden_community_path):
    new_community_reports = {}
    community_id = 0
    with open(leiden_community_path, "r", encoding="utf-8") as file:
        leiden_community_reports = json.load(file)
        for i in community_reports:
            new_community_reports[i] = {}
            new_community_reports[i]["level"] = community_reports[i]["level"]
            new_community_reports[i]["reports"] = community_reports[i][
                "reports"
            ]
            community_id = i
        for i in leiden_community_reports:
            community_id += 1
            new_community_reports[community_id] = {}
            new_community_reports[community_id]["level"] = (
                leiden_community_reports[i]["level"]
            )
            new_community_reports[community_id]["reports"] = (
                leiden_community_reports[i]["reports"]
            )
    return new_community_reports


async def get_global_search_community(
    graph_path, save_path, leiden_community_path, concurrent_num=5
):
    with open(graph_path, "r") as f:
        graph: nx.Graph = nx.node_link_graph(json.load(f))

    # 获取 level 2 列表
    page_list = []
    for _ in DRIVE_PAGE_MAP:
        page_list += DRIVE_PAGE_MAP[_]

    # 构建 level 2 的节点信息
    community_map = {}
    community_id = 0
    for _ in page_list:
        community_map[_] = {
            "community_id": community_id,
            "name": _,
            "level": 2,
            "nodes": [],
        }
        community_id += 1

    for id in graph.nodes():
        node = graph.nodes[id]
        if node["is_leaf"]:
            continue
        for page in node["pageList"]:
            if page in page_list:
                community_map[page]["nodes"].append(id)

    # LLM 生成社区报告
    community_reports = {}
    tasks = []
    semaphore = asyncio.Semaphore(concurrent_num)

    # Report for Level 2
    for page in community_map:
        prompt_input = f"以下是页面 {page} 的内容描述: \n"
        num_tokens = 0
        nodes = community_map[page]["nodes"]

        for node in nodes:
            current_node = graph.nodes[node]
            new_context = f"{current_node['name']}, {current_node['report']}\n"
            current_tokens = num_tokens_from_string(new_context)
            if num_tokens + current_tokens >= MAX_TOKEN:
                break
            prompt_input += new_context
            num_tokens += current_tokens

        id = community_map[page]["community_id"]
        community_reports[id] = {
            "community_id": id,
            "name": page,
            "level": 2,
            "reports": "",
            "nodes": nodes,
        }

        tasks.append(
            asyncio.create_task(
                worker(
                    semaphore,
                    {"id": id, "input": prompt_input},
                    community_reports,
                )
            )
        )

    await asyncio.gather(*tasks)

    # Report for Level 1
    tasks = []
    for module in DRIVE_PAGE_MAP:
        prompt_input = f"以下是 {DRIVE_MODULE_MAP[module]} 的内容描述: \n"
        num_tokens = 0
        nodes = []
        for page in DRIVE_PAGE_MAP[module]:
            nodes += community_map[page]["nodes"]
            current_community_id = community_map[page]["community_id"]
            new_context = f"{page}, {community_reports[current_community_id]['reports']}\n"
            current_tokens = num_tokens_from_string(new_context)
            if num_tokens + current_tokens >= MAX_TOKEN:
                break
            prompt_input += new_context
            num_tokens += current_tokens

        community_reports[community_id] = {
            "community_id": community_id,
            "name": module,
            "level": 1,
            "reports": "",
            "nodes": list(set(nodes)),
        }
        community_map[module] = {}
        community_map[module]["community_id"] = community_id
        tasks.append(
            asyncio.create_task(
                worker(
                    semaphore,
                    {"id": community_id, "input": prompt_input},
                    community_reports,
                )
            )
        )
        community_id += 1

    await asyncio.gather(*tasks)

    # Report for Level 0
    tasks = []
    prompt_input = "以下是 target_bundle 整体仓库的内容描述: \n"
    num_tokens = 0
    for module in DRIVE_PAGE_MAP:
        new_context = f"{module}, {community_reports[community_map[module]['community_id']]['reports']}\n"
        current_tokens = num_tokens_from_string(new_context)
        if num_tokens + current_tokens >= MAX_TOKEN:
            break
        prompt_input += new_context
        num_tokens += current_tokens

    community_reports[community_id] = {
        "community_id": community_id,
        "name": "target_bundle",
        "level": 0,
        "reports": "",
        "nodes": [],
    }

    tasks.append(
        asyncio.create_task(
            worker(
                semaphore,
                {"id": community_id, "input": prompt_input},
                community_reports,
            )
        )
    )
    await asyncio.gather(*tasks)

    community_reports = merge_leiden_community(
        community_reports, leiden_community_path
    )

    with open(save_path, "w") as f:
        json.dump(community_reports, f, indent=4, ensure_ascii=False)
