import json
from langchain_chroma import Chroma
from langchain_core.documents import Document
from pathlib import Path
from services.model_config import embedding_model
from constants import (
    COLLECTION_NAMES,
    DOCS_COLLECTION_NAMES,
    COMMIT_COLLECTION_NAMES,
    TECH_DOC_COLLECTION_NAMES,
    QAINFO_NAMES,
    EmbeddingType,
)
from utils.pull_qa_data import pull_latest_data


def transeList2Str(pageListInfo):
    pageListStrInfo = ""
    index_flag = 0
    for pageinfo in pageListInfo:
        if index_flag == 0:
            pageListStrInfo = pageListStrInfo + pageinfo
            index_flag = 1
        else:
            pageListStrInfo = pageListStrInfo + "|" + pageinfo

    return pageListStrInfo


def handler_code(name, node):
    if name not in node or node[name] == "" or node[name] is None:
        return None
    # pageListStr = transeList2Str(node["pageList"])
    doc = Document(
        page_content=node[name],
        metadata={
            "id": node["id"]
            # "IsUtLog": node["isLog"],
            # "PageList": pageListStr,
        },
    )
    return doc


def handler_docs(name, node):
    val_key = name.split("_")[-1]
    if val_key not in node or node[val_key] == "" or node[val_key] is None:
        return None
    doc = Document(
        page_content=node[val_key],
        metadata={"id": node["id"], "type": node["type"]},
    )
    return doc


def handler_commit(name, node):
    if name not in node or node[name] == "" or node[name] is None:
        return None
    doc = Document(
        page_content=node[name],
        metadata={
            **node,
            "files": json.dumps(node["files"]),
        },
    )
    return doc


def handler_tech_docs(name, node):
    if name not in node:
        return None
    doc = Document(
        page_content=node[name],
        metadata={"id": node["id"]},
    )
    return doc


embedding_config_map = {
    EmbeddingType.CODE: {"names": COLLECTION_NAMES, "handler": handler_code},
    EmbeddingType.DOCS: {
        "names": DOCS_COLLECTION_NAMES,
        "handler": handler_docs,
    },
    EmbeddingType.COMMIT: {
        "names": COMMIT_COLLECTION_NAMES,
        "handler": handler_commit,
    },
    EmbeddingType.TECH_DOCS: {
        "names": TECH_DOC_COLLECTION_NAMES,
        "handler": handler_tech_docs,
    },
}


def create_question_answer_create_embeddings(save_path):
    # 拉取最新的QA数据
    QA_data = pull_latest_data()
    docs = {}
    docs[QAINFO_NAMES] = []
    vector_db = Chroma(
        persist_directory=save_path,
        collection_name=QAINFO_NAMES,
        embedding_function=embedding_model,
    )
    # 删除旧数据，重新生成
    if len(vector_db.get()["ids"]):
        vector_db.delete(ids=vector_db.get()["ids"])
    for QA_node in QA_data:
        this_ids = str(QA_node["id"])
        doc = Document(
            ids=this_ids,
            page_content=QA_node["chat_query"],
            metadata={
                "id": QA_node["id"],
                "chat_query": QA_node["chat_query"],
                "chat_answer": QA_node["chat_answer"],
                "gmt_create": QA_node["gmt_create"],
            },
        )
        docs[QAINFO_NAMES].append(doc)
    print(f"正在将QA数据导入向量数据库中")
    vector_db.add_documents(
        docs[QAINFO_NAMES],
    )
    print(f"QA数据导入向量数据库完成")


def handler_tech_docs_sub_summary(node, collection, save_path):
    doc_list = []
    findings = node["findings"]
    for finding in findings:
        doc = Document(
            page_content=finding[collection],
            metadata={
                "id": node["id"],
                "content": json.dumps(node, ensure_ascii=False),
            },
        )
        if doc is not None:
            doc_list.append(doc)
    return doc_list


def handler_tech_docs_entity_desc(node, collection, save_path):
    doc_list = []
    entity_list = node["entity_list"]
    for entity in entity_list:
        doc = Document(
            page_content=entity["tech_doc_entity_desc"],
            metadata={
                "id": node["id"],
                "content": json.dumps(node, ensure_ascii=False),
            },
        )
        if doc is not None:
            doc_list.append(doc)
    return doc_list


