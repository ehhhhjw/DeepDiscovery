from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from chat.prompt.commit import (
    COMMIT_HANDLER_PROMPT,
    FILE_RELATED_PROMPT,
    EXTRACT_COMMIT_PROMPT,
)
from .index import cache_model, chat_model
from .utils import stream_output
from typing import List


# TAG 删除无用 commit，拆分 commit，提取场景/实体、功能/行为
class EXTRACT_COMMIT(BaseModel):
    message: str = Field(description="commit message")
    entity: str = Field(description="commit 中识别出的实体/场景。")
    action: str = Field(description="commit 中识别出的行为/功能。")
    reason: str = Field(description="commit 拆分的原因。使用中文输出。")
    is_valid: bool = Field(description="表示 message 是否包含有效信息。")


# JSON list 解析器
class ExtractCommitListParser(JsonOutputParser):
    def parse(self, output: str) -> List[EXTRACT_COMMIT]:
        # 调用父类的解析方法
        parsed_output = super().parse(output)
        return [EXTRACT_COMMIT(**item) for item in parsed_output]


async def extract_commit(data, use_cache):
    context = {"source_data": data}
    parser = ExtractCommitListParser(pydantic_object=EXTRACT_COMMIT)
    prompt_template = PromptTemplate(
        input_variables=["source_data"],
        template=EXTRACT_COMMIT_PROMPT,
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    model = cache_model if use_cache else chat_model
    chain = prompt_template | model | parser
    result = await stream_output(chain, context)
    return result


# TAG 判断文件和 commit 的关联性
class FILE_ITEM(BaseModel):
    name: str = Field(description="文件名称")
    reason: str = Field(description="文件是否与 commit 相关的原因。使用中文输出。")
    related: bool = Field(description="表示文件是否与 commit message 信息相关。")


class FILE_RELATED(BaseModel):
    message: str = Field(description="commit message")
    files: List[FILE_ITEM] = Field(
        description="处理后的文件列表。需要和输入的文件一一对应，不能丢失或增加。"
    )


async def check_file_related(data, use_cache):
    context = {"source_data": data}
    parser = JsonOutputParser(pydantic_object=FILE_RELATED)
    prompt_template = PromptTemplate(
        input_variables=["source_data"],
        template=FILE_RELATED_PROMPT,
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    model = cache_model if use_cache else chat_model
    chain = prompt_template | model | parser
    result = await stream_output(chain, context)
    return result


# TAG 链式处理 commit
async def handler_commit_chain(data, use_cache=True):
    message = data["message"]
    extract_result = await extract_commit(message, use_cache)
    commit_list = []
    for item in extract_result:
        if not item["is_valid"]:
            continue
        commit_list.append({**item, "files": data["files"]})
    if len(commit_list) == 0:
        return []
    check_result = await check_file_related(commit_list, use_cache)
    return check_result


# TAG 统一处理 commit
class FILE_REASON(BaseModel):
    name: str = Field(description="文件名称")
    reason: str = Field(
        description="输出 related true 或 false 的原因，请一步一步结合文件变更内容认真思考，此文件是否和 commit 相关。使用中文输出。"
    )
    related: bool = Field(description="表示文件是否与 commit message 信息相关")


class COMMIT_DATA(BaseModel):
    id: str = Field(description="源数据中的 Id")
    is_valid: bool = Field(description="表示 message 是否包含有效信息")
    reason: str = Field(description="commit 是否包含有效信息的原因。使用中文输出。")
    scene: str = Field(description="commit 中识别出的场景。")
    action: str = Field(description="commit 中识别出的行为。")
    message: str = Field(description="源数据中，commit message 信息。")
    files: List[FILE_REASON] = Field(description="处理的文件列表")


async def handler_commit(source_data, use_cache=True):
    context = {"source_data": source_data}
    parser = JsonOutputParser(pydantic_object=COMMIT_DATA)
    prompt_template = PromptTemplate(
        input_variables=["source_data"],
        template=COMMIT_HANDLER_PROMPT,
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    model = cache_model if use_cache else chat_model
    chain = prompt_template | model | parser
    result = await stream_output(chain, context)
    return result
