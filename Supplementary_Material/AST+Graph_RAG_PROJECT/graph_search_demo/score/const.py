from pathlib import Path
from langchain_openai import ChatOpenAI

# ai map. 100w
LLM_API_KEY = "YOUR_LLM_API_KEY"
LLM_BASE_URL = "https://your-llm-proxy.example.com/v1"
LLM_CACHE_URL = "https://your-llm-cache-proxy.example.com/v1"

# ai studio. 30w
AI_STUDIO_API_KEY = "YOUR_AI_STUDIO_API_KEY"
AI_STUDIO_BASE_URL = "https://your-ai-studio.example.com/api/openai/v1"


# TAG 目录
ROOT_DIR = Path(__file__).resolve().parent.parent
SCORE_DIR = ROOT_DIR / "score"
CONFIG_DIR = SCORE_DIR / "config"
SOURCE_DATA_DIR = SCORE_DIR / "data"
SOURCE_LOG_DIR = SCORE_DIR / "log"
# src 目录 chat 执行日志目录
SRC_CHAT_LOG_DIR = ROOT_DIR / "log"


# TAG GPT
chat_model = ChatOpenAI(
    model="gpt4o",
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    temperature=0,
)
cache_chat_model = ChatOpenAI(
    model="gpt4o",
    api_key=LLM_API_KEY,
    base_url=LLM_CACHE_URL,
    temperature=0,
)
ai_studio_chat_model = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=AI_STUDIO_API_KEY,
    base_url=AI_STUDIO_BASE_URL,
    temperature=0,
)
