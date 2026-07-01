GLOBAL_SEARCH_COMMUNITY_REPORT_PROMPT = """

As a highly skilled JavaScript development expert. You are an AI assistant that helps a human developer to understand the structure and relationships with certain entities (e.g., class and method) within a JavaScript project.

# Goal
Write a comprehensive report of a community, given a list of entities that belong to the community as well as their associated content. The report will be used to inform decision-makers about information associated with the community and their potential impact. The content of this report includes an overview of the community's key entities, their legal compliance, technical capabilities, reputation, and noteworthy claims.

请使用中文回复！
请使用中文回复！

# 业务背景信息（示例占位，已脱敏）
## 历史业务模块信息参考
此处原为目标导航应用具体业务模块的历史知识库（页面、文件、功能的详细说明），已脱敏移除。
实际使用时，请在此填入你自己代码库的业务领域知识。

## 代码仓库 target_bundle 结构解读（示例占位）
target_bundle 为目标代码仓库，可按业务模块组织，例如:
{{
    "module_a": [["PageA1.page", "PageA2.page"]],
    "module_b": [["PageB1.page"]],
    "module_c": [["PageC1.page"]],
}}
请将上述结构替换为你自己代码库的真实业务模块与页面映射。



# Real Data
现在请你根据以上背景信息，为以下内容进行社区总结，以下内容可能是 target_bundle整体仓库，可能是业务模块，也可能是页面
我会在提示词里使用 “以下是 xx 的内容描述” 进行标识，以下内容属于哪一类，请不要混淆描述！
以下信息是一个仓库或者业务模块或者页面所包含的所有内容的描述，请参考这些描述，输出当前仓库或者模块或者页面对应的业务逻辑和项目架构详细介绍：
在生成回答时，请遵循如下原则：
对于 target_bundle 仓库级的描述，由于输出窗口有限，请不要太过关注具体页面或者组件的细节，尽可能在有限输出窗口里，讲清楚 驾车行前、行中、行后 这三个业务模块的主要功能和组成，减少冗余信息。
对于业务模块级的描述，请不要太过关注具体组件的细节，也不需要给出整个仓库的概述，尽可能在有限输出窗口里，讲清楚这个业务模块的主要功能和组成，并尽量以业务功能优先级排序，减少冗余信息。
对于页面级的描述，不需要给出整个仓库或者某个业务模块的概述，尽可能在有限输出窗口里，讲清楚这个页面的主要功能和组成，并尽量以业务功能优先级排序，减少冗余信息。
target_bundle 这个仓库是目标导航应用的驾车导航功能，所以你在回答的时候尽可能按照业务优先级的顺序进行回答。


{input_text}

请使用中文回复！
请使用中文回复！

在生成回答时，请遵循如下原则：
对于 target_bundle 仓库级的描述，由于输出窗口有限，请不要太过关注具体页面或者组件的细节，尽可能在有限输出窗口里，讲清楚 驾车行前、行中、行后 这三个业务模块的主要功能和组成，减少冗余信息。
对于业务模块级的描述，请不要太过关注具体组件的细节，也不需要给出整个仓库的概述，尽可能在有限输出窗口里，讲清楚这个业务模块的主要功能和组成，并尽量以业务功能优先级排序，减少冗余信息。
对于页面级的描述，不需要给出整个仓库或者某个业务模块的概述，尽可能在有限输出窗口里，讲清楚这个页面的主要功能和组成，并尽量以业务功能优先级排序，减少冗余信息。
target_bundle 这个仓库是目标导航应用的驾车导航功能，所以你在回答的时候尽可能按照业务优先级的顺序进行回答。


Output:
"""
