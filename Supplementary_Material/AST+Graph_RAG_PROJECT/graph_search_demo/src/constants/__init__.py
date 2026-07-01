# from enum import Enum
from datetime import datetime
from pathlib import Path
from enum import Enum

DOCS_COLLECTION_NAMES = [
    "docs_name",
    "docs_report",
    "docs_comment",
    "docs_description",
]
# commit 检索的字段
COMMIT_COLLECTION_NAMES = ["message"]

# 技术文档 检索的字段
TECH_DOC_COLLECTION_NAMES = [
    "tech_doc_title",
    "tech_doc_sub_summary",
    "tech_doc_entity_desc",
    "tech_doc_summary",
]

# 默认 code 模式检索的字段
COLLECTION_NAMES = ["name", "report", "comment", "description", "short_report"]
QAINFO_NAMES = "question_answer"
QADATA_URL = "https://your-llm-cache-proxy.example.com/graph-search/log/get?last_id="

# 设置rag向量匹配时(包含 rerank + chat)对应node的评分上限
COLLECTION_SCORE_LIMIT = {
    COLLECTION_NAMES[0]: 1.6,
    COLLECTION_NAMES[1]: 1.2,
    COLLECTION_NAMES[2]: 1.2,
    COLLECTION_NAMES[3]: 1.6,
    COLLECTION_NAMES[4]: 1.1,
    COMMIT_COLLECTION_NAMES[0]: 1.1,
    QAINFO_NAMES: 0.7,  # Q&A 过滤分数
    TECH_DOC_COLLECTION_NAMES[0]: 0.9,
    TECH_DOC_COLLECTION_NAMES[1]: 0.9,
    TECH_DOC_COLLECTION_NAMES[2]: 0.9,
}
SUB_COLLECTION_SCORE_LIMIT = {
    COLLECTION_NAMES[0]: 1.5,
    COLLECTION_NAMES[1]: 1.2,
    COLLECTION_NAMES[2]: 1.2,
    COLLECTION_NAMES[3]: 1.6,
    COLLECTION_NAMES[4]: 1.1,
    COMMIT_COLLECTION_NAMES[0]: 1.1,
    QAINFO_NAMES: 0.7,  # Q&A 过滤分数
    TECH_DOC_COLLECTION_NAMES[0]: 0.9,
    TECH_DOC_COLLECTION_NAMES[1]: 0.9,
    TECH_DOC_COLLECTION_NAMES[2]: 0.9,
}
# 定义没部分占 tokens 的比例上限，除了 entity 以外，其他的如果放不开一个 则为空
# 如果分开定义的窗口和 > 总窗口，按 entity > class > community > Q&A > supplementary 的顺序进行计算，知道满足最大窗口限制
local_search_settings = {
    "entity_max_tokens": 90 * 1000,
    "class_max_tokens": 90 * 1000,
    "community_max_tokens": 90 * 1000,
    "relationship_max_tokens": 90 * 1000,
    "qa_context_max_tokens": 90 * 1000,
    "supplementary_max_tokens": 90 * 1000,
}
# code find_layer 的层级，设置为 n 会上下各追溯 n 个相关联的节点
code_find_layer_depth = 1
MAX_RELATION_MESSAGE_NUM = 100


NODE_CONTENT_KEYS = ["name", "report", "comment", "description", "code_comment"]
EXTRACT_CONTENT_KEYS = ["name", "report", "comment"]


class FindType:
    CLASS = "class"
    METHOD = "method"


class EdgeType:
    DEPENDENT = "dependent"
    CHILD = "child"
    EXTENDS = "extends"
    CALL = "call"


class EmbeddingType:
    CODE = "code"
    DOCS = "docs"
    COMMIT = "commit"
    TECH_DOCS = "tech_docs"


class SearchType:
    CODE = "code"
    DOCS = "docs"


class ContextType:
    RERANK = "rerank"
    CHAT = "chat"


formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
# 项目根目录
ROOT_PATH = Path(__file__).parent.parent.parent
# 当次执行的 log 目录
LOG_DIR_PATH = ROOT_PATH / f"log/{formatted_datetime}"
# print("ROOT_PATH: ", ROOT_PATH, LOG_DIR_PATH)

# 业务模块 -> 页面 的映射示例（已脱敏，请按你自己的代码库填写）
DRIVE_PAGE_MAP = {
    "module_a": ["PageA1.page", "PageA2.page"],
    "module_b": ["PageB1.page"],
    "module_c": ["PageC1.page"],
}

# 业务模块 -> 模块中文名 的映射示例（已脱敏）
DRIVE_MODULE_MAP = {
    "module_a": "业务模块A",
    "module_b": "业务模块B",
    "module_c": "业务模块C",
}


class RAG_STRATEGY(Enum):
    normal = 1  # embedding + bm25 分开召回，结果拼接到一起
    hybrid_normal = 2  # embedding + bm25 分数拉平
    hybrid_plus = 3  # 召回结果混合算分，按策略补充 parent class 节点




# 图谱中的关系权重，后续随着bundle的添加可以新增bundle权重
DEPENDENCE_POWER = 0.25 # 依赖关系权重
CALL_POWER = 1 # 调用关系权重
EXTEND_POWER = 1 # 继承关系权重
CHILDREN_POWER = 0.75 # 子类关系权重, 方法指向类与类指向方法的权重值相同
PAGELIST_POWER = 0.1 # 页面关系权重

# Leidan算法的权重
LEIDAN_POWER_LIST = [1, 2, 4] # L0, L1, L2层权重

# 文件夹信息的权重，根据目标文件夹如your_drive_bundle下的ajx_module与scr可以作为0层文件夹
FOLDER_POWER_LIST = [0.25, 0.5, 1, 2, 4] # L0, L1, L2, L3, L4层文件夹权重，由于L0，L1的噪声太大，暂定从L2级文件夹开始算

# QA信息的权重
QA_RERANK_POWER_LIST = [2, 1, 0.5, 0.25] # 根据rerank顺序，越靠前权重越大，前三个分别为4, 3, 2，后面的节点都为1
QA_COMMUNITY_POWER = 0.5 # QA信息中的社区权重，用到了这个社区，并且起了正向反馈，说明有用

# Commit信息的权重
COMMIT_POWER = 0.1

# 领域知识信息权重
DOMAIN_KNOWLEDGE_POWER = 2

# 根据文件夹信息添加边的阈值，一个文件夹下的最大文件数量
MAX_FOLD_FILE_NUM = 10000000

# 根据Commit信息添加边的阈值，一个Commit下的最大关联文件数量
MAX_COMMIT_FILE_NUM = 10000000

# 过滤边的阈值, 阈值越大社区中的节点越相关
FILTER_THRESHOLD = [11, 12, 13]

# 不同级别的社区中应该包含的最少节点数
MIN_COMMUNITY_SIZE = [20, 10, 4]


# 衰退范围，当衰退值小于（1 - DEGRADATION_SCOPE）* FILTER_THRESHOLD时，剪枝
DEGRADATION_SCOPE = 0.4 # 值越小，召回的越相关

# 衰退权重，第n层为DEGRADATION_WEIGHT^2
DEGRADATION_WEIGHT = 0.7 # 值越大，召回的越相关


MAX_RETRY_ATTEMPTS = 10
WAIT_SECONDS = 13.5

# 不符合要求的文件夹
FILTER_NODE_MODULE = ["node_modules", "output", ".ast_data", ".venv", ".vscode", "DotTrans", "tree_sitter", "DS_Store"]

# 符合要求的后缀信息
SUITABLE_EXTENSION = ["js", "ts", "jsx", "tsx", "page"]
