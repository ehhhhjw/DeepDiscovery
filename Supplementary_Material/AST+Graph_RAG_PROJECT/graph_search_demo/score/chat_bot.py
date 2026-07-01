import os
import sys
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.services.model_config import chat_model
from src.query import GraphSearch
from src.prompts import CHAT_PROMPT
from src.graph_models import get_tag_extract, get_sub_query_extract
from src.constants import formatted_datetime
from src.constants import ROOT_DIR


async def chat_bot(args, user_question):
    print(f"\n用户提问: {user_question} \n\n")
    result_obj = {}

    output_str = ""
    sub_querys = []
    page_list = []
    is_log = 0
    if args.open_query_split:
        rewrite_q, page_list, is_log = await get_tag_extract(user_question)
        # 问题重写
        if rewrite_q:
            user_question = rewrite_q
        sub_querys = await get_sub_query_extract(user_question)

    graph_rag = GraphSearch(
        query=user_question,
        top_k=args.top_k,
        db_path=args.db_path,
        graph_path=args.graph_path,
        open_rerank=args.open_rerank,
        community_path=args.community_path,
        page_list=page_list,
        is_log=is_log,
        sub_querys=sub_querys,
        is_class_use_code=args.is_class_use_code,
    )
    print("Performing RAG ......")
    context = await graph_rag.get_context()
    context["user_question"] = user_question
    print("RAG Done!")

    prompt_template = ChatPromptTemplate.from_messages([("user", CHAT_PROMPT)])
    parser = StrOutputParser()
    chain = prompt_template | chat_model | parser

    chunks = chain.stream(context)
    result = ""
    for chunk in chunks:
        result += chunk
        sys.stdout.write(chunk)
        sys.stdout.flush()

    result_obj = {
        "rag": prompt_template.invoke(context).messages[0].content,
        "llm": result,
    }
    return result_obj


# params = {
#     "chat": True,
#     "graph_path": ROOT_DIR
#     / "data/v4/code_graph_all_bundle_version20240807.json",
#     "db_path": ROOT_DIR / "chroma_db_all_bundle_version20240807",
#     "community_path": ROOT_DIR
#     / "data/v4/community_reports_all_bundle_version20240807.json",
#     "top_k": 12,
#     "open_rerank": True,
#     "open_query_split": True,
# }
# chat_bot(params)
