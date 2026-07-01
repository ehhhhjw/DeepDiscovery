import os
import json
import copy
import asyncio
import networkx as nx
from langchain_chroma import Chroma
from services.model_config import embedding_model
from constants import (
    EdgeType,
    SearchType,
    ContextType,
    DOCS_COLLECTION_NAMES,
    LOG_DIR_PATH,
)
from utils import (
    num_tokens_from_string,
    get_graph_node_content,
    get_graph_node_content_with_class_code,
    get_graph_node_extract_content,
    get_graph_doc_node_content_with_file,
    save_json_to_file,
    exit_app,
)
from graph_models import get_final_docs_query_entities
from utils.request import HttpClient
from collections import defaultdict
from typing import List, Dict
from datetime import datetime
from utils.load_vector_db import SingletonGetChroma
from utils.load_graph import SingletonLoadGraph

def merge_records_with_average_score(records: List[Dict]) -> List[Dict]:
    merged_results = defaultdict(lambda: {"score_sum": 0, "count": 0})

    # Traverse the list and populate the defaultdict
    for entry in records:
        key = (entry["id"], entry["type"])
        merged_results[key]["score_sum"] += entry["score"]
        merged_results[key]["count"] += 1

    # Calculate average score and store merged records
    final_merged_res = []
    for id_type, data in merged_results.items():
        avg_score = data["score_sum"] / data["count"]
        final_merged_res.append(
            {"id": id_type[0], "score": avg_score, "type": id_type[1]}
        )
    final_merged_res = sorted(final_merged_res, key=lambda x: x["score"])
    return final_merged_res


def calculate_weighted_score(records: List[Dict]) -> List[Dict]:
    weights = {
        "docs_description": 0.4,
        "docs_comment": 0.3,
        "docs_report": 0.2,
        "docs_name": 0.1,
    }
    default_score = 2  # 默认分数为2

    # the scores and types for each id
    accumulated_scores = defaultdict(lambda: {"score": {}, "types": set()})

    # Track scores and types based on id and type
    for record in records:
        id_ = record["id"]
        type_ = record["type"]
        score = record["score"]
        accumulated_scores[id_]["score"][
            type_
        ] = score  # Direct assignment, not accumulation
        accumulated_scores[id_]["types"].add(type_)

    # Calculate weighted score for each id
    final_scores = []
    for id_, data in accumulated_scores.items():
        score_dict = data["score"]
        types = data["types"]
        # Ensure all types are covered, set score to 2 if not present
        for type_ in weights:
            if type_ not in score_dict:
                score_dict[type_] = default_score
        weighted_score = sum(
            score_dict[type_] * weights[type_] for type_ in weights
        )
        types_str = " | ".join(
            sorted(types)
        )  # Create a string with types separated by '|'
        final_scores.append(
            {"id": id_, "score": weighted_score, "type": types_str}
        )
    final_scores = sorted(final_scores, key=lambda x: x["score"])
    return final_scores