def create_tech_doc_embeddings(tech_doc_path, save_path):
    # 拉取最新的技术文档数据
    with open(tech_doc_path, "r", encoding="utf-8") as file:
        tech_doc_nodes_data = json.load(file)
    docs = {}
    for c in TECH_DOC_COLLECTION_NAMES:
        docs[c] = []
    for collection in TECH_DOC_COLLECTION_NAMES:
        for node in tech_doc_nodes_data:
            ids = str(node["id"])
            if collection == "tech_doc_sub_summary":
                sub_summary_docs = handler_tech_docs_sub_summary(
                    node, collection, save_path
                )
                docs[collection].extend(sub_summary_docs)
                continue  # 跳出当前内循环
            if collection == "tech_doc_entity_desc":
                entity_desc = handler_tech_docs_entity_desc(
                    node, collection, save_path
                )
                docs[collection].extend(entity_desc)
                continue  # 跳出当前内循环
            doc = Document(
                ids=ids,
                page_content=node[collection],
                metadata={
                    "id": node["id"],
                    "content": json.dumps(node, ensure_ascii=False),
                },
            )
            if doc is not None:
                docs[collection].append(doc)
        print(f"正在将技术文档数据导入向量数据库中")
        Chroma.from_documents(
            documents=docs[collection],
            collection_name=collection,
            embedding=embedding_model,
            persist_directory=save_path,
        )
    print(f"技术文档导入向量数据库完成")


def create_embeddings(graph_path, save_path, graph_type=EmbeddingType.CODE):
    """
    Create embedding for {graph_path} and save results to {save_path}
        Args:
            graph_path: Path to graph storage
            save_path: Path to save directory.
    """
    if graph_type == EmbeddingType.COMMIT:
        # if not Path(graph_path).is_file():
        #     # commit 模式，且没有对应的文件，不处理直接跳过
        #     return
        vector_db = Chroma(
            persist_directory=save_path,
            collection_name=EmbeddingType.COMMIT,
            embedding_function=embedding_model,
        )
        # 删除旧数据，重新生成
        if len(vector_db.get()["ids"]):
            vector_db.delete(ids=vector_db.get()["ids"])
    embedding_config = embedding_config_map[graph_type]
    if not embedding_config:
        raise ValueError(f"Invalid graph type: {graph_type}")

    table_list = embedding_config["names"]
    handler = embedding_config["handler"]

    with open(graph_path, "r", encoding="utf-8") as file:
        print(f"Processing raw data from {graph_path} ......")
        data = json.load(file)
        node_list = data["nodes"]
        docs = {}
        for c in table_list:
            docs[c] = []
        for node in node_list:
            for c in table_list:
                doc = handler(c, node)
                if doc is not None:
                    docs[c].append(doc)

        print(f"Document construction completed !")

        for c in table_list:
            print(f"Processing embedding for {c} ......")

            def split_list(
                input_list, max_len=1000, max_embedding_tokens=100_000
            ):
                """
                按 tokens 和最大长度进行数据切割，防止一次处理过多数据导致报错
                """
                if not input_list:
                    return

                import tiktoken

                encoding = tiktoken.get_encoding("cl100k_base")
                total_token = 0
                start = 0
                for i in range(len(input_list)):
                    current = len(encoding.encode(input_list[i].page_content))
                    if current > max_embedding_tokens:
                        raise Exception(
                            f"单条数据超过tokens最大限制 tokens={current}"
                        )
                    total_token += current
                    if total_token >= max_embedding_tokens or (
                        i - start >= max_len
                    ):
                        yield input_list[start:i]
                        total_token = current
                        start = i
                # 返回最后一波
                yield input_list[start:]

            print(f"collection={c}, total_len={len(docs[c])}")
            vector_db = Chroma(
                persist_directory=save_path,
                collection_name=c,
                embedding_function=embedding_model,
            )
            # 删除旧数据，重新生成
            if len(vector_db.get()["ids"]):
                vector_db.delete(ids=vector_db.get()["ids"])
            input_len = 0
            for split_docs_chunk in split_list(docs[c]):
                input_len += len(split_docs_chunk)
                vector_db.add_documents(
                    documents=split_docs_chunk,
                    ids=[str(doc.metadata["id"]) for doc in split_docs_chunk],
                )
                print(f"Finish one batch! len={len(split_docs_chunk)}")
            print(
                f"Successfully save {c} embeddings to {save_path} ! final_len={input_len}"
            )
