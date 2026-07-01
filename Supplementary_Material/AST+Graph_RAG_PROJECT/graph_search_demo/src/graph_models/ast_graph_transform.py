import json
import networkx as nx
from graspologic.partition import hierarchical_leiden
from graspologic.utils import largest_connected_component
from constants import EdgeType
from .code_graph_add_parent_id import add_parent_id_to_node


def ast_graph_transform(
    data_path: str,
    graph_save_path: str,
    community_save_path: str,
    max_cluster_size=50,
):
    """
    AST -> networkx graph 方便后续计算与存储, 并使用 Leiden 算法生成社区
    Args:
        data_path: AST data path
        graph_save_path: path to save networkx graph
        community_save_path: path to save community information
        max_cluster_size: max cluster size for leiden algorithm
    """
    print(
        "Start transform AST json to networkx graph and detect communities......"
    )
    G = nx.DiGraph()

    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)
        node_map = {}
        for node in data:
            if node["Name"] not in node_map:
                id = len(node_map)
                node_map[node["Name"]] = id
                for _ in [
                    "Report",
                    "ShortReport",
                    "Comment",
                    "Description",
                    "FileContent",
                ]:
                    if _ not in node:
                        node[_] = ""
                G.add_node(
                    id,
                    name=node["Name"],
                    isLog=node["IsUtLog"],
                    report=node["Report"],
                    short_report=node["ShortReport"],
                    comment=node["Comment"] if node["Comment"] else node["FileComment"],
                    description=node["Description"],
                    path=node["Root"],
                    type=node["Type"],
                    pageList=node["RootPage"],
                    file_content=node["FileContent"],
                    is_leaf=False,
                    community_id=[],
                )
            for child in node["Children"]:
                child["Name"] = node["Name"] + "." + child["Name"]
                if child["Name"] not in node_map:
                    id = len(node_map)
                    node_map[child["Name"]] = id
                    for _ in ["Report", "ShortReport", "Comment", "Code"]:
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
                        short_report=child["ShortReport"],
                        comment=child["Comment"],
                        description=child["Code"],
                        path=node["Root"],
                        type=child["Type"],
                        pageList=child["RootPage"],
                        code_comment=code_comment,
                        is_leaf=True,
                        community_id=[],
                    )

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

    results_by_level = compute_communities(
        graph=G, use_lcc=True, max_cluster_size=max_cluster_size
    )
    community_info = []
    for level in results_by_level:
        for community_id in results_by_level[level]:
            current_record = {}
            current_record["community_id"] = community_id
            current_record["level"] = level
            # 社区内的 class 节点集合
            current_record["nodes"] = results_by_level[level][community_id]
            # 与社区内的 class 节点相关联的边的集合
            current_record["edges"] = []
            for node in current_record["nodes"]:
                # 更新节点的 community_id
                G.nodes[node]["community_id"].append(community_id)
                edge_list = list(G.out_edges(node)) + list(G.in_edges(node))
                for edge in edge_list:
                    if G.edges[edge]["type"] == "child":
                        G.nodes[edge[0]]["community_id"].append(community_id)
                        G.nodes[edge[1]]["community_id"].append(community_id)
                    else:
                        current_record["edges"].append(edge)
            current_record["edges"] = list(set(current_record["edges"]))
            community_info.append(current_record)

    all_graph_nodes = list(G.nodes())
    for node in all_graph_nodes:
        G.nodes[node]["community_id"] = list(set(G.nodes[node]["community_id"]))

    with open(graph_save_path, "w") as f:
        json.dump(
            add_parent_id_to_node(nx.node_link_data(G)),
            f,
            indent=4,
            ensure_ascii=False,
        )

    with open(community_save_path, "w") as f:
        json.dump(community_info, f, indent=4, ensure_ascii=False)

    print("Successfully transform AST json and detect communities !")
    print(f"Save graph to {graph_save_path} !")
    print(f"Save community map to {community_save_path} !")


def compute_communities(graph: nx.DiGraph, use_lcc=True, max_cluster_size=10):
    """
    使用 Leiden 算法提取社区
    Args:
        graph: networkx graph
        use_lcc: 是否使用最大连通分量
        max_cluster_size: Leiden 算法参数设定, 详情可参考算法细节
    """
    graph = graph.copy()

    # 只将 class 这一层级纳入社区计算
    class_nodes = [
        n for n, attr in graph.nodes(data=True) if not attr.get("is_leaf")
    ]
    graph = graph.subgraph(class_nodes).copy()

    if use_lcc:
        graph = largest_connected_component(graph)

    community_mapping = hierarchical_leiden(
        graph.to_undirected(),
        max_cluster_size=max_cluster_size,
        random_seed=2024,
    )

    results: dict[int, dict[int, int]] = {}
    for partition in community_mapping:
        results[partition.level] = results.get(partition.level, {})
        results[partition.level][partition.node] = partition.cluster

    levels = sorted(results.keys())
    results_by_level = {}
    for level in levels:
        result = {}
        results_by_level[level] = result
        for node_id, community_id in results[level].items():
            if community_id not in result:
                result[community_id] = []
            result[community_id].append(node_id)

    return results_by_level
