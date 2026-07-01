import argparse
import asyncio
from datetime import datetime
import re
from openai import AsyncOpenAI
from util import (
    get_attributes,
)
import json
import os
from task_queue import TaskQueue
import tiktoken


PROMPT_FILE_PATH = "prompts.txt"

tiktoken_enc = tiktoken.get_encoding('o200k_base') # 直接按 4o 计算

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
    else:
        print(f"文件不存在 >>>>>> {filepath}")
    return None

def getPrompts():
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    target_file = os.path.join(current_dir, PROMPT_FILE_PATH)
    prompts = getFileText(target_file)
    return prompts

def getOutputFilePath(filename):
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    base_output = os.path.join(current_dir, 'output')
    if not os.path.isdir(base_output):
        os.mkdir(base_output)
    target_file_path = os.path.join(base_output, filename)
    return target_file_path

client = AsyncOpenAI(
    base_url='https://your-llm-cache-proxy.example.com/v1',
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
    if results.startswith('```'):
        # 删除开头的格式化字符 和 空字符
        return re.sub(r'^```plaintext:?\s*|^```markdown:?\s*|^```output:?\s*|^```\s*|```\s*$', '', results, flags=re.IGNORECASE)
    return results

def template_replace(prompts, fileText, nodeList, importList, fileComment):
    prompts = re.sub(r'\{tuple_delimiter\}', '<|>', prompts)
    prompts = re.sub(r'\{record_delimiter\}', '##', prompts)
    prompts = re.sub(r'\{completion_delimiter\}', '<|COMPLETE|>', prompts)
    prompts = re.sub(r'\{entity_names\}', ','.join(nodeList), prompts)
    prompts = re.sub(r'\{import_entities\}', ','.join(importList), prompts)
    prompts = re.sub(r'\{file_comments\}', fileComment, prompts)
    # prompts = re.sub(r'\{input_text\}', fileText, prompts)
    prompts = prompts.replace('{input_text}', fileText)
    return prompts

# 将结果写入到文件中
def logResult2File(args, text, filename = None):
    if not filename:
        # 输出结果到文件中
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        filename = f'report_result_{formatted_time}:{current_time.microsecond}.log'
    filepath = getOutputFilePath(filename)
    if args.use_param:
        filepath = args.output_data_path
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

async def getSummary(file_content=None, filepath=None, nodeList=[], importList=[], fileComment=None):
    # print(len(nodeList))
    # return
    if len(nodeList) == 0 and len(importList) == 0:
        print(f"文件不存在需要提取的 nodeList 与 importList, filepath={filepath}")
        return {}
    # if (not file_content) and filepath:
    #     file_content = getFileText(filepath)

    if not file_content:
        return {}
    input = template_replace(
        prompts=getPrompts(),
        fileText=file_content,
        nodeList=nodeList,
        importList=importList,
        fileComment=fileComment,
    )
    # logResult2File(text=input)
    # return

    # 提前校验 tokens 长度，如果文件太大，就直接返回空数据了
    file_tokens = len(tiktoken_enc.encode(input))
    if file_tokens > 110_000:
        print(f"文件 tokens: {file_tokens} 超过 110k, filepath={filepath}")
        return {}

    messages = [
        {"role": "user", "content": input},
    ]
    history = [
        *messages,
    ]
    results = await (await TaskQueue.add_task(async_llm_chat, messages=messages))
    history.append({"role": "assistant", "content": results })

    # 最大连续问答次数
    max_retries = 4
    retries = 0
    while('<|COMPLETE|>' not in results) and (retries < max_retries):
        final_result, file_comment = get_attributes(results)
        # Todo: 处理一些bad case.如果个数已经够了，但是模型没有返回完成，立即终止。
        if len(final_result) >= len(nodeList) + len(importList):
            results += '\n<|COMPLETE|>\n--逻辑终止--'
            break
        retries += 1
        glean_messages = [
            *history,
            {"role": "user", "content": 'continue'},
        ]
        history.append({"role": "user", "content": 'continue'})
        glean_results = await (await TaskQueue.add_task(async_llm_chat, messages=glean_messages))
        history.append({"role": "assistant", "content": glean_results })
        # 合并两次问答的结果
        results += glean_results
    logLLMResult2File(text=f'''{filepath}
{results}
''')
    return get_attributes(results)

def getTreeConfig(args):
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    # TODO: 更改入口 json 配置
    target_file = os.path.join(current_dir, 'ast_graph_1501.json')
    if args.use_param:
        target_file = args.ast_data_path
    content = getFileText(target_file)
    json_tree = json.loads(content)
    return json_tree

async def main(args):
    tree = getTreeConfig(args)
    async def process_class_item(classItem):
        try:
            names = []
            if classItem['Children']:
                names = [a['Name'] for a in classItem['Children'] if a['Name']]
            className = ".".join(classItem['Name'].split('.')[:-1])
            if className:
                names = [
                    className,
                    *names,
                ]
            imports = []
            if classItem['Dependent']:
                imports = classItem['Dependent']
            if not (len(names) and classItem['Root']):
                return classItem
            filepath = classItem["Root"]
            filecomment = classItem["FileComment"]
            sumarry_result, file_comment = await getSummary(
                filepath=filepath,
                file_content=classItem["FileContent"],
                nodeList=names,
                importList=imports,
                fileComment=filecomment+names[0],
            )
            if len(sumarry_result) == 0:
                print(f">>>>>> 未提取到报告,filePath={className}")
            if className in sumarry_result:
                classItem['Report'] = sumarry_result[className]["Report"]
                classItem['ShortReport'] = sumarry_result[className]["ShortReport"]
                classItem['FileComment'] = file_comment[className]["FileComment"] if className in file_comment else ""
                # print(className, classItem['FileComment'])
            if classItem['Children']:
                for child in classItem['Children']:
                    if child['Name'] in sumarry_result:
                        child['Report'] = sumarry_result[child['Name']]["Report"]
                        child['ShortReport'] = sumarry_result[child['Name']]["ShortReport"]
                        child['RelatedScore'] = sumarry_result[child['Name']]['RelatedScore']
                        child['ScoreReason'] = sumarry_result[child['Name']]['ScoreReason']

            Dependent_Edge_Information = []
            for edge_target_name in sumarry_result:
                edge_message = {}
                edge_message['Name'] = edge_target_name
                edge_message['RelatedScore'] = sumarry_result[edge_target_name]['RelatedScore']
                edge_message['ScoreReason'] = sumarry_result[edge_target_name]['ScoreReason']
                edge_type = sumarry_result[edge_target_name]['EdgeType']
                if edge_type == "Dependent":
                    Dependent_Edge_Information.append(edge_message)
            classItem['DependentEdgeInformation'] = Dependent_Edge_Information
            print(classItem['Name'])
        except Exception as e:
            print(f"Error in getSummary >>>>>>\n {e}")
        return classItem

    tasks = [process_class_item(classItem) for classItem in tree]
    results = await asyncio.gather(*tasks)
    updated_tree = [result for result in results if result is not None]
    # 存储结果到文件
    logResult2File(args, json.dumps(updated_tree, indent=4, ensure_ascii=False))
    return updated_tree


if (__name__ == '__main__'):
    parser = argparse.ArgumentParser(description="parameters for summary")
    parser.add_argument("--use_param", action="store_true")
    parser.add_argument("--ast_data_path", type=str)
    parser.add_argument("--output_data_path", type=str)
    args = parser.parse_args()
    the_generated_ast_message = asyncio.run(main(args))
