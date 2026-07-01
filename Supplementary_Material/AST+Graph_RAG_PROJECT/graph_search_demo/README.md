# Graph Search Demo
面向 AJX 代码 AST 的 Graph Search 框架


## 新业务修改prompt汇总
1. chat_worksapce.py 聊天prompt
2. final_query_entity_extract.py rerank prompt
3. sub_query_extract.py 子问题提取prompt
4. tag_extract.py tag提取prompt
5. get_tag_extract.py 修改page 规则，和 tag_extract 对应

# 启动项目
## 本地启动 rag service
PYTHONPATH=src gunicorn -w 2 -b 0.0.0.0:5001 app:app
## chat (保持不变)  2选1
1. 执行 scripts/xx.sh
2. 执行 launch.json



## Get Started
你可以将 examples 目录下的文件复制到 data 目录进行初始测试
1. 依赖安装
```
// 用不用 conda 都行，看个人习惯
conda create -n graph_search python=3.10
conda activate graph_search
pip install -r requirements.txt

// 如新增依赖，请运行如下命令，更新 requirements.txt
pip install pipreqs
pipreqs ./ --force
```
2. AST -> Knowledge Graph (格式转换、Leiden 社区算法、大模型报告生成)
```
bash scripts/create_knowledge_graph.sh
```
3. 将图数据导入 neo4j（受社区版 neo4j 限制，运行前会先清空已有数据，请慎用！）
```
bash scripts/export_graph_to_neo4j.sh
```
4. 创建索引并保存至向量数据库
```
bash scripts/create_embeddings.sh
```
5. 问答对话测试
```
bash scripts/chat.sh
```

## Graph Search Pipeline
### 数据结构
1. 图结构
* code_graph_*.json
2. 社区结构
* community_report_*.json
### 算法设置
基于微软 GraphRAG 的检索方案进行改进：
1. 数据预处理
    * AST --> Code Graph --> Community Detection --> LLM Reports --> Embedding (with graph metadata) --> Vector DB
2. 检索
    * User Question --> Vector DB --> Top-k Entity
    * Top-k Entity --> Multi Source Graph Context 