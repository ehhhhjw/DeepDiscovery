import os
import re
import json
from datetime import datetime
import subprocess
import traceback
from .index import is_before_days
from types import SimpleNamespace
from typing import Dict


class ClassEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SimpleNamespace):
            return obj.__dict__
        return super().default(obj)


def get_current_branch(repo_path):
    try:
        # 切换到仓库路径
        os.chdir(repo_path)

        # 获取当前分支名称
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()
        return current_branch
    except subprocess.CalledProcessError as e:
        print(f"Failed to get current branch: {e}")
        # 打印完整的异常堆栈信息
        traceback.print_exc()
        return None


# 判断是否在特定分支
def is_on_branch(repo_path, branch_name):
    current_branch = get_current_branch(repo_path)
    if current_branch:
        return current_branch == branch_name
    return False


# 切换分支
def switch_branch(repo_path, branch_name):
    try:
        # 切换到仓库路径
        os.chdir(repo_path)

        status = is_on_branch(repo_path, branch_name)
        if status:
            # print(f"Already on branch: {branch_name}")
            return
        # 执行 git checkout branch_name 命令
        subprocess.run(["git", "checkout", branch_name], check=True)
        # print(f"Switched to branch: {branch_name}")
    except subprocess.CalledProcessError as e:
        # print(f"Failed to switch branch: {e}")
        # 打印完整的异常堆栈信息
        traceback.print_exc()
        pass


# 检查有无冗余信息
def has_useless_info(commit: Dict):
    status = False
    message = commit.message
    if message.startswith("Merge branch"):
        status = True
    return status


# 根据 message 判断是否需要处理此 commit
def include_commit(message):
    _message = message.strip()
    return (
        _message.startswith("feat")
        or _message.startswith("fix")
        or _message.startswith("refactor")
    ) and ("【" in _message or "[" in _message)


# 检查是否有处理信息
def has_process_info(commit: Dict):
    status = False
    message = commit.message
    if include_commit(message):
        status = True
    return status


# 排除的文件
def extend_file(change_type, path):
    # 排除删除的文件
    if change_type == "D":
        return True
    # 如果不是 js 等文件
    if not (
        path.endswith(".js")
        or path.endswith(".jsx")
        or path.endswith(".ts")
        or path.endswith(".tsx")
        or path.endswith(".json")
    ):
        return True


# 是否包含中文
def contains_chinese(text):
    pattern = re.compile(r"[\u4e00-\u9fff]")
    match = pattern.search(text)
    status = match is not None
    return status


# 去除前缀
def remove_prefix(message, prefixes=["feat", "fix", "refactor"]):
    # 构造正则表达式模式
    pattern = r"^(" + "|".join(map(re.escape, prefixes)) + r"):\s*"
    result = re.sub(pattern, "", message)

    # 删除特定垃圾内容
    # 定义正则表达式模式
    pattern_base = r"[【\[]双端[】\]]"
    pattern_digits = r"[【\[]\d+[\]]"
    result = re.sub(pattern_base, "", result)
    result = re.sub(pattern_digits, "", result)
    return result.strip()


# commit 其他排除条件判断
def check_is_extend_commit(commit, config):
    message = commit.message.strip()
    status = False
    # 如果没有中文的 commit 舍弃
    if not contains_chinese(message):
        status = True
    return status


# 根据 llm 去判断原来的 commit 文件是否保留
def handler_files(files, llm_res):
    result = []
    # 模型有时候可能不稳定，需要容错判断
    if len(llm_res["files"]) == 0:
        return files
    for _, file in enumerate(files):
        llm_item = next(x for x in llm_res["files"] if x["name"] == file["name"])
        # llm_item = llm_res["files"][_]
        if llm_item["related"]:
            result.append(
                {**file, "reason": llm_item["reason"], "related": llm_item["related"]}
            )
    return result


# 格式化 commit 文件修改内容
def format_commit_content(content, change_type):
    CHANGE_MAP = {
        "M": "修改文件内容",
        "D": "删除文件内容",
        "A": "新增文件内容",
    }
    content_list = content.split("\n")
    # 去除前 4 行的 git 提示信息
    GIT_PROMPT_LINES_TO_SKIP = 4
    if len(content_list) > GIT_PROMPT_LINES_TO_SKIP:
        content_list = content_list[GIT_PROMPT_LINES_TO_SKIP:]

    content_str = "\n".join(content_list)

    if change_type in CHANGE_MAP:
        change_type_str = f"change_type: {change_type}({CHANGE_MAP[change_type]})."
    else:
        change_type_str = ""
    return f"{change_type_str}\n{content_str}"


def parse_commit_info(repo_path: str, branch_name: str, bundle_name: str, commit):
    author = commit.author.name
    email = commit.author.email
    commit_time = commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S")
    message = commit.message.strip()
    hash = commit.hexsha
    type = message.split(":")[0] if message.find(":") != -1 else "other"
    files = []

    cmd = [
        "git",
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        hash,
    ]
    switch_branch(repo_path=repo_path, branch_name=branch_name)
    # 获取修改过的文件列表，及 change_type（M、D、A）
    result = subprocess.run(cmd, capture_output=True, text=True)
    if len(result.stdout) == 0 or len(result.stderr) > 0:
        return None
    changed_files = result.stdout.strip().split("\n")
    changed_files = [(f.split("\t")[0], f.split("\t")[1]) for f in changed_files]
    for change_type, changed_file in changed_files:
        if extend_file(change_type, changed_file):
            continue
        name = os.path.basename(changed_file)
        diff_cmd = ["git", "diff", hash + "^!", "--", changed_file]
        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True)
        if len(diff_result.stdout) > 0 and len(diff_result.stderr) == 0:
            commit_file = {
                "name": name,
                "path": changed_file,
                "change_type": change_type,
                "content": format_commit_content(diff_result.stdout, change_type),
            }
            files.append(commit_file)
    if len(files) == 0:
        # 如果没有调整 js 等文件，可能为空
        return None
    return {
        "author": author,
        "email": email,
        "date": commit_time,
        "message": message,
        "hash": hash,
        "type": type,
        "bundle_name": bundle_name,
        "files": files,
    }
