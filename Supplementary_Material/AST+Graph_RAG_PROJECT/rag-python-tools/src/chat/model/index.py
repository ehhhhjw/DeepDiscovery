from langchain_openai import OpenAIEmbeddings, ChatOpenAI

OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
OPENAI_BASE_URL = "https://openkey.cloud/v1"
# OPENAI_BASE_URL = "https://openkey.red/v1"
# https://giegie.green/


LLM_API_KEY = "YOUR_LLM_API_KEY"
LLM_BASE_URL = "https://your-llm-proxy.example.com/v1"
LLM_CACHE_URL = "https://your-llm-cache-proxy.example.com/v1"

embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_base=OPENAI_BASE_URL,
    openai_api_key=OPENAI_API_KEY,
)

chat_model = ChatOpenAI(
    model="gpt4o", api_key=LLM_API_KEY, base_url=LLM_BASE_URL, temperature=0.2
)

cache_model = ChatOpenAI(
    model="gpt4o", api_key=LLM_API_KEY, base_url=LLM_CACHE_URL, temperature=0.2
)
