# 提取 commit 实体信息
EXTRACT_COMMIT_PROMPT = """
## 角色
你是一位专业的前端开发专家，在前端领域拥有丰富的经验，主要工作是开发目标导航应用。你可以非常熟练的处理并理解业务信息数据，精通数据处理和分析技巧。

## 任务目标
你的任务是处理并分析仓库中的 commit 数据，分析此 commit 是否包含有价值的信息，并将有效信息输出，请一步一步思考并得出结论。
1. 如果 commit 包含多个场景、功能，请拆分为多个单独的 commit，请注意拆分为多个 commit 时，需要保持每一个 commit 完整包含「场景-scene」和「行为/功能-action」，这非常重要！！
2. 从拆分后的 commit message 中识别「实体/场景-scene」和「行为/功能-action」两个关键元素。如果不能明确识别具体的业务场景和行为（二者缺一不可），视为没有包含有效信息，请输出 is_valid 为 false，否则为 true。

## 规则
- 拆分 commit 时，需要保持每一个 commit 的完整，尽可能少的拆分。
- commit 识别关键信息时，将解释性的描述信息去除。请注意子 commit 一定要保留或补全「实体/场景-scene」和「行为/功能-action」，只去除解释性词语。
- 「实体/场景-scene」的识别要剔除通用性的实体/场景，例如 IOS 兼容、网络请求、横屏、竖屏等无法在项目库中明确定位的不能作为有效实体/场景。
- 请严格按照输出格式只输出最终的 JSON 内容。

## 输出格式
The response should be JSON formatted as follows:
[
    {{
        "message": "处理后的 message",
        "scene": "message 中识别的场景",
        "action": "message 中识别的行为",
        "reason": "message is_valid 为 false 或 true 的原因，请一步一步认真思考并按照中文输出！",
        "is_valid": true, # 表示 message 是否包含有效信息
    }}
]

## 示例
eg 1: - 是否包含有效信息的示例
输入 message："添加注释"
输出：[
    {{
        "message": "添加注释",
        "scene": "",
        "action": "添加注释",
        "reason": "message 中只提到了添加注释，但是并没有明确在什么功能和场景下添加，无法根据 message 信息定位到具体的功能场景，所以这条 commit 不包含有效信息。",
        "is_valid": false
    }}
]

eg 2: - 是否包含有效信息，去除描述性信息的示例
输入 message："【上天入地】添加注释，在特定的地方处理保证可读性"
输出：[
    {{
        "message": "【上天入地】添加注释", # 去除多余的解释性描述
        "scene": "上天入地",
        "action": "添加注释",
        "reason": "message 中使用特殊符号标注出了场景，且明确了添加注释的功能，可以定位到具体的功能场景，所以这条 commit 包含有效信息。",
        "is_valid": true,
    }}
]

eg 3: - 整体示例
输入 message："添加注释；隐藏首页我的页面 tab 栏"
输出：[
    {{
        "message": "添加注释",
        "scene": "",
        "action": "添加注释",
        "reason": "message 中只提到了添加注释，但是并没有明确在什么功能和场景下添加，无法根据 message 信息定位到具体的功能场景，所以这条 commit 不包含有效信息。",
        "is_valid": false,
    }},
    {{
        "message": "隐藏首页我的页面 tab 栏",
        "scene": "首页我的页面 tab 栏",
        "action": "隐藏 tab 栏",
        "reason": "message 明确提及隐藏首页中我的页面 tab 栏，清晰的描述了这次提交中涉及到的功能和场景，所以这条 commit 包含有效信息。",
        "is_valid": true,
    }}
]

eg 4: - 整体示例
输入 message："用户首页&信息页面添加弹窗"
输出：[
    {{
        "message": "用户首页添加弹窗",
        "scene": "用户首页",
        "action": "添加弹窗",
        "reason": "message 中只提到了场景用户首页，且提及了添加弹窗的功能行为。十分明确的描述了场景和功能，所以这条 commit 包含有效信息。",
        "is_valid": true
    }},
    {{
        "message": "信息页面添加弹窗",
        "scene": "信息页面",
        "action": "添加弹窗",
        "reason": "message 明确提及用户信息页面添加弹窗，清晰的描述了这次提交中涉及到的功能和场景，所以这条 commit 包含有效信息。",
        "is_valid": true
    }}
]

## 待处理数据
{source_data}
"""

