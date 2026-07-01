import math
from utils.hybrid_score import (
    hybrid_search_score_4_list,
    hybrid_list_calc_final_score,
)


def get_recall_list_with_sorted(recall, exists_ids=[], unique=True):
    """
    recall 数据
    unique 是否需要去重
    exists_ids 去重时需要过滤的 id
    """
    # 合并数据
    all_recall = [item for itemlist in recall.values() for item in itemlist]
    # 线按分数进行排序，优先保证分优的在前边，后续不会过滤
    all_recall = sorted(all_recall, key=lambda x: x["score"])
    final_recall = (
        filter_list_by_id(data_list=all_recall, exists_ids=exists_ids)
        if unique
        else all_recall
    )
    return final_recall


def filter_list_by_id(data_list, exists_ids=[]):
    """
    按id进行去重, 保证原来的顺序，优先保留前边的
    """
    final_list = []
    id_cache = set()
    for item in data_list:
        id = item["id"]
        if id not in id_cache and id not in exists_ids:
            id_cache.add(item["id"])
            final_list.append(item)
    return final_list


def get_optimal_embedding_data_by_id_map(search_res):
    """
    找到实体对应的分数最优的召回，放到最终结果里进行排序
    """
    all_list = get_recall_list_with_sorted(
        recall=search_res["recall"], unique=False
    )
    sub_query = search_res["sub_query"]
    for i in range(len(sub_query)):
        item = sub_query[i]
        all_list += get_recall_list_with_sorted(
            recall=item["recall"], unique=False
        )
    # 倒叙排序
    all_list = sorted(all_list, key=lambda x: -x["score"])
    final_id_map = {}
    for i in range(len(all_list)):
        item = all_list[i]
        id = item["id"]
        final_id_map[id] = item
    return final_id_map


def gen_final_result(search_res, top_k, query_top_k, sub_top_k, bm25_top_k):
    """
    计算数量

    embedding 相关: (总 top_k)
        原问题 query_top_k
            query_top_k = top_k - sub_top_k

        子问题占的数量，最多 3/4
            sub_top_k = min(len(sub_query) / (len(sub_query) + 1) + , 3/4)

        每个子问题，保证最少有一个进去，先各取一个分最高的
        剩下的子问题召回按分进行排序补齐到预期的数量
        如果问题个数过多，导致取不全了，直接忽略后边的子问题，说明分配不合理 或者 子问题拆分有问题

    bm25: bm25_top_k 不区分问题类别，整体补充 bm25_top_k (top_k / 5) 个 id 去重前的数量（ 实际可能 < bm25_top_k ）
    """
    id_cache = set()  # 缓存实体id，去重使用
    final_recall_embedding_list = []
    # 原问题最终召回的 实体
    query_final_all_recall = get_recall_list_with_sorted(
        recall=search_res["recall"]
    )[:query_top_k]

    final_recall_embedding_list += query_final_all_recall
    # 更新已经召回 实体id 到去重缓存中
    id_cache.update(set([item["id"] for item in query_final_all_recall]))

    first_sub_embedding_recall = []
    other_sub_embedding_recall = []
    sub_query = search_res["sub_query"]
    for i in range(min(len(sub_query), sub_top_k)):
        item = sub_query[i]
        sub_final_all_recall = get_recall_list_with_sorted(
            recall=item["recall"], exists_ids=id_cache
        )
        # 每个问题各取一个放到最终的结果里
        first_sub_embedding_recall += sub_final_all_recall[0:1]
        # 剩余的汇总起来
        other_sub_embedding_recall += sub_final_all_recall[1:]
    # first_sub_embedding_recall 去重

    first_sub_embedding_recall = filter_list_by_id(
        data_list=first_sub_embedding_recall, exists_ids=id_cache
    )
    final_recall_embedding_list += first_sub_embedding_recall
    # 更新已经召回 实体id 到去重缓存中
    id_cache.update(set([item["id"] for item in first_sub_embedding_recall]))

    other_sub_embedding_recall = sorted(
        other_sub_embedding_recall, key=lambda x: x["score"]
    )
    # other_sub_embedding_recall 去重
    other_sub_embedding_recall = filter_list_by_id(
        data_list=other_sub_embedding_recall, exists_ids=id_cache
    )
    # 计算子问题剩余可召回的数量
    sub_left_top_k = max(sub_top_k - len(first_sub_embedding_recall), 0)
    final_recall_embedding_list += other_sub_embedding_recall[0:sub_left_top_k]
    # 更新已经召回 实体id 到去重缓存中
    id_cache.update(set([item["id"] for item in final_recall_embedding_list]))

    optimal_id_map = get_optimal_embedding_data_by_id_map(search_res=search_res)

    final_recall_embedding_list = [
        optimal_id_map[item["id"]] for item in final_recall_embedding_list
    ]

    # 最终排序
    final_recall_embedding_list = sorted(
        final_recall_embedding_list, key=lambda x: x["score"]
    )

    # ********************** BM25 **********************
    bm25_final_res = []
    bm25_final_res += get_recall_list_with_sorted(
        recall=search_res["bm25_recall"]
    )
    sub_query = search_res["bm25_sub_query"]
    for i in range(len(sub_query)):
        item = sub_query[i]
        sub_recall = item["recall"]
        bm25_final_res += get_recall_list_with_sorted(recall=sub_recall)
    # 排序, 取 top_k
    bm25_final_res = sorted(bm25_final_res, key=lambda x: x["score"])
    # 去重
    bm25_final_res = filter_list_by_id(
        data_list=bm25_final_res, exists_ids=id_cache
    )
    bm25_final_res = bm25_final_res[:bm25_top_k]
    # 更新已经召回 实体id 到去重缓存中
    id_cache.update(set([item["id"] for item in bm25_final_res]))

    final_res = final_recall_embedding_list + bm25_final_res

    # 存储中间态的结果召回结果
    search_res["final_embedding_recall"] = final_recall_embedding_list
    search_res["final_bm25_recall"] = bm25_final_res

    return final_res


