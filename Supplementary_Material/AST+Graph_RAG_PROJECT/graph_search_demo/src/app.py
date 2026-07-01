from flask import Flask, request
from query.local_search import (
    local_search_without_chat,
    handle_user_question,
    rag_without_chat,
    local_chat,
)
from utils.args import ChatArgs
from utils.upload_log import upload_log
import traceback
from utils.stdout import DualOutput
from constants import (
    ROOT_PATH,
    COLLECTION_NAMES,
    COMMIT_COLLECTION_NAMES,
    SearchType,
)
from datetime import datetime
from utils.utils import get_base_params

app = Flask(__name__)


@app.route("/v1/local/handle_user_question", methods=["POST"])
async def v1_handle_user_question():
    try:
        body = request.get_json()
        # conversation_id = body.get("conversation_id")
        user_question = body.get("user_question")
        open_trace = body.get("open_trace", False)
        print(user_question)
        base_params = get_base_params(data=body)
        args = ChatArgs(
            **base_params,
            user_question=user_question,
        )

        if not args.user_question:
            return {"error": "用户问题不能为空"}, 500

        result = await handle_user_question(
            args=args, user_question=args.user_question
        )

        return {
            # 原始参数
            **base_params,
            # 处理后的结果
            **result,
            "open_trace": open_trace,
            "user_question": user_question,
        }
    except:
        stack_trace = traceback.format_exc()
        print("/v1/local/prompt/get Error Stack:\n", stack_trace)
        return {"error": f"Somethins wrong! {stack_trace}"}, 500


@app.route("/v1/local/rag_without_chat", methods=["POST"])
async def v1_rag_without_chat():
    try:
        formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        log_path = ROOT_PATH / f"log/{formatted_datetime}"
        log_path.mkdir(parents=True, exist_ok=True)
        DualOutput.open(log_path=log_path)

        body = request.get_json()
        conversation_id = body.get("conversation_id")
        user_question = body.get("user_question")
        final_user_question = body.get("final_user_question")
        sub_querys = body.get("sub_querys")
        page_list = body.get("page_list")
        is_log = body.get("is_log")
        # 是否开启日志采集
        open_trace = body.get("open_trace", False)

        args = ChatArgs(
            **get_base_params(data=body),
            user_question=user_question,
        )
        if not args.user_question:
            return {"error": "用户问题不能为空"}, 500
        print(user_question)

        result = await rag_without_chat(
            args=args,
            user_question=user_question,
            final_user_question=final_user_question,
            sub_querys=sub_querys,
            page_list=page_list,
            is_log=is_log,
        )
        final_prompt = result["final_prompt"]
        metadata = result["metadata"]

        log_id = None
        if open_trace:
            log_id = upload_log(
                {
                    **metadata,
                    "chat_prompt": final_prompt,
                    "conversation_id": conversation_id,
                    "chat_query": user_question,
                }
            )
        print(
            f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } 整体返回"
        )
        DualOutput.close()
        # 返回 日志 ID，方便 brain平台上传日志时，进行关联
        return {
            "chat_prompt": final_prompt,
            "rerank_output": metadata.get("rerank_entity_names", []),
            "docs_rerank_output": metadata.get("doc_rerank_entity_names", []),
            "log_id": log_id,
        }
    except:
        stack_trace = traceback.format_exc()
        print("/v1/local/rag_without_chat Error Stack:\n", stack_trace)
        DualOutput.close()
        return {"error": f"Somethins wrong! {stack_trace}"}, 500


@app.route("/v1/local/prompt/get", methods=["POST"])
async def chat_dirve():
    try:
        formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        log_path = ROOT_PATH / f"log/{formatted_datetime}"
        log_path.mkdir(parents=True, exist_ok=True)
        DualOutput.open(log_path=log_path)
        body = request.get_json()
        conversation_id = (
            body["conversation_id"] if "conversation_id" in body else None
        )
        user_question = body["user_question"]
        # 是否开启日志采集
        open_trace = body.get("open_trace", False)
        print(user_question)
        args = ChatArgs(
            **get_base_params(data=body),
            user_question=user_question,
        )
        if not args.user_question:
            return {"error": "用户问题不能为空"}, 500
        result = await local_search_without_chat(
            args, user_question=args.user_question
        )
        final_prompt = result["final_prompt"]
        metadata = result["metadata"]

        log_id = None
        if open_trace:
            log_id = upload_log(
                {
                    **metadata,
                    "chat_prompt": final_prompt,
                    "conversation_id": conversation_id,
                    "chat_query": user_question,
                }
            )

        if args.open_chat:
            final_prompt, chunks = await local_chat(result)
            result = ""
            for chunk in chunks:
                result += chunk
            print(
                f">>>>>>>>>> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 整体返回"
            )
            DualOutput.close()

            # 返回 日志 ID，方便 brain平台上传日志时，进行关联
            return {"log_id": log_id, "chat_result": result}
        else:
            print(
                f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } 整体返回"
            )
            DualOutput.close()

            # 返回 日志 ID，方便 brain平台上传日志时，进行关联
            return {
                "chat_prompt": final_prompt,
                "rerank_output": metadata.get("rerank_entity_names"),
                "log_id": log_id,
            }
    except:
        stack_trace = traceback.format_exc()
        print("/v1/local/prompt/get Error Stack:\n", stack_trace)
        DualOutput.close()
        return {"error": f"Somethins wrong! {stack_trace}"}, 500


