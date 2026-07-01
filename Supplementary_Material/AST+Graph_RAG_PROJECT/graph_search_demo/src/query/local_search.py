import sys
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from query import CodeGraphSearch, DocGraphSearch
import asyncio
from prompts import CHAT_PROMPT, CHAT_PROMPT_DOC, CHAT_PROMPT_WORKSPACE
from services.model_config import chat_model
from graph_models import get_tag_extract, get_sub_query_extract
from utils.args import ChatArgs
from constants import (
    SearchType,
    COLLECTION_NAMES,
    COLLECTION_SCORE_LIMIT,
    SUB_COLLECTION_SCORE_LIMIT,
    DOCS_COLLECTION_NAMES,
    COMMIT_COLLECTION_NAMES,
)
from datetime import datetime
from utils.embedding_query import embedding_querys


async def handle_user_question(args: ChatArgs, user_question):
    """
    问题重写 + 问题分类 + 问题拆解
    """
    sub_querys = args.sub_querys
    sub_querys = (
        [q.strip() for q in sub_querys.split(",") if q.strip()]
        if isinstance(sub_querys, str) and sub_querys != ""
        else []
    )
    page_list = []
    is_log = 1  # 默认不过滤
    final_user_question = user_question
    if args.open_query_split:
        rewrite_q, page_list, is_log = await get_tag_extract(user_question)
        # 问题重写
        if rewrite_q:
            final_user_question = rewrite_q
        # 如果没有传入子问题，通过模型提取
        if len(sub_querys) == 0:
            sub_querys = await get_sub_query_extract(final_user_question)
        print(f"\nsub_questions: {sub_querys}\n")
    return {
        # 新增数据
        "is_log": is_log,
        "page_list": page_list,
        "final_user_question": final_user_question,
        "sub_querys": sub_querys,
    }


