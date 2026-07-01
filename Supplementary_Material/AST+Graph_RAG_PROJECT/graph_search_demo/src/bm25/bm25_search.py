from langchain_community.retrievers import BM25Retriever
from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Plus
import numpy as np


def bm25_search_by_chroma_vector(
    vector_db: Chroma,
    query,
    filter=None,
    top_k=0,
):
    if top_k == 0:
        return []
    # initialize the bm25 retriever and faiss retriever
    data = vector_db.get(where=filter)
    ids = data["ids"]
    if not len(ids):
        return []
    metadatas = data["metadatas"]
    documents = data["documents"]
    bm25 = BM25Plus(documents)
    scores = bm25.get_scores(query=query)
    top_n = np.argsort(scores)[::-1][:top_k]
    # 分数转成负数，保证越小的相似度越高，和 embedding 的分数规则保持一致
    result = [
        (Document(page_content=documents[i], metadata=metadatas[i]), -scores[i])
        for i in top_n
        # 过滤掉 0分
        if (scores[i] > 0)
    ]
    return result


def bm25_search_by_nodes(
    nodes,
    query,
    collection_name,
    filter=None,
    top_k=0,
):
    if top_k == 0:
        return []
    # initialize the bm25 retriever and faiss retriever
    # 生成过滤条件，目前仅支持 按 id 进行过滤 $nin $in
    filter_condition = lambda id: True
    if filter and filter.get("id") and filter.get("id").get("$nin"):
        no_set = set(filter.get("id").get("$nin"))
        filter_condition = lambda id: id not in no_set
    elif filter and filter.get("id") and filter.get("id").get("$in"):
        yes_set = filter.get("id").get("$in")
        filter_condition = lambda id: id in yes_set

    node_list = [
        {"id": node_id, "content": nodes[node_id][collection_name]}
        for node_id in nodes
        if filter_condition(node_id) and (collection_name in nodes[node_id])
    ]
    if not len(node_list):
        return []
    documents = [node["content"] for node in node_list]
    bm25 = BM25Plus(documents)
    scores = bm25.get_scores(query=query)
    top_n = np.argsort(scores)[::-1][:top_k]
    # 分数转成负数，保证越小的相似度越高，和 embedding 的分数规则保持一致
    result = [
        (
            Document(
                page_content=documents[i], metadata={"id": node_list[i]["id"]}
            ),
            -scores[i],
        )
        for i in top_n
        # 过滤掉 0分
        if (scores[i] > 0)
    ]
    return result
