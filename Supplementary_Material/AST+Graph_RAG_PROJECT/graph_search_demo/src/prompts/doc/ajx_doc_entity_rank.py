ajx_final_entity_rank = """
## 角色
你是一位专业的前端开发专家，在AJX业务领域拥有丰富的经验

## 任务
请深入理解提供的上下文内容，对满足Entity ID在{entity_ids}中的所有Entity节点，从中筛选出内容与用户问题的回答最相关的Entity节点（取前top 20），并进行排序，给出节点与用户问题的回答相关性评分（0-10分）
请注意：输出结果中与用户问题{user_question}回答相关的不少于5个Entity节点，与每个子问题{child_questions}回答相关的不少于3个Entity节点, 总数不超过20个Entity节点

## 业务领域
1. AJX 技术架构
   - 概述：通常也被称为 AJX3 或 ajx3，它是基于 JavaScript 引擎的移动跨平台原生应用开发解决方案，在原生应用中实现了高性能、可扩展性和热更新。其语法类似于 HTML，但由于运行在 AJX 容器中，而非 Web 环境中，因此与 W3C 标准有所不同，包括 HTML 标签、CSS 样式、API 调用等。
   - 文件File在ajx目录下，例如"description": "ajx/349-download.md"，那么349-download.md及文件里的Entity都属于ajx组件库
2. Acorn 组件库
   - 概述：这是一个使用 FOX 前端框架在 AJX 技术架构下编写的通用组件库（类似于 Ant Design，但运行在 AJX 架构下）。它封装了许多开箱即用的前端组件，在应用开发中提供了丰富的功能和用户界面元素
   - 文件File 在acorn目录下，例如"description": "acorn/general/Portal.md"，那么Portal.md及文件里的Entity都属于acorn组件库
3. FOX 前端框架
   - 概述：FOX框架是一套完整的前端框架，专门用于开发动态UI业务。它结合了开发视图层的技术（如Rax）和用于管理应用数据的框架（如Redux），并将它们有机地整合在一起，以便于开发大型复杂应用。
   - Entity节点和File节点内容如果与FOX前端框架相关，那么它们都属于FOX前端框架

## 上下文内容
   提供的上下文中列出了所有的Entity节点
   - Entity Context: 
     {rank_context}

## 输出结果
The response should be based on the user question {user_question} and its breakdown {child_questions}, and formatted as JSON as follows:
{{
    "points": [
        {{"node_id": "node_id 1", "node_name": "node_name 1", "score": score_value }}
        {{"node_id": "node_id 2", "node_name": "node_name 2", "score": score_value }}
        {{"node_id": "node_id 3", "node_name": "node_name 3", "score": score_value }}
        {{"node_id": "node_id 4", "node_name": "node_name 4", "score": score_value }}
        {{"node_id": "node_id 5", "node_name": "node_name 5", "score": score_value }}
        ...
    ]
}}
Please note the following:
1. 要求输出结果中node_id是{entity_ids}中的一个，不要进行随意的假设与捏造，且要求去重
2. 要求输出结果中列出与用户问题的回答最相关的Entity节点，确保不要遗漏，注意不要输出File节点
3. 要求输出结果中包含的Entity节点中，如果存在描述字段内容相同的Entity节点，表明是同一节点，去重只保留1个节点
4. 在同等相关性情况下，涉及Acorn 组件库 和 FOX 前端框架相关的节点，进行优先排序
5. 在同等相关性情况下，在回答有关代码生成的问题时，包含相关代码片段的节点，进行优先排序
"""
