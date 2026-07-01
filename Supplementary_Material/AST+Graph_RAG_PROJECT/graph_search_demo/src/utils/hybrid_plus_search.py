import math
from utils.hybrid_score import (
    hybrid_search_score_4_list,
    hybrid_list_calc_final_score,
)


def hybrid_plus_search(
    nodes, top_k, search_res, query_top_k, sub_top_k, bm25_top_k
):
    bm25_len = 20  # TOOD： bm25的效果不太好，先只取一个
    """
    混合检索（替代rerank的版本）
    将所有的实体转化成混合检索分，如果是叶子节点，将父节点插入并给一半的分
    如果父节点存在，则子节点可以删除，还是要按分来
    """
    query_hybrid_list = []
    # 处理原问题
    for item_list in search_res["recall"].values():
        hybrid_list = hybrid_search_score_4_list(item_list)
        query_hybrid_list += hybrid_list
    for item_list in search_res["bm25_recall"].values():
        hybrid_list = hybrid_search_score_4_list(item_list[:bm25_len])
        query_hybrid_list += hybrid_list

    sub_query = search_res["sub_query"]
    # 处理子问题
    sub_query_hybrid_list = []
    for i in range(len(sub_query)):
        sub_recall = sub_query[i]["recall"]
        for item_list in sub_recall.values():
            hybrid_list = hybrid_search_score_4_list(item_list)
            sub_query_hybrid_list += hybrid_list

    # 处理bm25子问题
    bm25_sub_query = search_res["bm25_sub_query"]
    for i in range(len(bm25_sub_query)):
        sub_recall = bm25_sub_query[i]["recall"]
        for item_list in sub_recall.values():
            hybrid_list = hybrid_search_score_4_list(item_list[:bm25_len])
            sub_query_hybrid_list += hybrid_list

    final_list = hybrid_list_calc_final_score(
        query_hybrid_list + sub_query_hybrid_list
    )

    # 遍历添加 追加父节点
    parent_node_list = []
    for i in range(len(final_list)):
        item = final_list[i]
        id = item["id"]
        node = nodes[id]
        # 非叶子节点没有父节点
        if node["is_leaf"] == False:
            continue
        if "parent_id" not in node:
            continue
        parent_id = node["parent_id"]
        # parent_id 不存在的时候为 -1
        if not nodes[parent_id]:
            continue
        # 叶子节点追加 parent_id
        parent_node_list.append(
            {
                "id": parent_id,
                "score": item["score"] / 2,  # 先按子节点一半的分数追加父节点
                "type": "hybrid",
                "name": nodes[parent_id]["name"],
            }
        )
    final_result = hybrid_list_calc_final_score(final_list + parent_node_list)
    return final_result[0 : query_top_k + sub_top_k]
