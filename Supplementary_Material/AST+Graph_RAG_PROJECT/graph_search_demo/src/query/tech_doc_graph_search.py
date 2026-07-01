from langchain_chroma import Chroma
from services.model_config import embedding_model
from utils.embedding_query import embedding_querys
from utils import num_tokens_from_string
from utils.load_vector_db import SingletonGetChroma
from constants import COLLECTION_SCORE_LIMIT


class TechDocGraphSearch:
    """
    QA Graph Local Search Class
        Args:
            query: User question
            top_k: recall number
            db_path: Path to vector db storage
    """

    def __init__(
        self,
        user_question,
        query,
        db_path,
        table_list,
        sub_querys,
        max_tokens=10 * 1000,
        max_length=1,
        query_embeddings={},
    ):
        self.user_question = user_question
        self.query = query
        self.sub_querys = sub_querys or []
        self.query_embeddings = query_embeddings
        self.table_list = table_list
        self.vector_db: dict[str, Chroma] = {}
        self.score_limit = COLLECTION_SCORE_LIMIT
        for c in table_list:
            self.vector_db[c] = SingletonGetChroma.get_db(
                collection_name=c,
                persist_directory=db_path,
                embedding_function=embedding_model,
            )
        # selected entity {  }
        self.selected_entities = []
        self.token_num = 0
        self.max_length = max_length
        self.max_tokens = max_tokens

        self.current_context = ""
        self.final_context = None

    def query_entity_by_embedding(self):
        print("RAG RECALL SCORE: \n")
        final_res = []
        if not ("query" in self.query_embeddings):
            # query_embeddings => {"query": xxx, "sub_query": [ xxx, xxx ]}
            self.query_embeddings = embedding_querys(
                query=self.query, user_question=self.user_question
            )

        for c in self.table_list:
            print(f"\n>>>>>>>> Score of {c}")
            vertor_db = self.vector_db[c]
            recall = (
                vertor_db.similarity_search_by_vector_with_relevance_scores(
                    embedding=self.query_embeddings["query"],
                    k=self.max_length * 2,
                )
            )
            recall = sorted(recall, key=lambda x: x[1])
            for entity, score in recall:
                if self.need_filter_entity_by_score(
                    current_score=score, collection_name=c
                ):
                    continue
                metadata = entity.metadata
                tech_doc_id = metadata["id"]
                content = metadata["content"]
                print(
                    f"ID: {tech_doc_id}, TECH_DOC: {entity.page_content}, SCORE: {score}"
                )
                final_res.append(
                    {
                        "id": tech_doc_id,
                        "score": score,
                        "type": c,
                        "metadata": metadata,
                    }
                )

        final_res = sorted(final_res, key=lambda x: x["score"])
        print("Final Ranking: \n")
        cache = set()
        # 问题最多只取一个
        for i in range(min(self.max_length, len(final_res))):
            # 已经存在直接忽略
            entity_id = final_res[i]["id"]
            if entity_id in cache:
                continue
            cache.add(entity_id)
            content = final_res[i]["metadata"]["content"]
            # 加入到 selected_entities
            self.selected_entities.append(final_res[i])
            print(f"ID:{entity_id}, content:{content}")
        print("\n\n")

    def need_filter_entity_by_score(self, current_score, collection_name=None):
        """
        按 score 进行顾虑，默认分数从 0-2, 分数越低相似度越高，过滤掉分数过大的
        true 过滤
        false 不过滤
        """
        score_limit = (
            self.score_limit[collection_name]
            if (
                collection_name
                and self.score_limit
                and collection_name in self.score_limit
            )
            else 2
        )
        # 分数越低越好，小于给定的限制分数，直接通过
        return current_score > score_limit

    async def execute_local_search(self):
        """
        异步检索的方法
        """
        return self.execute_local_search_sync()

    def execute_local_search_sync(self):
        """
        同步检索的方法
        """
        self.final_context = self.get_context()
        return self.final_context

    def get_context(self):
        """
        Return context of graph search
        """
        self.query_entity_by_embedding()
        tech_doc_context = self.tech_doc_context()
        return {"tech_doc_context": tech_doc_context}

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

    def tech_doc_context(
        self,
    ):
        self.current_context = ""
        for node in self.selected_entities:
            metadata = node["metadata"]
            new_context = metadata["content"]
            isSuccess = self.add_new_context(new_context)
            if not isSuccess:
                break
        return self.current_context
