from services.model_config import report_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tenacity import retry, stop_after_attempt, wait_fixed
from prompts import (
    COMMUNITY_REPORT_PROMPT,
    GLOBAL_SEARCH_COMMUNITY_REPORT_PROMPT,
)


MAX_RETRY_ATTEMPTS = 10
WAIT_SECONDS = 10


@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS), wait=wait_fixed(WAIT_SECONDS)
)
async def stream_output(chain, prompt_input):
    res = ""
    async for chunk in chain.astream({"input_text": prompt_input["input"]}):
        res += chunk
    return res


async def llm_community_report_chain(prompt_input, community_type="local"):
    """
    为单个 community 生成总结报告
    prompt_input:
        id: 社区 id
        input: 字符串格式，具体包含如下三种信息
            Entities: entity
            Relationships: source,target,description
            Entity Info: entity,description
    """
    prompt = (
        COMMUNITY_REPORT_PROMPT
        if community_type == "local"
        else GLOBAL_SEARCH_COMMUNITY_REPORT_PROMPT
    )
    print(f"Generate reports for Community {prompt_input['id']} ......")
    prompt_template = ChatPromptTemplate.from_messages([("user", prompt)])
    parser = StrOutputParser()
    chain = prompt_template | report_model | parser
    result = await stream_output(chain, prompt_input)
    print(f"Community {prompt_input['id']} Done!")
    return result
