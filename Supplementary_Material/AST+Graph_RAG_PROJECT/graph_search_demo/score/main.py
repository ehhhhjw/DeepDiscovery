import os
import sys

root = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
)
# 添加绝对引用的工作目录
sys.path.append(os.path.join(root))

from datetime import datetime
import argparse
import asyncio
import traceback
from typing import Dict, List
from const import CONFIG_DIR, SOURCE_DATA_DIR
import configparser
from utils import get_dict_value, generate_random_string
from utils.excel import read_excel_file_to_list
from chat import Chat
from scoring_evaluator import ScoringEvaluator
from scoring_evaluator import ScoringEvaluatorDoc
from constants import ScoreType

def get_config():
    config = configparser.ConfigParser()
    # local 会覆盖默认配置中相同字段
    config.read(
        [
            CONFIG_DIR / "config.ini",
            CONFIG_DIR / "local.config.ini",
        ]
    )
    return config


# 运行获取 chat 问答
async def chat_script(config: Dict, excel_list: List, args, mark: str = None):
    excel_answer_range = get_dict_value(config, "source.excel_answer_range")
    excel_answer_range_arr = []
    if excel_answer_range:
        excel_answer_range_arr = [
            int(value) for value in excel_answer_range.split("-")
        ]
    if len(excel_answer_range_arr) == 2:
        excel_list = excel_list[
            excel_answer_range_arr[0] : excel_answer_range_arr[1]
        ]
    print("excel_list length: ", len(excel_list))
    evaluator = Chat(config=config["chat"], excel_list=excel_list, mark=mark, args=args)
    await evaluator.run()


# 获取评分
async def score_script(config: Dict, excel_list: List, args, mark: str = None):
    if not mark and "mark" not in config["score"]:
        raise Exception("mark not found in config.score")
    # 评分会依据 mark 读取 chat 结果
    mark = mark or config["score"]["mark"]
    # 并发数
    max_concurrent_tasks = config["score"].get("max_concurrent_tasks", None)

    async def score_script_inner(inner_type):
        classExecutor = ScoringEvaluator
        if inner_type == ScoreType.DOCS:
            classExecutor = ScoringEvaluatorDoc
        evaluator = classExecutor(
            mark=mark,
            config=config,
            excel_list=excel_list,
            max_concurrent_tasks=max_concurrent_tasks,
            args=args,
            score_type=inner_type
        )
        await evaluator.run()

    if args.exe_type == "doc":
        await score_script_inner(ScoreType.DOCS)
    elif args.exe_type == "code_doc":
        await score_script_inner(ScoreType.CODE)
        await score_script_inner(ScoreType.DOCS)
    else:
        await score_script_inner(ScoreType.CODE)


# chat 并且评分
async def chat_and_score_script(config: Dict, excel_list: List, args):
    formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    default_mark = f"{formatted_datetime}_{generate_random_string(10)}"
    mark = get_dict_value(config, "chat.mark", default_mark)
    await chat_script(
        config=config, excel_list=excel_list, args=args, mark=mark
    )
    await score_script(
        config=config, excel_list=excel_list, args=args, mark=mark
    )


# 获取 excel 数据评分
async def score_excel_script(config: Dict, excel_list: List, mark: str, args):
    if not mark and "mark" not in config["score"]:
        raise Exception("mark not found in config.score")
    mark = mark or config["score"]["mark"]

    row_index = int(args.row_index)
    answer_type = args.answer_type

    async def score_excel_script_inner(inner_type):
        classExecutor = ScoringEvaluator
        if inner_type == "doc":
            classExecutor = ScoringEvaluatorDoc
        evaluator = classExecutor(
            mark=mark, config=config, excel_list=excel_list, args=args, score_type=inner_type
        )
        result, error = await evaluator.execute_excel_row(
            row_index=row_index, answer_type=answer_type
        )
        if error:
            traceback.print_exc()
            print("error: ", error)
        print(result)

    if args.exe_type == "doc":
        await score_excel_script_inner(ScoreType.DOCS)
    elif args.exe_type == "code_doc":
        await score_excel_script_inner(ScoreType.CODE)
        await score_excel_script_inner(ScoreType.DOCS)
    else:
        await score_excel_script_inner(ScoreType.CODE)

    classExecutor = ScoringEvaluator
    if args.exe_type == "doc":
        classExecutor = ScoringEvaluatorDoc
    evaluator = classExecutor(
        mark=mark, config=config, excel_list=excel_list,args=args
    )
    result, error = await evaluator.execute_excel_row(
        row_index=row_index, answer_type=answer_type
    )
    if error:
        traceback.print_exc()
        print("error: ", error)
    print(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="parameters for score app")
    parser.add_argument(
        "--script_type",
        default="chat",
        choices=["chat", "score", "score_excel", "chat_score"],
        type=str,
        help="脚本类型。可选值：chat、score、score_excel",
    )

    # 与 "score_excel" 相关的参数
    parser.add_argument(
        "--row_index",
        default=0,
        type=int,
        help="Excel 文件行索引（从0开始，仅在 script_type=score_excel 时有效）",
    )
    parser.add_argument(
        "--answer_type",
        default="answer",
        type=str,
        choices=["answer", "aone_copilot", "tongyi"],
        help="回答的种类。可选值：answer、aone_copilot、tongyi，仅在 script_type=score_excel 时有效",
    )

    parser.add_argument(
        "--exe_type",
        default="code",
        type=str,
        choices=["code", "doc","code_doc"],
        help="执行code | 执行doc | 执行code_doc(仅支持script_type=chat)",
    )

    parser.add_argument(
        "--chat_script_path",
        default="./scripts/chat_workspace.sh",
        type=str,
        choices=["./scripts/chat_workspace.sh", "./scripts/chat_doc.sh", "./scripts/chat.sh"],
        help="执行code | 执行doc",
    )


    args = parser.parse_args()
    print("args: ", args)

    # 配置文件
    config = get_config()
    # 获取 excel 问题列表
    excel_list = read_excel_file_to_list(
        SOURCE_DATA_DIR / config["source"]["excel_file"],
        config["source"]["sheet_name"],
    )

    if args.script_type == "score":
        asyncio.run(
            score_script(config=config, excel_list=excel_list, args=args)
        )
    elif args.script_type == "score_excel":
        asyncio.run(
            score_excel_script(config=config, excel_list=excel_list, args=args)
        )
    elif args.script_type == "chat_score":
        asyncio.run(
            chat_and_score_script(
                config=config, excel_list=excel_list, args=args
            )
        )
    else:
        asyncio.run(
            chat_script(config=config, excel_list=excel_list, args=args)
        )
