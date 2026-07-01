# 文件目录
from pathlib import Path


# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"

# 日志路径
LOG_DIR = ROOT_DIR / ".log"
# 待处理数据路径
DATA_DIR = ROOT_DIR / ".data"
# 输出数据路径
OUTPUT_DIR = ROOT_DIR / ".output"
# 配置文件路径
CONFIG_DIR = SRC_DIR / "config"


# TAG commit 相关
commit_mark = "commit"
COMMIT_DIR = SRC_DIR / commit_mark

COMMIT_LOG_DIR = LOG_DIR / commit_mark

COMMIT_OUTPUT_DIR = OUTPUT_DIR / commit_mark

COMMIT_DATA_DIR = DATA_DIR / commit_mark


# TAG ast 相关
ast_mark = "ast"
AST_DIR = SRC_DIR / ast_mark

AST_OUTPUT_DIR = OUTPUT_DIR / ast_mark

AST_DATA_DIR = DATA_DIR / ast_mark
AST_SOURCE_CODE_DIR = AST_DATA_DIR / "source_code"

AST_LOG_DIR = LOG_DIR / ast_mark

AST_TREE_SITTER_DIR = AST_DIR / "tree_sitter"


# print("ROOT_DIR", ROOT_DIR, SRC_DIR)
