hybird_score_k = 60


def hybrid_search_score_4_list(data_list):
    result = []
    for index in range(len(data_list)):
        result.append(
            {
                **data_list[index],
                "score": 1 / (hybird_score_k + index),
            }
        )
    return result


def hybrid_list_calc_final_score(data_list):
    cache = {}
    for index in range(len(data_list)):
        id = data_list[index]["id"]
        score = data_list[index]["score"]
        if id in cache:
            cache[id]["score"] = cache[id]["score"] + score
        else:
            cache[id] = {**data_list[index]}
    list_1 = []
    for key in cache:
        list_1.append(cache[key])
    # 分数大排序在前边，hybrid 的 score 越大越好
    list_1 = sorted(list_1, key=lambda x: -x["score"])
    return list_1
