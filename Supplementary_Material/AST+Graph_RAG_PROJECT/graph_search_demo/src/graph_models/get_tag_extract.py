from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
from services.model_config import chat_model
from prompts.tag_extract import tag_extract_prompt
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List
from datetime import datetime

pageMap = {
    "行前页": [
        "PageA1.page",
        "PageA2.page",
        "PageA3.page",
        "PageA4.page",
        "PageA5.page",
    ],
    "行中页": ["PageB1.page"],
    "行后页": ["PageC1.page"],
}


class ExtractResult(BaseModel):
    """
    {
        "business": "business list",
        "is_log": "Is the question about log",
        "rewrite_q": "rewrite question"
    }
    """

    business: List[str] = Field(description="business list")
    is_log: str = Field(description="Is the question about log")
    rewrite_q: str = Field(description="The rephrased question")


async def stream_output(chain, prompt_input):
    res = None
    async for chunk in chain.astream(prompt_input):
        res = chunk
    return res


async def get_tag_extract(user_question):
    print(
        f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } 开始问题拆分"
    )
    parser = JsonOutputParser(pydantic_object=ExtractResult)
    prompt_template = PromptTemplate(
        template=tag_extract_prompt,
        input_variables=["input_text"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        },
    )
    chain = prompt_template | chat_model | parser
    result = await stream_output(chain, {"input_text": user_question})
    # [] - 不过滤 or ['PageA1.page'] or [ '...PageA1.page', 'PageA1.page' ]
    page_list = [
        page
        for item in result["business"]
        if item in pageMap
        for page in pageMap[item]
    ]
    # 1-保留log文件 0-过滤log文件
    is_log = result["is_log"]
    # 重写后的问题
    rewrite_q = result["rewrite_q"]
    print(f"\ntag_extract: rewrite_q -> {rewrite_q}\n")
    print(f"\ntag_extract: page_list -> {page_list}\n")
    print(f"\ntag_extract: is_log -> {is_log}\n")

    print(
        f">>>>>>>>>> { datetime.now().strftime('%Y-%m-%d %H:%M:%S') } 问题拆分完成"
    )
    return rewrite_q, page_list, is_log