import os
import time
from services.model_config import embedding_qurey_model
from utils.load_vector_db import SingletonGetChroma
from query.extra_embedding_query import (
    search_commit_by_embedding,
    search_commit_by_bm25,
)
from utils.load_graph import SingletonLoadGraph


@app.route("/v1/local/query", methods=["POST"])
async def query_by_embedding():
    pid = os.getpid()
    body = request.get_json()
    collection_name = body["collection_name"]
    query_embedding = body.get("query_embedding")
    query = body.get("query")
    if not query_embedding and query:
        query_embedding = embedding_qurey_model.embed_documents([query])[0]
    if not query_embedding:
        return {"msg": "query_embedding 不能为空"}, 500
    filter_condition = body.get("filter_condition") or None
    search_type = body.get("search_type") or SearchType.CODE
    min_score = body.get("min_score") or float("inf")
    top_k = body.get("top_k") or 60
    print(
        f">>>>>>>>> trace_entry ---- c={collection_name} pid={pid} {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}"
    )
    start = time.time()
    args = ChatArgs()
    vector_db = SingletonGetChroma.get_db(
        collection_name=collection_name,
        persist_directory=args.db_path,
        embedding_function=embedding_qurey_model,
    )
    final_list = []
    graph_path = (
        args.graph_path
        if search_type == SearchType.CODE
        else args.docs_graph_path
    )
    if collection_name == COMMIT_COLLECTION_NAMES[0]:
        params = {
            "G": SingletonLoadGraph.get_code_graph(graph_path),
            "vector_db": vector_db,
            "top_k": top_k,
            "query_embedding": query_embedding,
            "score_limit": min_score,
        }
        commit_list = search_commit_by_embedding(params=params)
        final_list = [
            {
                "id": item["id"],
                "score": item["score"],
                "name": item["name"],
                "type": item["type"],
                "message": item["extra"]["message"],
            }
            for item in commit_list
        ]
    else:
        recall = vector_db.similarity_search_by_vector_with_relevance_scores(
            embedding=query_embedding,
            k=top_k,
            filter=filter_condition,
        )
        print(f"=========:graph_path:{graph_path}")
        G = SingletonLoadGraph.get_code_graph(graph_path)
        nodes = G.nodes
        final_list = []
        for i in recall:
            if i[1] <= min_score:
                final_list.append(
                    {
                        "id": i[0].metadata["id"],
                        "score": i[1],
                        "name": nodes[i[0].metadata["id"]]["name"],
                        "type": collection_name,
                    }
                )
        # short_report 过滤掉叶子节点, 只保留 class
        if collection_name == "short_report":
            final_list = [
                item
                for item in final_list
                if nodes[item["id"]]["is_leaf"] == False
            ]

    print(
        f">>>>>>> c={collection_name} pid={pid} rag_gap={time.time() - start} s"
    )

    return {"list": final_list}


from bm25 import bm25_search_by_nodes


