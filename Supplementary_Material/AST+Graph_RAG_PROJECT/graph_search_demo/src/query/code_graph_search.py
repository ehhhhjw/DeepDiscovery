import json
import os
import asyncio
import networkx as nx
import queue
from datetime import datetime
from constants import (
    TECH_DOC_COLLECTION_NAMES,
    QAINFO_NAMES,
    EdgeType,
    SearchType,
    ContextType,
    local_search_settings,
    code_find_layer_depth,
    FindType,
    LOG_DIR_PATH,
    COMMIT_COLLECTION_NAMES,
    RAG_STRATEGY,
)
from utils import (
    num_tokens_from_string,
    get_graph_node_content,
    get_graph_node_content_with_class_code,
    get_graph_node_content_without_description,
    get_graph_node_extract_content,
    get_layer_nodes,
    save_json_to_file,
    exit_app,
)
from graph_models import get_final_query_entities
from .qa_graph_search import QAGraphSearch
from .tech_doc_graph_search import TechDocGraphSearch
from utils.code_search import (
    gen_hybrid_result,
    gen_final_result,
)
from utils.hybrid_plus_search import hybrid_plus_search
from utils.request import HttpClient
from utils.load_graph import SingletonLoadGraph


class CodeGraphSearch:
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
        open_rerank,
        db_path,
        graph_path,
        community_path,
        table_list,
        sub_querys=[],
        page_list=[],
        is_log=None,
        search_type=SearchType.CODE,
        max_tokens=10 * 1000,
        query_embeddings={},
        score_limit=None,
        sub_score_limit=None,
        is_local_tokens_limit_enabled=False,
        is_use_qa=False,
        is_use_tech_doc=False,
        search_res_fields="",
        stage="",
    ):
        self.user_question = user_question
        self.query = query
        self.top_k = max(top_k, 4)  # top_k 最小为4
        self.sub_top_k = int(
            min(len(sub_querys) / (len(sub_querys) + 1), 3 / 4) * top_k
        )  # 子问题的召回数量
        self.query_top_k = top_k - self.sub_top_k  # 用户问题的召回数量
        # 关键字召回的数量取 top_k 的 1/5 - math.ceil(self.top_k / 5) 关闭bm25设置为0
        self.bm25_top_k = 7
        self.open_rerank = open_rerank
        self.sub_querys = sub_querys
        # query_embeddings => {"query": xxx, "sub_query": [ xxx, xxx ]}
        self.query_embeddings = query_embeddings
        self.is_use_filter = search_type == SearchType.CODE  # code 的时候才过滤
        self.table_list = table_list  # 基础字段
        # node id list (selected entity + corresponding class)
        self.selected_entities = []
        # 选中实体的补充信息
        self.selected_entities_extra_info = {}
        self.db_path = db_path
        self.token_num = 0
        self.max_tokens = max_tokens
        self.current_context = ""
        self.is_local_tokens_limit_enabled = is_local_tokens_limit_enabled
        self.is_use_qa = is_use_qa
        self.is_use_tech_doc = is_use_tech_doc
        self.community = {}
        self.stage = stage
        self.search_res_fields = search_res_fields
        # 记录检索过程结果
        self.search_res = {
            "recall": {},  # 原问题 embedding 召回
            "sub_query": [],  # 子问题 embedding 召回 # 每个 item 对应 {"query": self.sub_querys[i], "recall": result}
            "bm25_recall": {},  # 原问题 bm25 召回
            "bm25_sub_query": [],  # 子问题 bm25 召回
            "final_embedding_recall": [],  # embedding 最终召回
            "final_bm25_recall": [],  # bm25 最终召回
            "final_recall": [],  # embedding + bm25 最终召回
            "rerank_entity_in_context": [],  # final_recall 进入到 rerank 窗口的实体
            "rerank_community_in_context": [],  # 进入到 rerank窗口的 community
            "chat_entity_in_context": [],  # final_recall or final_rerank_entity 进入到 chat 窗口的实体
            "chat_community_in_context": [],  # 进入到 chat 窗口的 community
            "rerank_input": [],  # rerank 的实体输入
            "rerank_output": [],  # rerank 的结果
        }

        self.G: nx.Graph = SingletonLoadGraph.get_code_graph(
            graph_path=graph_path
        )
        # self.community = SingletonLoadGraph.get_community(
        #     community_path=community_path
        # )

        self.search_type = search_type
        # 初始化过滤条件
        self.filter_condition = (
            self.create_filter_condition(
                self.get_this_query_target_id_list(is_log, page_list)
            )
            if self.is_use_filter
            else {}
        )
        self.score_limit = score_limit
        self.sub_score_limit = sub_score_limit
        self.final_context = None
        self.qa_context = None
        self.rerank_entity_names = None
        self.rerank_entity_ids = None
        self.rerank_prompt = None
        self.rerank_result = None

    def create_filter_condition(self, filter_ids: list[int]) -> dict:
        """
        Chroma_db 过滤条件, is_log + page_list
        """
        # 空 [] or None
        if not filter_ids:
            return None
        return {
            "id": {"$nin": list(filter_ids)},
        }

    def get_this_query_target_id_list(
        self, need_log: int, query_page_list: list[int]
    ):
        """
        根据 pageList 进行数据过滤
        """
        # 不需要过滤
        if not len(query_page_list) and need_log == 1:
            return None
        filter_id_list = []
        for son_node in self.G.nodes:
            list1 = set(query_page_list)
            list2 = set(self.G.nodes[son_node]["pageList"])
            # isLog => 1-保留log文件 0-过滤log文件
            if (query_page_list and not (list1 & list2)) or (
                need_log == 0 and self.G.nodes[son_node]["isLog"] == 1
            ):
                filter_id_list.append(son_node)
        return filter_id_list

    def add_new_context(self, new_context, current_max_tokens=0):
        exceed_max_token_prompt = "The maximum token limit is exceeded, the following content is omitted."
        if self.token_num >= self.max_tokens:
            self.current_context += exceed_max_token_prompt
            return False
        current_token_num = num_tokens_from_string(new_context)
        # 如果开启了每块内容的 tokens 单独限制，先进行区块的校验
        if (
            self.is_local_tokens_limit_enabled
            and current_max_tokens > 0
            and self.current_token_num + current_token_num >= current_max_tokens
        ):
            self.current_context += exceed_max_token_prompt
            return False
        if self.token_num + current_token_num >= self.max_tokens:
            self.current_context += exceed_max_token_prompt
            return False
        self.current_context += new_context
        self.current_token_num += current_token_num
        self.token_num += current_token_num
        return True

    async def _query_by_bm25(
        self,
        top_k,
        query,
        query_embedding=None,
    ):
        """
        BM25 召回
        """
        final_result = {}
        tasks = []
        async with HttpClient() as client:
            for c in self.table_list:
                if c not in final_result:
                    final_result[c] = []

                # commit 的差异在服务端已经处理
                # 单个的异步任务。存储结果到 final_result
                async def task_item_fn(collection_name):
                    params = {
                        "collection_name": collection_name,
                        "query": query,
                        "filter_condition": (
                            self.filter_condition
                            if collection_name not in COMMIT_COLLECTION_NAMES
                            else None
                        ),
                        "top_k": top_k,
                        "min_score": None,
                    }
                    url = (
                        os.environ.get(
                            "http_rag_search_url",
                            "http://127.0.0.1:5001/v1/local/query",
                        )
                        + "/bm25"
                    )
                    response = await client.request(
                        method="POST", url=url, json=params
                    )
                    list_data = []
                    if response["status"] == 200 and "list" in response["data"]:
                        list_data = response["data"].get("list", [])
                    final_result[collection_name] = list_data

                tasks.append(task_item_fn(c))
            await asyncio.gather(*tasks)
        return final_result

    async def query_entity_by_bm25(self):
        # 如果 bm25_top_k 为 0 不进行检索召回
        if self.bm25_top_k <= 0:
            return
        print("\n\nBM25 RECALL SCORE: \n")

        recall_future = self._query_by_bm25(
            query=self.query,
            query_embedding=None,
            top_k=self.bm25_top_k,
        )

        # 保存 embedding query 结果的结构化数据
        sub_query_len = len(self.sub_querys)

        sub_query_futures = [
            self._query_by_bm25(
                query=self.sub_querys[i],
                query_embedding=None,
                top_k=self.bm25_top_k,
            )
            for i in range(sub_query_len)
        ]

        results = await asyncio.gather(recall_future, *sub_query_futures)

        self.search_res["bm25_recall"] = results[0]
        sub_results = results[1:]
        self.search_res["bm25_sub_query"] = [
            {"query": self.sub_querys[i], "recall": sub_results[i]}
            for i in range(len(sub_results))
        ]

    async def _query_by_embedding(
        self,
        type,
        top_k,
        query,
        query_embedding,
    ):
        final_result = {}
        tasks = []
        score_limit = (
            self.score_limit if type == "query" else self.sub_score_limit
        )
        # 使用 with 确保 client 被正确关闭，且复用会话
        async with HttpClient() as client:
            for c in self.table_list:
                if c not in final_result:
                    final_result[c] = []

                # commit 的差异在服务端已经处理
                # 单个的异步任务。存储结果到 final_result
                async def task_item_fn(collection_name):
                    params = {
                        "collection_name": collection_name,
                        "query_embedding": query_embedding,
                        "filter_condition": (
                            self.filter_condition
                            if collection_name not in COMMIT_COLLECTION_NAMES
                            else None
                        ),
                        "top_k": top_k,
                        "min_score": score_limit[collection_name],
                        "search_type":SearchType.CODE
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
                    final_result[collection_name] = list_data

                tasks.append(task_item_fn(c))
            await asyncio.gather(*tasks)
        return final_result

    async def query_entity_by_embedding(self):
        print("\n\nRAG RECALL SCORE: \n")
        if not ("query" in self.query_embeddings):
            # query_embeddings => {"query": xxx, "sub_query": [ xxx, xxx ]}
            raise Exception("未找到 query embeddings 结果")
        start_time = datetime.now().timestamp()
        print(f">>>>>>>>>> code query embedding start currtime:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # 保存 embedding query 结果的结构化数据
        sub_query_len = len(self.query_embeddings["sub_query"])
        print("\nself.sub_querys: ", len(self.sub_querys), sub_query_len)

        recall_future = self._query_by_embedding(
            query=self.query,
            query_embedding=self.query_embeddings["query"],
            top_k=self.top_k,
            type="query",
        )
        # 并发执行子查询
        sub_query_futures = [
            self._query_by_embedding(
                query=self.sub_querys[i],
                query_embedding=self.query_embeddings["sub_query"][i],
                top_k=self.top_k,
                type="sub_query",
            )
            for i in range(len(self.sub_querys))
        ]
        # 并行等待所有查询的结果
        results = await asyncio.gather(recall_future, *sub_query_futures)
        finish_time = datetime.now().timestamp()
        print(
            f">>>>>>>>>>  code query embedding finish , currtime:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 耗时time:{finish_time - start_time}")
        # 处理第一个主要查询的结果
        self.search_res["recall"] = results[0]
        # 处理子查询的结果
        for i, result in enumerate(results[1:]):
            self.search_res["sub_query"].append(
                {"query": self.sub_querys[i], "recall": result}
            )

    def gen_final_recall_selected_entities(self):
        """
        召回数据最终处理, 包含 embedding、bm25召回的数据
        过滤、去重等
        """
        # 生成最终的数据, 已经是排序好的了
        rag_strategy = RAG_STRATEGY.hybrid_plus
        final_res = []
        if rag_strategy == RAG_STRATEGY.hybrid_plus:
            final_res = hybrid_plus_search(
                nodes=self.G.nodes,
                search_res=self.search_res,
                top_k=self.top_k,
                query_top_k=self.query_top_k,
                sub_top_k=self.sub_top_k,
                bm25_top_k=self.bm25_top_k,
            )

        elif rag_strategy == RAG_STRATEGY.hybrid_normal:
            final_res = gen_final_result(
                search_res=self.search_res,
                top_k=self.top_k,
                query_top_k=self.query_top_k,
                sub_top_k=self.sub_top_k,
                bm25_top_k=self.bm25_top_k,
            )
        else:
            final_res = gen_hybrid_result(
                search_res=self.search_res,
                top_k=self.top_k,
                query_top_k=self.query_top_k,
                sub_top_k=self.sub_top_k,
                bm25_top_k=self.bm25_top_k,
            )
        # 存储最终的召回结果
        self.search_res["final_recall"] = final_res
        print("\nFinal Ranking: \n")
        for i in range(len(final_res)):
            final_res_item = final_res[i]
            final_res_item_id = final_res_item["id"]
            self.search_res["rerank_input"].append(final_res_item)
            self.selected_entities.append(final_res_item_id)
            # 记录添加实体的补充信息
            if "extra" in final_res_item:
                if final_res_item_id not in self.selected_entities_extra_info:
                    self.selected_entities_extra_info[final_res_item_id] = {}
                current_dict = self.selected_entities_extra_info[
                    final_res_item_id
                ]
                for key, value in final_res_item["extra"].items():
                    # 每一个字段使用 list 存储
                    if key not in current_dict:
                        current_dict[key] = []
                    current_dict[key].append(value)

            print(
                f"ID: {self.G.nodes[final_res_item_id]['name']} score: {final_res_item['score']} search_type: {final_res_item['type']}"
            )
        print("\n\n")
        pass

    # 通过
    async def filter_selected_entities_by_llm(self, context):
        """
        针对 query_entity_by_embedding 的结果
        利用大模型对 self.selected_entities 进行一次筛选
        """
        if not len(self.selected_entities):
            return
        rerank_entity_ids, rerank_prompt, rerank_result = (
            await get_final_query_entities(
                graph_nodes=self.G.nodes,
                user_question=self.query,
                context={**context, "user_question": self.query},
                search_type=self.search_type,
            )
        )
        # 重置为 rerank 后的 selected_entities
        self.selected_entities = rerank_entity_ids

        selected_entity_names = []
        print(f"\nFinal {self.search_type} rerank result ( By LLM ): \n")
        # 打印日志
        for i in range(len(rerank_entity_ids)):
            node_id = rerank_entity_ids[i]
            node_name = self.G.nodes[node_id]["name"]
            selected_entity_names.append(node_name)
            self.search_res["rerank_output"].append(node_name)
            print(f"ID: {node_name}")
        print("\n\n")
        self.rerank_entity_names = selected_entity_names
        self.rerank_entity_ids = rerank_entity_ids
        self.rerank_prompt = rerank_prompt
        self.rerank_result = rerank_result

    async def execute_local_search(self):
        """
        混合检索（代码 + 文档）参数适配层
        """
        context = {}

        print(
            f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } code 开始进行RAG召回"
        )
        if self.open_rerank:
            context = await self.get_context_with_rerank()
        else:
            context = await self.get_context()
        self.final_context = context
        print(
            f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } code RAG结束"
        )
        # rerank 结束后，保存结构化数据
        self.save_rerank_output_json()

    async def get_context(self):
        """
        Return context of graph search
        """
        self.get_graph_node_content = get_graph_node_content
        await asyncio.gather(
            self.query_entity_by_embedding(), self.query_entity_by_bm25()
        )
        self.gen_final_recall_selected_entities()
        context = self.get_all_context_from_query(ContextType.CHAT)
        return context

    async def get_context_with_rerank(self):
        self.get_graph_node_content = get_graph_node_extract_content
        await asyncio.gather(
            self.query_entity_by_embedding(), self.query_entity_by_bm25()
        )
        self.gen_final_recall_selected_entities()
        self.should_exit_and_save_json("rag")
        rerank_context = self.get_all_context_from_query(
            type=ContextType.RERANK
        )
        start_time = datetime.now().timestamp()
        print(
            f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } code 开始进行rerank"
        )
        await self.filter_selected_entities_by_llm(context=rerank_context)
        finish_time = datetime.now().timestamp()
        print(
            f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } code rerank结束  耗时time:{finish_time - start_time}"
        )
        self.should_exit_and_save_json("rerank")
        context = self.get_all_context_from_query(type=ContextType.CHAT)
        return context

    def get_all_context_from_query(self, type=ContextType.CHAT):
        if not len(self.selected_entities):
            raise Exception(
                f"问题: << {self.query} >> 未能召回有效的实体,有疑问请联系管理员"
            )
        self.token_num = 0
        entity_context = self.get_entity_context(type=type)
        # class_context = self.get_class_context(type=type)
        class_context = ""
        relationship_context, node_list_1 = self.get_relationship_context(
            type=type
        )
        community_context, node_list_2 = self.get_community_context(type=type)
        qa_context = self.get_qa_context()
        tech_doc_context = self.get_tech_doc_context()
        supplementary_context = self.get_supplementary_context(
            list(set(node_list_1 + node_list_2)),
            type=type,
        )
        return {
            "entity_context": entity_context,
            "class_context": class_context,
            "relationship_context": relationship_context,
            "community_context": community_context,
            "supplementary_context": supplementary_context,
            "qa_context": qa_context,
            "tech_doc_context": tech_doc_context,
        }

    # 获取实体的补充信息。作为 rerank prompt 信息补充。
    def get_entity_item_extra_context(self, id):
        def message_extra_handler(extra_data):
            if len(extra_data) == 0:
                return ""
            # 一个实体最多添加 5 条 commit 信息
            max_len = 5
            extra_str = "\nGitCommitHistory(供参考):"
            for index, extra_item in enumerate(extra_data):
                if index >= max_len:
                    break
                message = extra_item["message"]
                extra_str += f"\n  {message}"
            return extra_str

        # 只有配置了 desc 的 key 才会添加
        entity_config = {"message": message_extra_handler}

        context = ""
        if id not in self.selected_entities_extra_info:
            return ""
        _extra_item = self.selected_entities_extra_info[id]
        for extra_key, extra_value in _extra_item.items():
            if extra_key not in entity_config:
                continue
            handler = entity_config[extra_key]
            context += handler(extra_value)
        return context

    def get_entity_context(self, type=ContextType.CHAT):
        self.current_token_num = 0
        self.current_context = ""
        # 创建一个优先队列
        pq_Context = queue.PriorityQueue()
        class_MP = {}
        begin_index = 0
        log_result = (
            self.search_res["chat_entity_in_context"]
            if type == ContextType.CHAT
            else self.search_res["rerank_entity_in_context"]
        )
        # chat 的时候，使用 补充 class 原文件 的召回方式
        _get_graph_node_content = (
            get_graph_node_content
            if type == ContextType.RERANK
            else get_graph_node_content_with_class_code
        )
        for node_id in self.selected_entities:
            current_node = self.G.nodes[node_id]
            this_class_id = -1
            # 如果该实体的类型是类的话,那么当前类节点为node_id
            if not current_node["is_leaf"]:
                this_class_id = node_id
            else:
                for edge in list(self.G.in_edges(node_id)):
                    # 如果该实体的类型是方法的话,那么当前类节点为它属于的类
                    if self.G[edge[0]][edge[1]]["type"] == EdgeType.CHILD:
                        this_class_id = edge[0]
            if this_class_id == -1:
                # 如果当前节点不是类也不属于任何类的话，不加入
                continue

            if this_class_id not in class_MP:
                # 根据selected_entities的顺序加入节点信息
                class_MP[this_class_id] = begin_index
                begin_index += 1
                class_node = self.G.nodes[this_class_id]
                if type == ContextType.CHAT:
                    new_context = f"Entity Name: {class_node['name']}\n{'Code Path: ' + class_node['path'] if 'path' in class_node else ''}\n{self.get_graph_node_content(node=class_node, type=self.search_type)}\nCode: {class_node['file_content']}\n\n"
                else:
                    new_context = f"Entity Name: {class_node['name']}\n{'Code Path: ' + class_node['path'] if 'path' in class_node else ''}\n{self.get_graph_node_content(node=class_node, type=self.search_type)}\n\n"
                pq_Context.put((class_MP[this_class_id], new_context))

            # TODO 暂时去除 commit 补充信息
            # commit_str = self.get_entity_item_extra_context(id=node_id)
            commit_str = ""
            if type == ContextType.CHAT:
                graph_node_content = get_graph_node_content_without_description(
                    node=current_node, type=self.search_type
                ).strip()
                new_context = f"Entity Name: {current_node['name']}\nType:{current_node['type']}\n{('Code Path: ' + current_node['path']) if 'path' in current_node else ''}\n{graph_node_content}Commit Information: {commit_str}\n\n"
            else:
                graph_node_content = _get_graph_node_content(
                    node=current_node, type=self.search_type
                ).strip()
                new_context = f"Entity Name: {current_node['name']}\nType:{current_node['type']}\n{('Code Path: ' + current_node['path']) if 'path' in current_node else ''}\n{graph_node_content}Commit Information: {commit_str}\n\n"
            if type == ContextType.RERANK:
                if this_class_id != node_id:
                    pq_Context.put((class_MP[this_class_id], new_context))

        # 按照顺序将信息加到entity context中
        while not pq_Context.empty():
            priority, new_context = pq_Context.get()
            isSuccess = self.add_new_context(
                new_context,
                current_max_tokens=local_search_settings["entity_max_tokens"],
            )
            if not isSuccess:
                break
            # 实体进入到窗口记录下来

            log_result.append({**current_node, "id": node_id})
        return self.current_context

    def get_class_context(self, type=ContextType.CHAT):
        self.current_token_num = 0
        self.current_context = ""
        is_add = {}
        for node_id in self.selected_entities:
            current_node = self.G.nodes[node_id]
            # 检索出来的 entity 就是 class，直接取即可
            if not current_node["is_leaf"]:
                if node_id in is_add:
                    continue
                is_add[node_id] = 1
                if type == ContextType.RERANK:
                    new_context = f"ID: {node_id}\nClass Name: {current_node['name']}\n{'Code Path: ' + current_node['path'] if 'path' in current_node else ''}\n{self.get_graph_node_content(node=current_node, type=self.search_type)}\n\n"
                else:
                    new_context = f"ID: {node_id}\nClass Name: {current_node['name']}\n{'Code Path: ' + current_node['path'] if 'path' in current_node else ''}\n{self.get_graph_node_content(node=current_node, type=self.search_type)}\nCode: {current_node['file_content']}\n\n"

                isSuccess = self.add_new_context(
                    new_context,
                    current_max_tokens=local_search_settings[
                        "class_max_tokens"
                    ],
                )
                if not isSuccess:
                    break
                continue
            edge_list = list(self.G.out_edges(node_id))
            for edge in list(self.G.in_edges(node_id)):
                if self.G[edge[0]][edge[1]]["type"] == EdgeType.CHILD:
                    edge_list.append(edge)
            # edge_list = list(self.G.out_edges(node_id)) + list(
            #     self.G.in_edges(node_id)
            # )
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
                        # new_context = f"ID: {candidate_node_id}\nClass Name: {candidate_node['name']}\n{self.get_graph_node_content(node=candidate_node, type=self.search_type)}\n\n"
                        new_context = f"ID: {candidate_node_id}\nClass Name: {candidate_node['name']}\n{self.get_graph_node_content(node=candidate_node, type=self.search_type)}\nCode: {candidate_node['file_content']}\n\n"
                        isSuccess = (
                            self.add_new_context(
                                new_context,
                                current_max_tokens=local_search_settings[
                                    "class_max_tokens"
                                ],
                            )
                            and isSuccess
                        )
                if not isSuccess:
                    break
        self.selected_entities += list(is_add.keys())
        self.selected_entities = list(set(self.selected_entities))
        return self.current_context if len(self.current_context) > 0 else "null"

    def get_relationship_context(self, type):
        return "", []
        if type == ContextType.RERANK:
            now_find_layer_depth = 1
        else:
            now_find_layer_depth = code_find_layer_depth
        self.current_context = ""
        node_list = []
        if self.search_type == SearchType.CODE:
            for node_id in self.selected_entities:
                if not self.G.nodes[node_id]["is_leaf"]:
                    # 接下来需要加入extend,以及上下x层的信息
                    this_node_list, addition_context = get_layer_nodes(
                        self.G, node_id, now_find_layer_depth, FindType.CLASS
                    )
                    self.current_context += addition_context
                    node_list += this_node_list
                else:
                    this_node_list, addition_context = get_layer_nodes(
                        self.G, node_id, now_find_layer_depth, FindType.METHOD
                    )
                    self.current_context += addition_context
                    node_list += this_node_list
        elif self.search_type == SearchType.DOCS:
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
                    if "relative" in edge_type:
                        # 提取关键词
                        keywords = (
                            edge_description.split(":")[1].strip().split(", ")
                        )
                        self.current_context += f"{source_node} and {target_node} are relative by keywords: {', '.join(keywords)}\n"
            print("the number of this_node_list: ", len(node_list))
            print("the current_context: ", self.current_context)
        # return self.current_context, list(set(node_list))
        # TODO: 不添加 relationship_context
        return "", list(set(node_list))

    def get_community_context(self, type):
        return "", []
        self.current_token_num = 0
        self.current_context = ""
        is_add = {}
        node_list = []
        log_result = (
            self.search_res["chat_community_in_context"]
            if type == ContextType.CHAT
            else self.search_res["rerank_community_in_context"]
        )
        for node_id in self.selected_entities:
            community_ids = self.G.nodes[node_id]["community_id"]
            if not isinstance(community_ids, list):
                community_ids = [community_ids]
            if len(community_ids) == 0:
                continue
            community_ids = community_ids[::-1]
            for community_id in community_ids:
                if int(community_id) < 0:
                    continue
                community_id = str(community_id)

                if community_id not in is_add:
                    is_add[community_id] = 1
                    node_list += self.community[community_id]["nodes"]
                    # new_context = f"Community ID: {community_id}\n Community Node List: {','.join([self.G.nodes[node_id]['name'] for node_id in self.community[community_id]['nodes']])}\n Community Description: {self.community[community_id]['reports']}\n\n"
                    new_context = f"Community ID: {community_id}\n Community Description: {self.community[community_id]['reports']}\n\n"
                    isSuccess = self.add_new_context(
                        new_context,
                        current_max_tokens=local_search_settings[
                            "community_max_tokens"
                        ],
                    )
                    if not isSuccess:
                        break
                    log_result.append(
                        {
                            **self.community[community_id],
                            "community_id": community_id,
                            "node_names": [
                                self.G.nodes[node_id]["name"]
                                for node_id in self.community[community_id][
                                    "nodes"
                                ]
                            ],
                        }
                    )
        return self.current_context, list(set(node_list))

    # 补充实体
    def get_supplementary_context(self, node_list, type=ContextType.CHAT):
        return "", []
        self.current_token_num = 0
        self.current_context = ""
        # rerank 不添加补充内容
        if type == ContextType.RERANK:
            return self.current_context
        for node_id in node_list:
            if node_id in self.selected_entities:
                continue
            node = self.G.nodes[node_id]
            new_context = f"ID: {node_id}\nEntity Name: {node['name']}\nType: {node['type']}\n{'Code Path: ' + node['path'] if 'path' in node else ''}\n{self.get_graph_node_content(node=node, type=self.search_type)}\n\n"
            isSuccess = self.add_new_context(
                new_context,
                current_max_tokens=local_search_settings[
                    "supplementary_max_tokens"
                ],
            )
            if not isSuccess:
                break
        return self.current_context

    def get_qa_context(self):
        if not self.is_use_qa or self.search_type != SearchType.CODE:
            return ""
        if self.qa_context:
            return self.qa_context
        # 目前仅 代码的 rerank + chat 支持 qa context
        qa_max_tokens = min(
            local_search_settings["qa_context_max_tokens"],
            self.max_tokens - self.token_num,
        )
        # 如果剩余 tokens 过小，不再召回 Q&A
        if qa_max_tokens <= 100:
            return ""
        qa_graph_rag = QAGraphSearch(
            user_question=self.user_question,
            query=self.query,
            sub_querys=self.sub_querys,
            query_embeddings=self.query_embeddings,
            db_path=self.db_path,
            table_list=[QAINFO_NAMES],
            max_tokens=qa_max_tokens,
        )
        qa_final_context = qa_graph_rag.execute_local_search_sync()
        self.qa_context = qa_final_context["qa_context"]
        return self.qa_context

    def get_tech_doc_context(self):
        # TODO 后面再看下
        if not self.is_use_tech_doc:
            return ""
        # if self.qa_context:
        #     return self.qa_context
        # 目前仅 代码的 rerank + chat 支持 qa context
        qa_max_tokens = min(
            local_search_settings["qa_context_max_tokens"],
            self.max_tokens - self.token_num,
        )
        # 如果剩余 tokens 过小，不再召回 Q&A
        if qa_max_tokens <= 100:
            return ""
        qa_graph_rag = TechDocGraphSearch(
            user_question=self.user_question,
            query=self.query,
            sub_querys=self.sub_querys,
            query_embeddings=self.query_embeddings,
            db_path=self.db_path,
            table_list=TECH_DOC_COLLECTION_NAMES,
            max_tokens=qa_max_tokens,
        )
        tech_doc_context = qa_graph_rag.execute_local_search_sync()
        self.tech_doc_context = tech_doc_context["tech_doc_context"]
        return self.tech_doc_context

    # 输出结构化日志数据
    def save_rerank_output_json(self):
        log_path = LOG_DIR_PATH / f"output.json"
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
                "query_top_k": self.query_top_k,
                "sub_top_k": self.sub_top_k,
                "bm25_top_k": self.bm25_top_k,
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
