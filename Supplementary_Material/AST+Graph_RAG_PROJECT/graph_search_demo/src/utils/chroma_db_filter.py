import networkx as nx


def get_target_filter_id_list(
    nodes: nx.Graph.nodes, need_log: int, query_page_list: list[int]
):
    """
    根据 pageList 进行数据过滤
    """
    # 不需要过滤
    if not len(query_page_list) and need_log == 1:
        return None
    filter_id_list = []
    for son_node in nodes:
        list1 = set(query_page_list)
        list2 = set(nodes[son_node]["pageList"])
        # isLog => 1-保留log文件 0-过滤log文件
        """
        两个条件满足一个，说明文件需要被过滤
        1-query_page_list存在且node不包含对应的page
        2-
        """
        if (query_page_list and not (list1 & list2)) or (
            need_log == 0 and nodes[son_node]["isLog"] == 1
        ):
            filter_id_list.append(son_node)
    return filter_id_list


def get_filter_condition(
    nodes: nx.Graph.nodes, need_log: int, query_page_list: list[int]
) -> dict:
    """
    Chroma_db 过滤条件, is_log + page_list
    """
    filter_ids = get_target_filter_id_list(
        nodes=nodes, need_log=need_log, query_page_list=query_page_list
    )
    # 空 [] or None
    if not filter_ids:
        return None
    return {
        "id": {"$nin": list(filter_ids)},
    }
