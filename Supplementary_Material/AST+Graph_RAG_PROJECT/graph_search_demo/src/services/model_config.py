from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# from langchain_anthropic import ChatAnthropic


OPENAI_EMBEDDING_API_KEY = "YOUR_OPENAI_EMBEDDING_API_KEY"
OPENAI_EMBEDDING_BASE_URL = "https://your-llm-cache-proxy.example.com/cache/v1"


LLM_API_KEY = "YOUR_LLM_API_KEY"
LLM_BASE_URL = "https://your-llm-proxy.example.com/v1"
LLM_CACHE_URL = "https://your-llm-cache-proxy.example.com/v1"

AI_STUDIO_API_KEY = "YOUR_AI_STUDIO_API_KEY"
AI_STUDIO_BASE_URL = "https://your-ai-studio.example.com/api/openai/v1"


# client = Anthropic(
#     # defaults to os.environ.get("ANTHROPIC_API_KEY")
#     api_key="my_api_key",
# )

embedding_qurey_model = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_base=AI_STUDIO_BASE_URL,
    openai_api_key=AI_STUDIO_API_KEY,
)


embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_base=OPENAI_EMBEDDING_BASE_URL,
    openai_api_key=OPENAI_EMBEDDING_API_KEY,
)

rerank_model_mini = ChatOpenAI(
    model="gpt-4o-mini-0718-global",
    api_key=AI_STUDIO_API_KEY,
    base_url=AI_STUDIO_BASE_URL,
    temperature=0.5,
)
rerank_model_no_stream = ChatOpenAI(
    model="gpt4o",
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    temperature=0,
    streaming=False,
)

chat_model = ChatOpenAI(
    model="gpt4o",
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    streaming=False,
    temperature=0,
)

# chat_model = ChatOpenAI(
#     model="claude35_sonnet", api_key=AI_STUDIO_API_KEY, base_url=AI_STUDIO_BASE_URL, streaming=False
# )

rerank_model = ChatOpenAI(
    model="claude35_sonnet",
    api_key=AI_STUDIO_API_KEY,
    base_url=AI_STUDIO_BASE_URL,
    streaming=False,
)

report_model = ChatOpenAI(
    model="gpt4o", api_key=LLM_API_KEY, base_url=LLM_CACHE_URL
)

ai_studio_chat_model = ChatOpenAI(
    model="gpt-4o-0513-global",
    api_key=AI_STUDIO_API_KEY,
    base_url=AI_STUDIO_BASE_URL,
    temperature=0,
)
