from langchain_chroma import Chroma

# "docs_name",
# "docs_report",
# "docs_comment",
# "docs_description",
vector_db = Chroma(
    collection_name="docs_description",
    persist_directory="./chroma_db_docs/chroma_db",
)


data = vector_db.get()

print(len(data.get("ids")))