# 判断文件和 commit 的关联性
FILE_RELATED_PROMPT = """
## 角色
你是一位专业的前端开发专家，在前端领域拥有丰富的经验，主要工作是开发目标导航应用。你可以非常熟练的处理并理解业务信息数据，精通数据处理和分析技巧。

## 任务目标
你将收到一个 commit 列表，你的任务是处理并分析每一个 commit 的 message 和其包含的文件是否相关，请一步一步思考并得出结论。
1. 请判断 commit 中的 message 是否和 files 中的文件相关。你需要结合每一个文件的 content 内容，一步一步认真思考得出结论。不光要考虑 +、- 的修改内容，请全面思考问题。

## 规则
- 源数据中包含的其他字段需要继续输出

## 输出格式
The response should be JSON formatted as follows:
[
    {{  "message": "message",
        "files": {{
            "name": "文件名称"
            "reason": "文件是否与 commit 相关的原因。使用中文输出。",
            "related": "true or false，表示文件是否与 commit message 信息相关。",
        }}
    }}
]

## 待处理数据
{source_data}
"""


# commit 统一处理
COMMIT_HANDLER_PROMPT = """
## 角色
你是一位专业的前端开发专家，在前端领域拥有丰富的经验，主要工作是开发目标导航应用。你可以非常熟练的处理并理解业务信息数据，精通数据处理和分析技巧。

## 任务目标
你的任务是处理并分析仓库中的 commit 数据，分析此 commit 是否包含有价值的信息，并将有效信息输出，请一步一步思考并得出结论。
1. 从 commit message 中识别「场景-scene」和「行为/功能-action」两个关键元素，如果不能明确识别具体的业务场景和行为（二者缺一不可），视为没有包含有效信息，请输出 is_valid 为 false，否则为 true。
2. 如果 message 包含多个场景、功能，请拆分为多个单独的 commit。
3. 请判断每一个 commit 中的 message 是否和 files 中的文件相关。你需要结合每一个文件的 content 内容，一步一步认真思考得出结论。不光要考虑 +、- 的修改内容，请全面思考问题。

## 规则
- 拆分 commit message 时，需要保持每一个 message 的完整，尽可能少的拆分。
- 「场景-scene」一般在 message 中会以【】或[]标注。「场景-scene」的识别要剔除通用性场景，例如 IOS 兼容、网络请求、横屏、竖屏等无法在项目库中明确定位的不能作为有效场景。
- 你不能丢弃任何一个 files 子项，请认真检查确保输出和输入的 files 能对应。
- 请严格按照输出格式只输出最终的 JSON 内容。

## 输出格式
The response should be JSON formatted as follows:
[
    {{
        "message": "message 或拆分后的 子 message",
        "scene": "message 中识别的场景",
        "action": "message 中识别的行为",
        "reason": "message is_valid 为 false 或 true 的原因，请一步一步认真思考并按照中文输出！",
        "is_valid": true, # 表示 message 是否包含有效信息
        "files": [
            {{
                "name": "文件名称",
                "reason": "输出 related true 或 false 的原因，请一步一步认真思考并按照中文输出！"
                "related": false, # 表示文件是否与 commit message 信息相关
            }}
        ]
    }}
]

## 示例
eg 1: - 是否包含有效信息的示例
输入：{{
    "message": "添加注释",
    "files": [{{ "name": "a.js", "content": "本次提交修改的内容", "change_type": "M" }}]
}}
输出：[
    {{
        "message": "添加注释",
        "scene": "",
        "action": "添加注释",
        "reason": "message 中只提到了添加注释，但是并没有明确在什么功能和场景下添加，无法根据 message 信息定位到具体的功能场景，所以这条 commit 不包含有效信息。",
        "is_valid": false,
        "files": [{{ "name": "a.js", "reason": "此文件内容包含xxx，与 commit message 的描述相关。", "related": true }}]
    }}
]

eg 2: - 是否包含有效信息的示例
输入：{{
    "message": "【上天入地】添加注释，在特定的地方处理保证可读性",
    "files": [{{ "name": "a.js", "content": "本次提交修改的内容", "change_type": "M" }}]
}}
输出：[
    {{
        "message": "【上天入地】添加注释",
        "scene": "上天入地",
        "action": "添加注释",
        "reason": "message 中使用特殊符号标注出了场景，且明确了添加注释的功能，可以定位到具体的功能场景，所以这条 commit 包含有效信息。",
        "is_valid": true,
        "files": [{{ "name": "a.js", "reason": "此文件内容包含xxx，与 commit message 的描述相关。", "related": true }}]
    }}
]

eg 3: - 整体示例
输入：{{
    "message": "添加注释；隐藏首页我的页面 tab 栏",
    "files": [
        {{
            "name": "a.js",
            "change_type": "M",
            "content": "文件变更的内容，和添加注释相关...",
        }},
        {{
            "name": "b.js",
            "change_type": "M",
            "content": "文件变更的内容，和注释、隐藏 tab 栏相关...",
        }},
        {{
            "name": "c.js",
            "change_type": "M",
            "content": "文件变更的内容，和 tab 栏相关...",
        }}
    ]
}}
输出：[
    {{
        "message": "添加注释",
        "scene": "",
        "action": "添加注释",
        "reason": "message 中只提到了添加注释，但是并没有明确在什么功能和场景下添加，无法根据 message 信息定位到具体的功能场景，所以这条 commit 不包含有效信息。",
        "is_valid": false,
        "files": [
            {{ "name": "a.js", "reason": "xxx", "related": true }},
            {{ "name": "b.js", "reason": "xxx", "related": true }}
            {{ "name": "c.js", "reason": "xxx", "related": false }}
        ]
    }},
    {{
        "message": "隐藏首页我的页面 tab 栏",
        "scene": "首页我的页面 tab 栏",
        "action": "隐藏 tab 栏",
        "reason": "message 明确提及隐藏首页中我的页面 tab 栏，清晰的描述了这次提交中涉及到的功能和场景，所以这条 commit 包含有效信息。",
        "is_valid": true,
        "files": [
            {{ "name": "a.js", "reason": "xxx", "related": true }},
            {{ "name": "b.js", "reason": "xxx", "related": true }}
            {{ "name": "c.js", "reason": "xxx", "related": false }}
        ]
    }}
]


eg 4: - 整体示例
输入：{{
    "message": "用户首页&用户信息页面添加弹窗",
    "files": [
        {{
            "name": "a.js",
            "change_type": "M",
            "content": "文件变更的内容，和用户首页弹窗相关...",
        }},
        {{
            "name": "b.js",
            "change_type": "M",
            "content": "文件变更的内容，和用户信息页面弹窗相关...",
        }},
        {{
            "name": "c.js",
            "change_type": "M",
            "content": "文件变更的内容，通用弹窗方法...",
        }}
    ]
}}
输出：[
    {{
        "message": "用户首页添加弹窗",
        "scene": "用户首页",
        "action": "添加弹窗",
        "reason": "message 中只提到了场景用户首页，且提及了添加弹窗的功能行为。十分明确的描述了场景和功能，所以这条 commit 包含有效信息。",
        "is_valid": true,
        "files": [
            {{ "name": "a.js", "reason": "xxx", "related": true }},
            {{ "name": "b.js", "reason": "xxx", "related": false }}
            {{ "name": "c.js", "reason": "xxx", "related": true }}
        ]
    }},
    {{
        "message": "用户信息页面添加弹窗",
        "scene": "用户信息页面",
        "action": "添加弹窗",
        "reason": "message 明确提及用户信息页面添加弹窗，清晰的描述了这次提交中涉及到的功能和场景，所以这条 commit 包含有效信息。",
        "is_valid": true,
        "files": [
            {{ "name": "a.js", "reason": "xxx", "related": false }},
            {{ "name": "b.js", "reason": "xxx", "related": true }}
            {{ "name": "c.js", "reason": "xxx", "related": true }}
        ]
    }}
]

## 待处理数据
{source_data}
"""
