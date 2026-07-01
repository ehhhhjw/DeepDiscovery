# AST + Graph RAG Project

面向前端代码(AJX / JavaScript / TypeScript)的 **AST + 图谱 RAG** 工程集合。

本仓库通过对源码做 AST 解析,抽取类/方法/文件实体及其依赖、调用、继承等关系,构建代码知识图谱,
再借鉴微软 GraphRAG 的思路做社区检测、大模型社区报告生成、向量化与检索,最终提供面向代码理解与
问答的检索增强(RAG)能力。

> 说明:本仓库中的示例数据、密钥、内部域名、业务标识等均已脱敏处理,代码中出现的 `target_bundle`、
> `PageA1.page`、`ExampleAgent` 等为占位名称,使用时请替换为你自己代码库的真实信息。

---

## 目录结构与三个子项目

```
AST+Graph_RAG_PROJECT/
├── AST_Tree_Graph/      # 1. AST 解析与代码图谱构建(底层)
├── rag-python-tools/    # 2. AST/Commit/总结 工具集(数据加工)
└── graph_search_demo/   # 3. Graph Search 检索框架与问答服务(上层)
```

### 整体数据流

```
源码仓库
  │  (AST 解析、实体与关系抽取)
  ▼
AST_Tree_Graph / rag-python-tools   ──►  code_graph_*.json(图结构) + commit/summary 等加工数据
  │  (格式转换 → Leiden 社区检测 → LLM 社区报告 → 带图元数据的 Embedding → 向量库)
  ▼
graph_search_demo                   ──►  Neo4j 图库 + 向量数据库(chroma)
  │  (用户提问 → 向量召回 Top-k 实体 → 多源图上下文 → LLM 回答)
  ▼
代码问答 / 代码理解服务(Flask + gunicorn)
```

---

## 1. AST_Tree_Graph —— AST 解析与代码图谱构建

### 职能
流水线最底层。基于 `tree-sitter` 对前端源码做语法解析,抽取类、方法、函数、文件等实体,
并识别依赖(dependent)、子节点(child)、继承(extends)、调用(call)等关系,
产出图结构数据(DotTrans / JSON),可进一步导入 Neo4j。

### 关键内容
- 根目录流程脚本(按序执行):
  - `step1_get_relation_entity.py` —— 抽取实体与关系
  - `step2_get_file_description.py` —— 生成文件级描述
  - `step3_get_class_and_func_json.py` —— 汇总类与函数为 JSON
  - `new_step1_get_totoal_information.py` —— 汇总整体信息(新版入口)
- `tree_sitter/` —— 底层 AST 抽取与图构建工具:
  - `step1_Get_class_information.py` → `step2_AST_exact_class_func_newest.py` →
    `step3_Combine_class_entity_information.py` → `step4_Get_code_comment_into_json.py` →
    `step5_Fill_code_and_comment_into_json_file.py`(`tree_sitter/run.sh` 串起了这 5 步)
  - `tool_leiden_calculate.py` —— Leiden 社区算法
  - `tool_get_code_embedding.py` —— 代码片段向量化示例
  - `tool_trans_jsonfile_into_neo4j.py` / `tool_new_trans_jsonfile_into_neo4j.py` —— 图数据导入 Neo4j
  - `const.py` —— 路径、根节点等配置
- `tree-sitter-javascript/` —— tree-sitter 的 JS 语法支持

### 使用方法
```bash
cd AST_Tree_Graph
# 依赖见 package.json / poetry.lock;tree-sitter 语法库需先构建(参见 tree_sitter/build.py)

# 运行底层 AST → 图谱 5 步流程
bash tree_sitter/run.sh
# 或按需逐步运行根目录 step 脚本
python3 step1_get_relation_entity.py
python3 step2_get_file_description.py
python3 step3_get_class_and_func_json.py
```
> 前置约束(见 `README.txt`):要求被解析仓库内所有文件名互不重复。
> 运行前请在 `const.py` 及各 step 脚本中把目标仓库路径、根节点页面等替换为你自己的配置。

---

## 2. rag-python-tools —— AST / Commit / 总结 工具集

### 职能
数据加工层。以 poetry 管理的工具集,提供 commit 记录提取(并可转为图结构)、AST 解析客户端、
以及基于大模型的代码实体总结(summary)能力,为图谱补充 commit、文件总结等多源信息。