@app.route("/v1/local/query/bm25", methods=["POST"])
async def query_by_bm25():
    """
    入参:
        collection_name: str
        query = str
        filter_condition = int[]
        min_score = int
        top_k = int
    """
    pid = os.getpid()
    body = request.get_json()
    collection_name = body["collection_name"]
    query = body["query"]
    filter_condition = body.get("filter_condition")
    min_score = body.get("min_score") or float("inf")
    search_type = body.get("search_type") or SearchType.CODE
    top_k = body.get("top_k") or 60
    print(
        f">>>>>>>>> trace_entry ---- c={collection_name} pid={pid} {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}"
    )
    start = time.time()
    args = ChatArgs()
    vector_db = SingletonGetChroma.get_db(
        collection_name=collection_name,
        persist_directory=args.db_path,
        embedding_function=embedding_qurey_model,
    )
    final_list = []
    graph_path = (
        args.graph_path
        if search_type == SearchType.CODE
        else args.docs_graph_path
    )
    G = SingletonLoadGraph.get_code_graph(graph_path)
    if collection_name == COMMIT_COLLECTION_NAMES[0]:
        params = {
            "G": G,
            "vector_db": vector_db,
            "top_k": top_k,
            "query": query,
        }
        commit_list = search_commit_by_bm25(params=params)
        final_list = [
            {
                "id": item["id"],
                "score": item["score"],
                "name": item["name"],
                "type": item["type"],
                "message": item["extra"]["message"],
            }
            for item in commit_list
        ]
    else:
        nodes = G.nodes
        recall = bm25_search_by_nodes(
            nodes=nodes,
            collection_name=collection_name,
            query=query,
            top_k=top_k,
            filter=filter_condition,
        )
        final_list = [
            {
                "id": i[0].metadata["id"],
                "score": i[1],
                "name": nodes[i[0].metadata["id"]]["name"],
                "type": collection_name,
            }
            for i in recall
            if i[1] <= min_score
        ]
        # short_report 过滤掉叶子节点, 只保留 class
        if collection_name == "short_report":
            final_list = [
                item
                for item in final_list
                if nodes[item["id"]]["is_leaf"] == False
            ]

    print(
        f">>>>>>> c={collection_name} pid={pid} rag_gap={time.time() - start} s"
    )

    return {"list": final_list}


import requests

# 记录缓存是否被激活过
is_active = False


@app.route("/v1/local/query-active", methods=["POST", "GET"])
async def query_active():
    """
    拉起 vector_db 到内存缓存
    """
    http_rag_active_url = os.environ.get("http_rag_active_url", None)
    # 通过对外接口访问重定向到内部接口上执行
    if http_rag_active_url:
        response = requests.request("GET", http_rag_active_url)
        return response.json()

    # 执行内存拉活逻辑
    pid = os.getpid()
    start = time.time()
    try:
        global is_active
        if is_active:
            return {"msg": "已经被激活过了", "pid": pid}
        query_embedding = embedding_qurey_model.embed_documents(["对星"])[0]
        args = ChatArgs()

        table_list = COLLECTION_NAMES + COMMIT_COLLECTION_NAMES

        for c in table_list:
            vector_db = SingletonGetChroma.get_db(
                collection_name=c,
                persist_directory=args.db_path,
                embedding_function=embedding_qurey_model,
            )
            vector_db.similarity_search_by_vector_with_relevance_scores(
                embedding=query_embedding,
                k=1,
                filter=None,
            )
        # 激活之后缓存标识
        is_active = True
        return {"success": True, "pid": pid, "spend": time.time() - start}
    except:
        return {"success": False, "pid": pid, "spend": time.time() - start}


@app.route("/", methods=["GET", "POST"])
async def app_root():
    return {"error": "Not Found"}, 404


@app.route("/<path:subpath>", methods=["GET", "POST"])
async def app_common(subpath):
    return {"error": "Not Found"}, 404


@app.route("/v1/local/doc_rag_without_chat", methods=["POST"])
async def doc_rag_without_chat():
    try:
        formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        log_path = ROOT_PATH / f"log/{formatted_datetime}"
        log_path.mkdir(parents=True, exist_ok=True)
        DualOutput.open(log_path=log_path)
        body = request.get_json()
        conversation_id = (
            body["conversation_id"] if "conversation_id" in body else None
        )
        user_question = body["user_question"]
        print(user_question)
        args = ChatArgs(
            **get_base_params(data=body),
            user_question=user_question,
        )
        if not args.user_question:
            return {"error": "用户问题不能为空"}, 500
        result = await local_search_without_chat(
            args, user_question=args.user_question
        )
        final_prompt = result["final_prompt"]
        metadata = result["metadata"]

        log_id = upload_log(
            {
                **metadata,
                "chat_prompt": final_prompt,
                "conversation_id": conversation_id,
                "chat_query": user_question,
            }
        )
        print(
            f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } 整体返回"
        )
        DualOutput.close()

        graph_path = args.docs_graph_path
        G = SingletonLoadGraph.get_code_graph(graph_path)
        nodes = G.nodes
        doc_rerank_entity_ids = metadata.get("doc_rerank_entity_ids")
        recall_entitys = []
        for node_id in doc_rerank_entity_ids:
            node = nodes[node_id]
            recall_entitys.append(node)

        # 返回 日志 ID，方便 brain平台上传日志时，进行关联
        return {
            "log_id": log_id,
            "user_question": user_question,
            "recall": recall_entitys,
        }
    except:
        stack_trace = traceback.format_exc()
        print("/v1/local/doc_rag_without_chat Error Stack:\n", stack_trace)
        DualOutput.close()
        return {"error": f"Somethins wrong! {stack_trace}"}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5002")
