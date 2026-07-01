import threading
from langchain_chroma import Chroma


class SingletonGetChroma:
    def get_db(
        collection_name, persist_directory, embedding_function
    ) -> Chroma:
        print(f"get db collection_name={collection_name}")
        return Chroma(
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedding_function=embedding_function,
        )