def gen_hybrid_result(search_res, top_k, query_top_k, sub_top_k, bm25_top_k):
    """
    混合检索
    原问题按 hybrid_score 召回 query_top_k 个
    子问题按 hybrid score 召回 sub_top_k / 子问题个数
    将每个问题的召回结果重新进行算分 打平后进行排序
    """
    embedding_recall = get_recall_list_with_sorted(
        recall=search_res["recall"], unique=False
    )
    bm25_recall = get_recall_list_with_sorted(
        recall=search_res["bm25_recall"], unique=False
    )
    search_score_embedding = hybrid_search_score_4_list(embedding_recall)
    search_score_bm25 = hybrid_search_score_4_list(bm25_recall)
    query_final_res = hybrid_list_calc_final_score(
        search_score_embedding + search_score_bm25
    )[:query_top_k]
    # 对召回结果重新进行算分 方便后续进行总体排序
    query_final_res = hybrid_search_score_4_list(query_final_res)

    sub_embedding_recall = search_res["sub_query"]
    sub_bm25_recall = search_res["bm25_sub_query"]

    sub_recall = []
    every_sub_top_k = math.ceil(
        sub_top_k / len(sub_embedding_recall)
    )  # 向上取整，可能会多召回n个
    for i in range(len(sub_embedding_recall)):
        embedding_recall = get_recall_list_with_sorted(
            recall=sub_embedding_recall[i]["recall"], unique=False
        )
        bm25_recall = get_recall_list_with_sorted(
            recall=sub_bm25_recall[i]["recall"], unique=False
        )
        search_score_embedding = hybrid_search_score_4_list(embedding_recall)
        search_score_bm25 = hybrid_search_score_4_list(bm25_recall)
        sub_res = hybrid_list_calc_final_score(
            search_score_embedding + search_score_bm25
        )
        # 对召回结果重新进行算分 方便后续进行总体排序
        sub_recall += hybrid_search_score_4_list(sub_res[0:every_sub_top_k])

    finla_res = hybrid_list_calc_final_score(query_final_res + sub_recall)

    return finla_res
