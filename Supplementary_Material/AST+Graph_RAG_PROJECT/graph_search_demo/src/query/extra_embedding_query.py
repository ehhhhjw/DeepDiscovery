import json
from typing import Dict
from utils import query_nodes
from bm25 import bm25_search_by_chroma_vector
from constants import COMMIT_COLLECTION_NAMES
from enum import Enum


class RAG_SEARCH_TYPE(Enum):
    EMBEDDING = 1
    BM25 = 2


# commit embedding 检索
def commit_search(search_type: RAG_SEARCH_TYPE, params):
    G = params["G"]
    vector_db = params["vector_db"]
    top_k = params["top_k"]
    score_limit = params.get("score_limit") or float("inf")
    query = (
        params["query"]
        if search_type == RAG_SEARCH_TYPE.BM25
        else params["query_embedding"]
    )

    res = {}
    recall = []
    if search_type == RAG_SEARCH_TYPE.EMBEDDING:
        recall = vector_db.similarity_search_by_vector_with_relevance_scores(
            k=top_k,
            embedding=query,
            # TODO commit 类型先不执行过滤（log）
            filter=None,
        )
    else:
        recall = bm25_search_by_chroma_vector(
            vector_db=vector_db,
            query=query,
            top_k=top_k,
        )
    recall = sorted(recall, key=lambda x: x[1])
    for entity, score in recall:
        # 按分数进行过滤
        if score > score_limit:
            continue
        commit_entity = []
        files = json.loads(entity.metadata["files"])
        # 通过文件列表查询对应实体
        for commit_file in files:
            graph_nodes = query_nodes(
                G=G,
                attribute="name",
                value=commit_file["name"],
            )
            commit_entity += list(graph_nodes)
        # message = entity.metadata["message"]
        # print(f"commit: {message}. score: {score}")
        if len(commit_entity) == 0:
            # print("entity is empty")
            continue
        for id, item in commit_entity:
            # print(f"  ID: {item['name']}")
            data = {
                "id": id,
                "name": item["name"],
                "score": score,  # 多次添加的相同文件取最高分
                "type": COMMIT_COLLECTION_NAMES[0],
                "extra": {"message": entity.metadata},
            }
            # final_res.append(data)
            if id in res:
                # 多次添加的文件处理
                res[id]["total"] += 1
            else:
                res[id] = {"total": 1, "score": score, "data": data}

    # 自定义排序函数
    def custom_sort(item):
        # item => (key, value)
        key, value = item
        # 先按 total 的降序排列，total > 1 的优先
        # 再按 score 的升序排列，总是按升序排列，确保小分数优先
        # 使用负值处理 total 的降序排序
        return (-value["total"], value["score"])

    # 排序
    sorted_res = sorted(res.items(), key=custom_sort)
    # 取出 data 字段组成 list
    data_list = [item[1]["data"] for item in sorted_res]

    # TAG commit 可能对应很多个实体，限制数量
    return data_list[0:top_k]


def search_commit_by_embedding(params: Dict[str, any]):
    res = commit_search(search_type=RAG_SEARCH_TYPE.EMBEDDING, params=params)
    return res


def search_commit_by_bm25(params: Dict[str, any]):
    res = commit_search(search_type=RAG_SEARCH_TYPE.BM25, params=params)
    return res