### 关键内容
- `src/main.py` —— 命令行入口,通过 `--tool` / `--action` 选择工具
- `src/commit_tool/` —— commit 提取与转换
- `src/ast_tool/` —— AST 解析客户端及 tree-sitter 构建产物(`build/my-languages.so`)
- `src/chat/` —— 大模型调用与 prompt(`chat/prompt/commit.py` 等)
- `src/config/config.ini` —— 配置模板(仓库路径、分支、密钥等)
- `summary/` —— 代码实体总结脚本与 few-shot prompt(`summary.py`、`prompts.txt`、
  `summary_test*.py`),输入放在 `summary/input/`

### 使用方法
```bash
cd rag-python-tools
# 1) 环境(pyenv + poetry)
pyenv local 3.10.14
poetry env use 3.10.14
poetry install

# 2) 复制配置并按需修改
cp ./src/config/config.ini ./src/config/local.config.ini

# 3) commit 提取工具
python ./src/main.py --tool commit                # 提取 commit 记录
python ./src/main.py --tool commit --action graph # 转换为图结构
# 可选参数:--repo_dir <仓库绝对路径> --branch <分支> --start_date <起始时间>

# 4) 代码总结(summary)
python ./summary/summary.py
```

---

## 3. graph_search_demo —— Graph Search 检索框架与问答服务

### 职能
流水线上层应用。借鉴微软 GraphRAG:把代码图谱做 Leiden 社区检测、LLM 生成社区报告、
连同图元数据一起 Embedding 写入向量库;检索时由用户问题召回 Top-k 实体并补充多源图上下文,
最终由大模型生成回答。对外提供 Flask + gunicorn 的 RAG 问答服务,并支持 docker-compose 部署。

### 关键内容
- `src/app.py` —— 服务入口(WSGI `app`)
- `src/cli.py` —— 命令行入口
- `src/graph_models/` —— 图谱建模、社区报告、tag 抽取(`get_global_search_community.py`、
  `get_tag_extract.py` 等)
- `src/index/` —— 索引/向量化构建
- `src/query/` —— 检索与召回
- `src/prompts/` —— 各类提示词(`chat.py`、`tag_extract.py`、`sub_query_extract.py`、
  `final_query_entity_extract.py`、`global_search_*.py`、`prd_to_task.py` 等)
- `src/constants/` —— 评分阈值、权重、社区参数、业务模块映射(占位示例)等全局配置
- `scripts/` —— 各阶段一键脚本;`docker-compose*.yaml` / `Dockerfile` —— 容器化部署
- `data/` —— 运行所需数据目录(可将示例数据复制进来测试)

### 使用方法
```bash
cd graph_search_demo
# 1) 依赖(conda 可选)
conda create -n graph_search python=3.10 && conda activate graph_search
pip install -r requirements.txt   # 或使用 pyproject.toml / poetry

# 2) AST → 知识图谱(格式转换 + Leiden 社区 + LLM 报告)
bash scripts/create_knowledge_graph.sh

# 3) 导入 Neo4j(注意:社区版会先清空已有数据,慎用)
bash scripts/export_graph_to_neo4j.sh

# 4) 创建索引并写入向量数据库
bash scripts/create_embeddings.sh

# 5) 问答测试
bash scripts/chat.sh

# 启动 RAG 服务
PYTHONPATH=src gunicorn -w 2 -b 0.0.0.0:5001 app:app
# 或容器部署
docker-compose up -d
```

---

## 运行前必做的配置替换
- 各项目中的大模型 / Embedding **API Key、BASE_URL**(占位为 `YOUR_*` 与 `*.example.com`)
- **Neo4j** 连接地址与密码(占位为 `YOUR_NEO4J_PASSWORD`)
- 目标代码仓库名与路径(占位为 `target_bundle`、`/path/to/project`)
- `graph_search_demo/src/constants/__init__.py` 中的业务模块映射
  (`DRIVE_PAGE_MAP` / `DRIVE_MODULE_MAP`,占位为 `module_a` / `PageA1.page`)
- 各 prompt 中的「业务领域知识」占位段落,替换为你自己代码库的领域说明