class DocGraphSearch:
    """
    Graph Local Search Class
        Args:
            query: User question
            top_k: recall number
            db_path: Path to vector db storage
            graph_path: Path to graph storage
            community_path: Path to community storage
            page_list: Target Information of page_list
            is_log: The Log Type
    """

    def __init__(
        self,
        user_question,
        query,
        top_k,
        sub_top_k,
        open_rerank,
        db_path,
        sub_querys,
        is_use_docs,
        is_use_code,
        docs_graph_path,
        docs_community_path,
        query_embeddings={},
        search_res_fields="",
        stage="",
    ):
        self.user_question = user_question
        self.query = query
        self.top_k = top_k
        self.sub_top_k = sub_top_k
        self.open_rerank = open_rerank
        self.sub_querys = sub_querys or []
        # query_embeddings => {"query": xxx, "sub_query": [ xxx, xxx ]}
        self.query_embeddings = query_embeddings
        all_collections = DOCS_COLLECTION_NAMES
        self.vector_db: dict[str, Chroma] = {}
        for c in all_collections:
            self.vector_db[c] = SingletonGetChroma.get_db(
                collection_name=c,
                persist_directory=db_path,
                embedding_function=embedding_model,
            )
        # node id list (selected entity + corresponding class)
        self.selected_entities = []
        self.rerank_entity_names = []
        self.rerank_entity_ids = []
        self.rerank_prompt = ""
        self.rerank_result = []
        self.token_num = 0
        self.max_tokens = 90 * 1000
        self.current_context = ""
        self.is_use_filter = True
        self.is_ranked = False
        self.is_use_code = is_use_code
        self.is_use_docs = is_use_docs
        self.G: nx.Graph = SingletonLoadGraph.get_code_graph(docs_graph_path)
        self.community = SingletonLoadGraph.get_community(docs_community_path)
        self.search_type = SearchType.DOCS
        self.stage = stage
        self.search_res_fields = search_res_fields
        self.final_context = None
        # 记录检索过程结果
        self.search_res = {
            "recall": {},  # 原问题
            "sub_query": [],  # 子问题
            "merge_avg_recall": [],  # merge
            "weight_recall": [],  # weight
            "final_recall": [],  # final
            "rerank_output": [],  # rerank 的结果
        }

    """
    # 如果录入新的图时则使用此方案充当过滤条件
    def create_filter(IsLog: int, query_page_list: list[int]) -> dict:
        filter_dict = {"IsUtLog": IsLog}
        if query_page_list:
            filter_dict["PageList"] = {"$in": query_page_list}
        return filter_dict
    """

    def create_filter_condition_child(self, child_list: list[int]) -> dict:
        if not len(child_list):
            return None
        filter_dict = {}
        filter_dict["id"] = {"$in": list(child_list)}
        return filter_dict

    def add_new_context(self, new_context):
        exceed_max_token_prompt = "The maximum token limit is exceeded, the following content is omitted."
        if self.token_num >= self.max_tokens:
            self.current_context += exceed_max_token_prompt
            return False
        current_token_num = num_tokens_from_string(new_context)
        if self.token_num + current_token_num >= self.max_tokens:
            self.current_context += exceed_max_token_prompt
            return False
        self.current_context += new_context
        self.token_num += current_token_num
        return True

    async def _query_by_embedding(
        self,
        type,
        top_k,
        query,
        query_embedding,
    ):
        final_result = {}
        tasks = []
        # 使用 with 确保 client 被正确关闭，且复用会话
        async with HttpClient() as client:
            for c in self.table_list:
                if c not in final_result:
                    final_result[c] = []

                filter_condition = {}
                if self.is_use_filter:
                    if c == "docs_report":
                        filter_condition = {"type": {"$eq": "file"}}
                    else:
                        filter_condition = {"type": {"$ne": "file"}}

                # commit 的差异在服务端已经处理
                # 单个的异步任务。存储结果到 final_result
                async def task_item_fn(collection_name):
                    # start_time = datetime.now().timestamp()
                    # print(
                    #     f"===================>  query one embedding start query={query} collection_name={collection_name} time:{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }")
                    params = {
                        "collection_name": collection_name,
                        "query_embedding": query_embedding,
                        "filter_condition": (
                            filter_condition
                        ),
                        "top_k": top_k,
                        "min_score": 2,
                        "search_type":SearchType.DOCS
                    }
                    url = os.environ.get(
                        "http_rag_search_url",
                        "http://127.0.0.1:5001/v1/local/query",
                    )
                    response = await client.request(
                        method="POST", url=url, json=params
                    )
                    list_data = []
                    if response["status"] == 200 and "list" in response["data"]:
                        list_data = response["data"].get("list", [])
                    # finish_time = datetime.now().timestamp()
                    # print(f"===================>  query one embedding finish query={query} collection_name={collection_name} time:{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }   耗时:{finish_time - start_time}")
                    final_result[collection_name] = list_data

                tasks.append(task_item_fn(c))
            await asyncio.gather(*tasks)
        return final_result

    async def query_entity_by_embedding(self):
        print("RAG RECALL SCORE: \n")
        if not (
            "query" in self.query_embeddings
            and "sub_query" in self.query_embeddings
        ):
            raise Exception("未找到 query embeddings 结果")
        start_time = datetime.now().timestamp()
        print(f">>>>>>>>>> doc query embedding start currtime:{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }")
        recall_future = self._query_by_embedding(
            query=self.query,
            query_embedding=self.query_embeddings["query"],
            top_k=self.top_k * 2,
            type="query",
        )
        # 并发执行子查询
        sub_query_futures = [
            self._query_by_embedding(
                query=self.sub_querys[i],
                query_embedding=self.query_embeddings["sub_query"][i],
                top_k=self.sub_top_k,
                type="sub_query",
            )
            for i in range(len(self.sub_querys))
        ]
        # 并行等待所有查询的结果
        results = await asyncio.gather(recall_future, *sub_query_futures)
        finish_time = datetime.now().timestamp()
        print(f">>>>>>>>>>  doc query embedding finish , currtime:{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') } 耗时time:{finish_time - start_time}")

        # 处理第一个主要查询的结果
        self.search_res["recall"] = results[0]
        # 处理子查询的结果
        for i, result in enumerate(results[1:]):
            self.search_res["sub_query"].append(
                {"query": self.sub_querys[i], "recall": result}
            )

        final_res = []
        for items in results:
            for key,values in items.items():
                final_res.extend(values)
        
        # 1：按照类型合并相同id的记录并计算平均分数
        merged_records = merge_records_with_average_score(final_res)
        for item in merged_records:
            self.search_res["merge_avg_recall"].append({"id": item["id"], "score": item["score"], "type": item["type"], "name": self.G.nodes[item["id"]]['name']})

        # 2：汇总所有类型的分数并按权重计算最终结果
        final_weighted_res = calculate_weighted_score(merged_records)
        for item in final_weighted_res:
            self.search_res["weight_recall"].append({"id": item["id"], "score": item["score"], "type": item["type"], "name": self.G.nodes[item["id"]]['name']})

        print(f">>>>>>>>>> doc Final Ranking: currtime:{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') } \n")
        final_weighted_res = sorted(
            final_weighted_res, key=lambda x: x["score"]
        )
        for i in range(
            min(int(self.top_k * 1.5), len(final_weighted_res))
        ):
            item = final_weighted_res[i]
            # 已经存在直接忽略
            if item["id"] in self.selected_entities:
                continue
            self.selected_entities.append(item["id"])
            self.search_res["final_recall"].append(
                {"id": item["id"], "score": item["score"], "type": item["type"], "name": self.G.nodes[item["id"]]['name']})
            print(
                f"ID: {self.G.nodes[item['id']]['name']} score: {item['score']} search_type: {item['type']}"
            )
        print("\n\n")

    # 通过
    async def filter_selected_entities_by_llm(
        self, context, selected_entities, search_type=SearchType.DOCS
    ):
        """
        针对 query_entity_by_embedding 的结果
        利用大模型对 self.selected_entities 进行一次筛选
        """
        context["user_question"] = self.query
        rerank_entity_ids, rerank_prompt, rerank_result = (
            await get_final_docs_query_entities(
                doc_graph_nodes=(
                    self.G.nodes
                ),
                user_question=self.query,
                entity_ids=selected_entities,
                search_type=search_type,
                child_questions=self.sub_querys,
            )
        )

        selected_entity_names = []
        print(f"\nFinal {search_type} rerank result ( By LLM ): \n")
        # 打印日志
        for i in range(len(rerank_entity_ids)):
            node_id = rerank_entity_ids[i]
            node_name = self.G.nodes[node_id]["name"]
            selected_entity_names.append(node_name)
            self.search_res["rerank_output"].append(node_name)
            print(f"ID: {node_name}")
        print("\n\n")
        return (
            rerank_entity_ids,
            selected_entity_names,
            rerank_prompt,
            rerank_result,
            search_type,
        )

    async def execute_local_search(self):
        """
        混合检索（代码 + 文档）参数适配层
        """
        print(
            f">>>>>>>>>> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} doc 开始进行RAG召回"
        )
        self.is_ranked = False
        self.max_tokens = 20 * 1000 if self.is_use_code else 90 * 1000
        self.table_list = DOCS_COLLECTION_NAMES
        self.selected_entities = []
        docs_context = await self.get_context()
        docs_selected_entities = copy.deepcopy(self.selected_entities)

        if self.open_rerank:
            tasks = []
            if len(docs_selected_entities) > 0:
                tasks.append(
                    self.filter_selected_entities_by_llm(
                        docs_context, docs_selected_entities, SearchType.DOCS
                    )
                )
            start_time = datetime.now().timestamp()
            print(
                f">>>>>>>>>> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} doc 开始进行rerank"
            )
            results = await asyncio.gather(*tasks)
            finish_time = datetime.now().timestamp()
            print(
                f">>>>>>>>>> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} doc rerank结束  耗时time:{finish_time - start_time}"
            )
            for result in results:
                (
                    selected_entity_ids,
                    selected_entity_names,
                    selected_prompt,
                    selected_result,
                    search_type,
                ) = result
                self.selected_entities = copy.deepcopy(selected_entity_ids)
                self.rerank_entity_names = selected_entity_names
                self.rerank_entity_ids = selected_entity_ids
                self.rerank_prompt = selected_prompt
                self.rerank_result = selected_result
                self.is_ranked = True
                self.should_exit_and_save_json("rerank")
                docs_context = self.get_all_context_from_query(
                    type=ContextType.CHAT
                )
        self.final_context = docs_context
        print(
            f">>>>>>>>>> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} doc RAG结束"
        )
        self.save_rerank_output_json()

    async def get_context(self):
        """
        Return context of graph search
        """
        self.get_graph_node_content = get_graph_node_content
        await self.query_entity_by_embedding()
        self.should_exit_and_save_json("rag")

        context = self.get_all_context_from_query(type=ContextType.CHAT)
        return context

    def get_all_context_from_query(self, type=ContextType.CHAT):
        __get_graph_node_content = self.get_graph_node_content
        if type == ContextType.RERANK:
            self.get_graph_node_content = get_graph_node_extract_content
        self.token_num = 0

        entity_context = self.get_doc_entity_context(type=type)
        class_context = self.get_class_context()
        relationship_context, node_list_1 = self.get_relationship_context()
        community_context, node_list_2 = self.get_community_context()
        supplementary_context = self.get_supplementary_context(
            list(set(node_list_1 + node_list_2))
        )
        self.get_graph_node_content = __get_graph_node_content
        return {
            "entity_context": entity_context,
            "class_context": class_context,
            "relationship_context": relationship_context,
            "community_context": community_context,
            "supplementary_context": supplementary_context,
        }

    def get_doc_entity_context(self, type=ContextType.CHAT):
        self.current_context = ""

        for node_id in self.selected_entities:
            current_node = self.G.nodes[node_id]
            new_context = get_graph_doc_node_content_with_file(
                id=node_id, node=current_node
            )
            isSuccess = self.add_new_context(new_context)
            if not isSuccess:
                break
        return self.current_context

    def get_entity_context(self, type=ContextType.CHAT):
        self.current_context = ""
        # chat 的时候，使用 补充 class 原文件 的召回方式
        _get_graph_node_content = (
            get_graph_node_content
            if type == ContextType.RERANK
            else get_graph_node_content_with_class_code
        )
        for node_id in self.selected_entities:
            current_node = self.G.nodes[node_id]
            new_context = f"ID: {node_id}\nEntity Name: {current_node['name']}\nType:{current_node['type']}\n{('Code Path: ' + current_node['path']) if 'path' in current_node else ''}\n{_get_graph_node_content(node=current_node, type=self.search_type)}\n\n"
            isSuccess = self.add_new_context(new_context)
            if not isSuccess:
                break
        return self.current_context

    def get_class_context(self):
        self.current_context = ""
        is_add = {}
        for node_id in self.selected_entities:
            current_node = self.G.nodes[node_id]
            # 检索出来的 entity 就是 class，直接取即可
            if not current_node["is_leaf"]:
                if node_id in is_add:
                    continue
                is_add[node_id] = 1
                new_context = f"### File ID: {node_id}\n    File Name: {current_node['name']}\n{self.get_graph_node_content(node=current_node, type=self.search_type)}\n\n"
                isSuccess = self.add_new_context(new_context)
                if not isSuccess:
                    break
                continue
            edge_list = list(self.G.out_edges(node_id)) + list(
                self.G.in_edges(node_id)
            )
            for edge in edge_list:
                edge_type = self.G.edges[edge]["type"]
                if EdgeType.CHILD not in edge_type:
                    continue
                isSuccess = True
                for candidate_node_id in [edge[0], edge[1]]:
                    candidate_node = self.G.nodes[candidate_node_id]
                    if (
                        not candidate_node["is_leaf"]
                        and candidate_node_id not in is_add
                    ):
                        is_add[candidate_node_id] = 1
                        new_context = f"### File ID: {candidate_node_id}\n    File Name: {candidate_node['name']}\n{self.get_graph_node_content(node=candidate_node, type=self.search_type)}\n\n"
                        isSuccess = (
                            self.add_new_context(new_context) and isSuccess
                        )
                if not isSuccess:
                    break
        self.selected_entities += list(is_add.keys())
        self.selected_entities = list(set(self.selected_entities))
        return self.current_context if len(self.current_context) > 0 else "null"

    def query_embedding_by_child_relationship(self, parent_node):
        edge_list = list(self.G.out_edges(parent_node))
        is_add = list(self.selected_entities)
        child_ids = []

        for edge in edge_list:
            edge_type = self.G.edges[edge]["type"]
            if EdgeType.CHILD not in edge_type:
                continue
            for candidate_node_id in [edge[0], edge[1]]:
                candidate_node = self.G.nodes[candidate_node_id]
                if (
                    candidate_node["is_leaf"]
                    and candidate_node_id not in is_add
                ):
                    is_add.append(candidate_node_id)
                    child_ids.append(candidate_node_id)

        supplementary_entity_ids = []
        relation_entity_context = ""
        if len(child_ids) != 0:
            vertor_db = self.vector_db["docs_description"]

            # 在主集合中进行相似性搜索时添加过滤条件
            filter_dict = self.create_filter_condition_child(child_ids)

            recall = (
                vertor_db.similarity_search_by_vector_with_relevance_scores(
                    embedding=self.query_embeddings["query"],
                    k=3,
                    filter=filter_dict,
                )
            )
            recall = sorted(recall, key=lambda x: x[1])

            threshold = 1.3
            for entity, score in recall:
                if score > threshold:
                    continue
                entity_id = entity.metadata["id"]
                current_node = self.G.nodes[entity_id]
                print(f"ID: {self.G.nodes[entity_id]['name']}, SCORE: {score}")
                relation_entity_context += get_graph_doc_node_content_with_file(
                    id=entity_id, node=current_node
                )
                supplementary_entity_ids.append(entity_id)
        return relation_entity_context, supplementary_entity_ids

    def get_relationship_context(self):
        self.current_context = ""
        node_list = []
        for node_id in self.selected_entities:
            edge_list = list(self.G.out_edges(node_id)) + list(
                self.G.in_edges(node_id)
            )
            for edge in edge_list:
                edge_type = self.G.edges[edge]["type"]
                if EdgeType.CHILD in edge_type:
                    continue
                source_node = self.G.nodes[edge[0]]["name"]
                target_node = self.G.nodes[edge[1]]["name"]
                node_list.append(edge[0])
                node_list.append(edge[1])
                edge_description = edge_type
                if edge_type == EdgeType.DEPENDENT:
                    edge_description = "depends on"
                    self.current_context += (
                        f"{source_node} {edge_description} {target_node}\n"
                    )
                elif edge_type == EdgeType.EXTENDS:
                    edge_description = "extends from"
                    self.current_context += (
                        f"{source_node} {edge_description} {target_node}\n"
                    )
                elif edge_type == EdgeType.CALL:
                    edge_description = "calls"
                    self.current_context += (
                        f"{source_node} {edge_description} {target_node}\n"
                    )
                elif "relative" in edge_type:
                    # 提取关键词
                    keywords = (
                        edge_description.split(":")[1].strip().split(", ")
                    )
                    self.current_context += f"##File <{source_node}> and File <{target_node}> are relative by keywords: {', '.join(keywords)}\n"

        return self.current_context, list(set(node_list))

    def get_community_context(self):
        self.current_context = ""
        is_add = {}
        node_list = []
        for node_id in self.selected_entities:
            community_id = self.G.nodes[node_id]["community_id"]
            if community_id == -1:
                continue
            community_id = str(community_id)
            if community_id not in is_add:
                is_add[community_id] = 1
            else:
                is_add[community_id] = is_add[community_id] + 1

        # 按值排序并获取 top3
        top_communities = sorted(
            is_add.items(), key=lambda item: item[1], reverse=True
        )[:3]

        print("Top 3 communities:")
        for community_id, count in top_communities:
            print(f"Community {community_id}: {count} Entities")
            node_list += self.community[community_id]["nodes"]
            new_context = f"##Community ID: {community_id}\n Community Node List: {','.join([self.G.nodes[node_id]['name'] for node_id in self.community[community_id]['nodes']])}\n Community Description: {self.community[community_id]['reports']}\n\n"
            isSuccess = self.add_new_context(new_context)
            if not isSuccess:
                break

        return self.current_context, list(set(node_list))

    def get_supplementary_context(self, node_list):
        self.current_context = ""
        for node_id in node_list:
            if node_id in self.selected_entities:
                continue
            node = self.G.nodes[node_id]

            new_context = ""
            if not self.is_ranked:
                query_context, supplementary_entity_ids = (
                    self.query_embedding_by_child_relationship(node_id)
                )
                if query_context != "":
                    print(
                        f">>>>>> begin search_with_score_vector_db: {self.G.nodes[node_id]['name']}"
                    )
                    new_context = f"\n\n##  File ID: {node_id}\n    File Name: {node['name']}\n    Type: {node['type']}\n{self.get_graph_node_content(node=node, type=self.search_type)}"
                    new_context += query_context
                    self.selected_entities = (
                        self.selected_entities + supplementary_entity_ids
                    )

            if new_context != "":
                isSuccess = self.add_new_context(new_context)
                if not isSuccess:
                    break

        return self.current_context

    # 输出结构化日志数据
    def save_rerank_output_json(self):
        log_path = LOG_DIR_PATH / f"docs_output.json"
        if not log_path.exists():
            # 确保父目录存在
            log_path.parent.mkdir(exist_ok=True, parents=True)
            log_path.touch()
        data = {
            "query_info": {
                "user_question": self.user_question,
                "query": self.query,
                "search_type": self.search_type,
                "top_k": self.top_k,
                "sub_top_k": self.sub_top_k,
                "open_rerank": self.open_rerank,
                "sub_querys": self.sub_querys,
            },
            **self.search_res,
        }
        save_json_to_file(data, log_path, self.search_res_fields)

    def should_exit_and_save_json(self, stage):
        if self.stage == stage:
            # 如果限制执行阶段，退出并保存数据
            self.save_rerank_output_json()
            exit_app(stage)