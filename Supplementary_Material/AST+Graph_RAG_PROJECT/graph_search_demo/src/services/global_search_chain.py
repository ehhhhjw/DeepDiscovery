import sys
from typing import List
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_fixed
from services.model_config import chat_model
from prompts.global_search_map import MAP_SYSTEM_PROMPT
from prompts.global_search_reduce import REDUCE_SYSTEM_PROMPT


MAX_RETRY_ATTEMPTS = 10
WAIT_SECONDS = 10


class Point(BaseModel):
    community_id: str = Field(
        description="The ID of the community associated with the point."
    )
    description: str = Field(
        description="Description of the point, including relevant data."
    )
    score: float = Field(description="Score value associated with the point.")


class PointsData(BaseModel):
    points: List[Point] = Field(
        description="List of points containing community details."
    )


@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS), wait=wait_fixed(WAIT_SECONDS)
)
async def stream_output(chain, prompt_input):
    res = None
    async for chunk in chain.astream(prompt_input):
        res = chunk
    return res


async def stream_output_chat(chain, prompt_input):
    async for chunk in chain.astream(prompt_input):
        sys.stdout.write(chunk)
        sys.stdout.flush()


async def llm_global_search_map(prompt_input):
    parser = JsonOutputParser(pydantic_object=PointsData)
    prompt_template = PromptTemplate(
        template=MAP_SYSTEM_PROMPT,
        input_variables=["context_data", "user_question"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        },
    )
    chain = prompt_template | chat_model | parser
    result = await stream_output(chain, prompt_input)
    return result


async def llm_global_search_reduce(prompt_input):
    prompt_template = ChatPromptTemplate.from_messages(
        [("user", REDUCE_SYSTEM_PROMPT)]
    )
    parser = StrOutputParser()
    chain = prompt_template | chat_model | parser
    await stream_output_chat(chain, prompt_input)
    context = prompt_template.invoke(prompt_input).messages[0].content
    return context
