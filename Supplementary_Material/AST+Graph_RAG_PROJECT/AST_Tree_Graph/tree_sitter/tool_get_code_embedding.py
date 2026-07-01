from langchain_openai import OpenAIEmbeddings

OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
OPENAI_BASE_URL = "https://openkey.cloud/v1"

LLM_API_KEY = "YOUR_LLM_API_KEY"
LLM_BASE_URL = "https://your-llm-proxy.example.com/v1"

embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-large", 
        openai_api_base=OPENAI_BASE_URL,
        openai_api_key=OPENAI_API_KEY
    )

text = "// example method\n    getInfo() {\n        const Util = require('@your_bundle_lib_common/Util.js').default;\n        return Util.getData(this.id);\n    }\n"
embeddings = embedding_model.embed_documents(
    text
)
print(embeddings[0])
print(len(embeddings[0]))