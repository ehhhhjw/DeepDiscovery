import asyncio
from datetime import datetime
import re
from openai import AsyncOpenAI
from util import get_attributes
import json

import os

PROMPT_FILE_PATH = "prompts.txt"

def is_file(filepath):
    return os.path.isfile(filepath)
# 读取 代码文件
def getFileText(filepath):
    if is_file(filepath):
        with open(filepath, 'r') as file:
            # 读取文件内容
            content = file.read()
            # 打印文件内容
            return content
    return None

def getPrompts():
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    # TODO: 切换 prompts
    # 微调优化的版本
    target_file = os.path.join(current_dir, PROMPT_FILE_PATH)
    prompts = getFileText(target_file)
    return prompts

def getOutputFilePath(filename):
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    base_output = os.path.join(current_dir, 'output')
    if not os.path.isdir(base_output):
        os.mkdir(base_output)
    target_file_path = os.path.join(current_dir, 'output', filename)
    return target_file_path

client = AsyncOpenAI(
    base_url='https://your-llm-proxy.example.com/v1',
    api_key='YOUR_LLM_API_KEY'
)
async def async_llm_chat(messages):
    response = await client.chat.completions.create(
        messages=messages,
        stream=True,
        model="gpt4o",
        logprobs=False,
        n=1,
        temperature=0.5
    )
    results = ""
    async for chunk in response:
        # chunk的数据结构类似于 {'choices': [{'delta': {'content': '...'}}]}
        if chunk.choices:
            for choice in chunk.choices:
                if choice.delta and choice.delta.content:
                    results += choice.delta.content
    return results

def template_replace(prompts, fileText, nodeList):
    prompts = re.sub(r'\{tuple_delimiter\}', '<|>', prompts)
    prompts = re.sub(r'\{record_delimiter\}', '##', prompts)
    prompts = re.sub(r'\{completion_delimiter\}', '<|COMPLETE|>', prompts)
    prompts = re.sub(r'\{entity_names\}', ','.join(nodeList), prompts)
    prompts = prompts.replace('{input_text}', fileText)
    return prompts

# 将结果写入到文件中
def logResult2File(text, filename = None):
    if not filename:
        # 输出结果到文件中
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        filename = f'result_{formatted_time}:{current_time.microsecond}.log'
    filepath = getOutputFilePath(filename)
    with open(filepath, 'w', encoding='utf-8') as file:
        # 写入文本内容到文件中
        file.write(text)
    pass

# 将结果写入到文件中
def logLLMResult2File(text, filename = None):
    if not filename:
        # 输出结果到文件中
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        filename = f'llm_result_{formatted_time}:{current_time.microsecond}.log'
    filepath = getOutputFilePath(filename)
    with open(filepath, 'w', encoding='utf-8') as file:
        # 写入文本内容到文件中
        file.write(text)
    pass

async def getSummary(filepath, nodeList):
    # print(len(nodeList))
    # return
    code = getFileText(filepath)
    if not code:
        return {}
    input = template_replace(
        prompts=getPrompts(),
        fileText=code,
        nodeList=nodeList
    )
    # logResult2File(text=input)
    # return

    messages = [
        {"role": "user", "content": input},
    ]
    history = [
        *messages,
    ]
    results = await async_llm_chat(
        messages=messages,
    )
    history.append({"role": "assistant", "content": results })

    # 最大连续问答次数
    max_retries = 0
    retries = 0
    while('<|COMPLETE|>' not in results) and (retries < max_retries):
        retries += 1
        glean_messages = [
            *history,
            {"role": "user", "content": 'continue'},
        ]
        history.append({"role": "user", "content": 'continue'})
        glean_results = await async_llm_chat(messages=glean_messages)
        history.append({"role": "assistant", "content": glean_results })
        # 合并两次问答的结果
        results += glean_results
    logLLMResult2File(text=f'''{filepath}
{results}
''')
    return get_attributes(results)

def getTreeConfig():
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    # target_file = os.path.join(current_dir, 'final_json_file_2.json')
    target_file = os.path.join(current_dir, 'tree.json')
    content = getFileText(target_file)
    json_tree = json.loads(content)
    return json_tree

async def main():
    sumarry_result = await getSummary(
        # TODO: 修改被总结的文件地址 和 nodeList
        filepath='./summary/input/ExampleController.js',
        nodeList = [
            "ExampleController",
            "doInit",
            "doHandleClick",
            "doOpenList",
            "doCloseList",
            "doRefreshList",
            "doUpdateData"
        ],
    )
    print(sumarry_result)

if (__name__ == '__main__'):
    asyncio.run(main())
