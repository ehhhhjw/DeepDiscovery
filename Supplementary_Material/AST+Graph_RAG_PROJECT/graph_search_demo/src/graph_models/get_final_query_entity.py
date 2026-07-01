from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser 

from prompts.doc.ajx_doc_entity_rank import ajx_final_entity_rank
from services.model_config import rerank_model, chat_model
from prompts.final_query_entity_extract import final_entity_rank_prompts
from constants import SearchType, LOG_DIR_PATH
import os
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List
import json
from utils.utils import write_text_to_log, get_graph_doc_node_content_with_file, get_graph_doc_node_content_for_rank
import time

class RERANK_POINT(BaseModel):
    node_id: int = Field(description="Entity/Class/Supplementary id")
    node_name: str = Field(description="Entity/Class/Supplementary name")
    # reason: str = Field(description="选择原因")
    score: int = Field(description="选择分数")


class RERANK_PointsData(BaseModel):
    points: List[RERANK_POINT] = Field(
        description="List of points containing output details."
    )


async def stream_output(chain, prompt_input):
    res = None
    async for chunk in chain.astream(prompt_input):
        res = chunk
    return res


async def get_final_query_entities(
    user_question, graph_nodes, context, search_type
):
    context = {**context, "user_question": user_question}
    parser = JsonOutputParser(pydantic_object=RERANK_PointsData)

    if search_type == SearchType.DOCS:
        final_entity_rank = ajx_final_entity_rank
    else:
        final_entity_rank = final_entity_rank_prompts

    prompt_template = PromptTemplate(
        template=final_entity_rank,
        input_variables=[
            "entity_context",
            "class_context",
            "relationship_context",
            "community_context",
            "supplementary_context",
            "user_question",
        ],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        },
    )
    print(f"\n>>>>>> 正在努力对 {search_type} 进行 RERANK,请耐心等待…… \n")
    timeStart = time.time()
    # chain = prompt_template | rerank_model | parser
    chain = prompt_template | chat_model | parser
    result = await stream_output(chain, context)
    output_str = prompt_template.invoke(context).text
    elapsed_time = time.time() - timeStart
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    write_text_to_log(
        f"""\n{output_str}\n\n******************************************  LLM 结果 ***********************************************\n{json.dumps(result, indent=4, ensure_ascii=False)}\n""",
        f"{search_type}_rerank.txt",
    )
    item_list = result["points"]
    item_list = [
        item for item in item_list if ("score" in item and "node_name" in item)
    ]
    item_list = sorted(item_list, key=lambda x: -x["score"])

    final_name_list = [item["node_name"] for item in item_list]
    print(f"\n>>>>>> final_name_list of {search_type}: {final_name_list}\n")

    # final_id_list = list(set([item["node_id"] for item in item_list]))
    # print(f"\n>>>>>> final_id_list: {final_id_list}\n")

    # 通过 name 找到对应的实体，模型返回的 id 可能是错误的
    final_id_map = {}
    for node_id in graph_nodes:
        node_item = graph_nodes[node_id]
        node_name = node_item["name"]
        if node_name in final_name_list and node_name not in final_id_map:
            final_id_map[node_name] = node_id

    if len(final_id_map) > 0:
        # (entity_ids, rerank_prompt, rerank_result)
        return (
            [
                int(final_id_map[name])
                for name in final_name_list
                if name in final_id_map
            ],
            output_str,
            result,
        )
    raise Exception(
        "rerank_error, 未匹配到有效的 rerank 实体, 请联系管理员排查"
    )


async def get_final_docs_query_entities(
    user_question,
    entity_ids: list,
    doc_graph_nodes,
    search_type,
    child_questions,
):
    parser = JsonOutputParser(pydantic_object=RERANK_PointsData)

    rank_context = ''
    final_entity_ids = []
    filter_file_ids = ["Button_QA", "ButtonGroup_QA"]
    for node_id in entity_ids:
        node_item = doc_graph_nodes[node_id]
        if node_item["is_leaf"] and all(
            not node_item["name"].startswith(prefix)
            for prefix in filter_file_ids
        ):
            final_entity_ids.append(node_id)
            rank_context += get_graph_doc_node_content_for_rank(
                id=node_id, node=node_item, graph_nodes=doc_graph_nodes
            )

    context = {
        "rank_context": rank_context,
        "user_question": user_question,
        "child_questions": child_questions,
        "entity_ids": final_entity_ids,
    }
    final_entity_rank = ajx_final_entity_rank
    prompt_template = PromptTemplate(
        template=final_entity_rank,
        input_variables=[
            "rank_context",
            "user_question",
            "child_questions",
            "entity_ids",
        ],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        },
    )

    print(f"\n>>>>>> 正在努力对 {search_type} 进行 RERANK,请耐心等待…… \n")
    timeStart = time.time()
    chain = prompt_template | chat_model | parser
    result = await stream_output(chain, context)
    output_str = prompt_template.invoke(context).text
    elapsed_time = time.time() - timeStart
    print(f"Docs rank elapsed time: {elapsed_time:.2f} seconds")

    write_text_to_log(
        f"""\n{output_str}\n\n******************************************  LLM 结果 ***********************************************\n{json.dumps(result, indent=4, ensure_ascii=False)}\n""",
        f"{search_type}_rerank.txt",
    )

    item_list = result["points"]

    item_list = [
        item
        for item in item_list
        if ("score" in item and "node_id" in item)
    ]
    item_list = sorted(item_list, key=lambda x: -x["score"])

    final_ranked_ids = [int(item["node_id"]) for item in item_list]

    final_ids_list = []
    filter_file_ids = ["Button_QA", "ButtonGroup_QA"]
    for node_id in final_ranked_ids:
        node_item = doc_graph_nodes[node_id]
        if (
            node_id not in final_ids_list
            and node_item["is_leaf"]
            and all(
                not node_item["name"].startswith(prefix)
                for prefix in filter_file_ids
            )
        ):
            final_ids_list.append(node_id)

    return final_ids_list, output_str, result