async def rag_without_chat(
    args, user_question, final_user_question, sub_querys, page_list, is_log
):
    """
    将 handle_user_question 的结果，传入，继续执行 拿到 chat 需要的最终的 prompt
    """
    # 多个 graph 里都用到了 问题的embedding 结果，放在此处统一进行 embedding
    query_embeddings = {}
    print(
        f">>>>>>>>>> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} local search :query embedding start"
    )
    if args.is_use_code or args.is_use_docs:

        query_embeddings = embedding_querys(
            query=final_user_question,
            user_question=user_question,
            sub_querys=sub_querys,
        )


    code_graph_rag = None
    docs_graph_rag = None
    tasks = []
    if args.is_use_code:
        code_graph_rag = CodeGraphSearch(
            user_question=user_question,
            query=final_user_question,
            sub_querys=sub_querys,
            query_embeddings=query_embeddings,
            top_k=args.top_k,
            db_path=args.db_path,
            graph_path=args.graph_path,
            open_rerank=args.open_rerank,
            community_path=args.community_path,
            page_list=page_list,
            is_log=is_log,
            search_type=SearchType.CODE,
            table_list=COLLECTION_NAMES + COMMIT_COLLECTION_NAMES,
            max_tokens=80 * 1000,
            is_use_qa=args.is_use_qa,
            is_use_tech_doc=args.is_use_tech_doc,
            score_limit=COLLECTION_SCORE_LIMIT,
            sub_score_limit=SUB_COLLECTION_SCORE_LIMIT,
            is_local_tokens_limit_enabled=True,
            search_res_fields=args.search_res_fields,
            stage=args.stage,
        )
        tasks.append(code_graph_rag.execute_local_search())
    if args.is_use_docs:
        docs_graph_rag = DocGraphSearch(
            user_question=user_question,
            query=final_user_question,
            top_k=args.top_k,
            sub_top_k=4,
            db_path=args.db_path,
            open_rerank=args.open_rerank,
            sub_querys=sub_querys,
            query_embeddings=query_embeddings,
            is_use_code=False,
            is_use_docs=True,
            docs_graph_path=args.docs_graph_path,
            docs_community_path=args.docs_community_path,
            search_res_fields=args.search_res_fields,
            stage=args.stage,
        )
        tasks.append(docs_graph_rag.execute_local_search())

    print("Performing RAG ......")

    current_prompt = "{user_question}"
    context = {}
    context["user_question"] = final_user_question
    if len(tasks):
        await asyncio.gather(*tasks)

    print(
        f">>>>>>>>>> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} local search : query embedding finished"
    )
    if args.is_use_code:
        code_context = code_graph_rag.final_context
        current_prompt = CHAT_PROMPT_WORKSPACE
        context["entity_context"] = code_context["entity_context"]
        context["class_context"] = code_context["class_context"]
        context["relationship_context"] = code_context["relationship_context"]
        context["community_context"] = code_context["community_context"]
        context["supplementary_context"] = code_context["supplementary_context"]
        context["qa_context"] = code_context["qa_context"]
        context["tech_doc_context"] = code_context["tech_doc_context"]

    if args.is_use_docs:
        docs_context = docs_graph_rag.final_context
        current_prompt = CHAT_PROMPT_DOC
        context["docs_entity_context"] = docs_context["entity_context"]
        context["docs_class_context"] = docs_context["class_context"]
        context["docs_relationship_context"] = docs_context[
            "relationship_context"
        ]
        context["docs_community_context"] = docs_context["community_context"]
        context["docs_supplementary_context"] = docs_context[
            "supplementary_context"
        ]

    metadata = {
        "open_query_split": args.open_query_split,
        "rewrite_q": final_user_question,
        "is_log": is_log,
        "page_list": page_list,
        "sub_query": sub_querys,
        "is_use_docs": args.is_use_docs,
        "is_use_code": args.is_use_code,
        "doc_rerank_entity_ids": (
            docs_graph_rag.rerank_entity_ids if docs_graph_rag else None
        ),
        "doc_rerank_entity_names": (
            docs_graph_rag.rerank_entity_names if docs_graph_rag else None
        ),
        "doc_rerank_prompt": (
            docs_graph_rag.rerank_prompt if docs_graph_rag else None
        ),
        "doc_rerank_result": (
            docs_graph_rag.rerank_result if docs_graph_rag else None
        ),
        "rerank_entity_ids": (
            code_graph_rag.rerank_entity_ids if code_graph_rag else None
        ),
        "rerank_entity_names": (
            code_graph_rag.rerank_entity_names if code_graph_rag else None
        ),
        "rerank_prompt": (
            code_graph_rag.rerank_prompt if code_graph_rag else None
        ),
        "rerank_result": (
            code_graph_rag.rerank_result if code_graph_rag else None
        ),
    }
    if args.is_use_code and args.is_use_docs:
        context["tag_scene"] = metadata['page_list']
        current_prompt = CHAT_PROMPT

    print("RAG Done!")
    prompt_template = ChatPromptTemplate.from_messages(
        [("user", current_prompt)]
    )
    final_prompt = prompt_template.invoke(context).messages[0].content

    return {
        "prompt_template": prompt_template,
        "context": context,
        "final_prompt": final_prompt,
        "metadata": metadata,
    }


async def local_search_without_chat(args: ChatArgs, user_question):
    """
    handle_user_question + rag_without_chat 两步合二为一
    获取 chat 阶段需要的最终的 prompt
    提供给 brain 平台，进行 chat 对话
    """
    query_result = await handle_user_question(
        args=args, user_question=user_question
    )
    final_user_question = query_result.get("final_user_question")
    sub_querys = query_result.get("sub_querys")
    page_list = query_result.get("page_list")
    is_log = query_result.get("is_log")
    result = await rag_without_chat(
        args=args,
        user_question=user_question,
        final_user_question=final_user_question,
        sub_querys=sub_querys,
        page_list=page_list,
        is_log=is_log,
    )
    return result


async def local_search(args: ChatArgs, user_question):
    result = await local_search_without_chat(
        args=args, user_question=user_question
    )
    return await local_chat(result)

async def local_chat(result):
    prompt_template = result["prompt_template"]
    context = result["context"]
    final_prompt = result["final_prompt"]

    parser = StrOutputParser()
    chain = prompt_template | chat_model | parser
    chunks = chain.stream(context)
    return final_prompt, chunks
