import json
import re
import base64
from prompts.prd_to_task import prd_to_task_prompt
from services.model_config import chat_model


def format_requirements(requirement_list):
    # 构造所需格式的字符串
    formatted_output = '{\n'
    for index, requirement in enumerate(requirement_list):
        formatted_output += f'    "子需求{index + 1:02d}": "{requirement}"'
        if index < len(requirement_list) - 1:
            formatted_output += ',\n'
        else:
            formatted_output += '\n'
    formatted_output += '}'

    return formatted_output


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


"""
解析GPT4O返回的结果
 "ui_design_draft":"",
 "original_business_logic":""
 "Requirement Analysis": "",
 "Requirement Pool": {
    "1": ""
    "2": ""
    "3": ""
 },
 "Anything UNCLEAR": ""
"""


def parse_result(content):
    # 提取[CONTENT]至[/CONTENT]之间的内容
    content_match = re.search(r'\[CONTENT\](.*?)\[/CONTENT\]', content, re.DOTALL)
    if content_match:
        content_json = content_match.group(1).strip()
        # 解析JSON内容
        content_dict = json.loads(content_json)

        ui_design_draft = content_dict.get("ui_design_draft", "")
        original_business_logic = content_dict.get("original_business_logic", "")
        requirement_analysis = content_dict.get("Requirement Analysis", "")
        Anything_UNCLEAR = content_dict.get("Anything UNCLEAR", "")

        # 提取Requirement Pool内容并转换为list
        requirement_pool = content_dict.get("Requirement Pool", {}).values()

        # 转换为list输出结果
        requirement_list = list(requirement_pool)

        return ui_design_draft, original_business_logic, requirement_analysis, requirement_list, Anything_UNCLEAR
    else:
        print("未找到[CONTENT]内容")


def gpt4o_call(base64_image, origin_requirement):
    response = chat_model.invoke(
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prd_to_task_prompt
                    },
                    {
                        "type": "text",
                        "text": "ui_design_draft:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        },
                    },
                    {
                        "type": "text",
                        "text": "original_business_logic:"
                    },
                    {
                        "type": "text",
                        "text": origin_requirement
                    },
                ],
            }
        ],
    )
    response = response.content.strip()

    ui_design_draft, original_business_logic, requirement_analysis, requirement_list, Anything_UNCLEAR = parse_result(
        response)
    return ui_design_draft, original_business_logic, requirement_analysis, requirement_list, Anything_UNCLEAR


def get_prd_design(ui_draft, file_requirement):
    ## encode image
    base64_image = encode_image(ui_draft)
    ## read
    with open(file_requirement, 'r', encoding='utf-8') as file:
        origin_requirement = file.read()

    ## call LLM
    sub_tasks = gpt4o_call(base64_image, origin_requirement)

    return sub_tasks


def writePRD(prd_ui_draft_path, prd_business_logic_path):
    # test_data_image = "../../data/design_draft.jpg"
    # test_data_text = "../../data/require_description.md"

    ui_design_draft, original_business_logic, requirement_analysis, requirement_list, Anything_UNCLEAR = get_prd_design(
        prd_ui_draft_path, prd_business_logic_path)

    ui_result = f"[UI 设计草图:]\n {ui_design_draft}\n"
    logic_result = f"[业务逻辑:]\n {original_business_logic}\n"

    prd_analysis = f"[需求分析:]\n {requirement_analysis}\n"

    # 构造所需格式的字符串
    result_output = f"[需求池:]\n {format_requirements(requirement_list)}\n"
    unclear_output = f"[Anything_UNCLEAR:]\n {Anything_UNCLEAR}"

    prd = ui_result + logic_result + prd_analysis + result_output + unclear_output
    return prd, requirement_list


if __name__ == '__main__':
    prd, requirement_list = writePRD()

    print(prd + '\n')
    print(requirement_list)

