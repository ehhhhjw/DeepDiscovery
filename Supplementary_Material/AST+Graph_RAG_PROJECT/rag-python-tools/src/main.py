# import os
# import sys
# root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))
# # 添加绝对引用的工作目录
# sys.path.append(os.path.join(root))
import asyncio
import argparse
import configparser
from const.dir import CONFIG_DIR
from commit_tool import CommitTool


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


async def main(config, args):
    tools_map = {"commit": CommitTool}
    evaluator = tools_map[args.tool]
    app_info = config["app_info"]
    if not evaluator:
        raise ValueError(f"tool {args.tool} not found.")
    evaluator = evaluator(config=config[args.tool], app_info=app_info, args=args)
    await evaluator.run()


if __name__ == "__main__":
    config = get_config()
    parser = argparse.ArgumentParser(description="parameters for rag_tools app")
    parser.add_argument(
        "--tool", type=str, required=True, help="工具名称。", choices=["commit"]
    )
    parser.add_argument(
        "--action",
        type=str,
        default="generate",
        help="工具行为。",
        choices=["generate", "graph"],
    )

    parser.add_argument(
        "--api",
        action="store_true",
        help="供外层api调用",
    )
    parser.add_argument("--repo_dir", type=str, help="仓库绝对路径")
    parser.add_argument("--branch", type=str, help="分支名称")
    parser.add_argument("--start_date", type=str, help="提取commit的起始时间")
    args = parser.parse_args()

    if args.api:
        config[args.tool]["repo"] = args.repo_dir
        config[args.tool]["branch"] = args.branch
        config[args.tool]["start_date"] = args.start_date

    asyncio.run(main(config, args))
