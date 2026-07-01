from services.model_config import embedding_qurey_model


# 聚合 query ，一起进行 embedding
def embedding_querys(query, user_question, sub_querys=[]):
    """
    未开启问题重写（or 问题未被重写）
    query 和 user_question 是一致的 只embedding 一次
    """
    embedding_result = embedding_qurey_model.embed_documents(
        ([query] if user_question == query else [user_question, query])
        + sub_querys
    )
    query_embeddings = {}
    if user_question == query:
        query_embeddings["user_question"] = embedding_result[0]
        query_embeddings["query"] = embedding_result[0]
        query_embeddings["sub_query"] = embedding_result[1:]
    else:
        query_embeddings["user_question"] = embedding_result[0]
        query_embeddings["query"] = embedding_result[1]
        query_embeddings["sub_query"] = embedding_result[2:]
    return query_embeddings
