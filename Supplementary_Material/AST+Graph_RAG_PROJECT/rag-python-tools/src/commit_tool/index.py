import git
import json
import traceback
from datetime import datetime
from tqdm import tqdm
import networkx as nx
from utils.commit import (
    parse_commit_info,
    has_process_info,
    check_is_extend_commit,
    remove_prefix,
)
from utils.file import read_json_file, save_json_to_file
from utils.chat import num_tokens_from_string
from utils.batch import AsyncTaskQueue
from const.dir import COMMIT_OUTPUT_DIR
from chat.model.commit import handler_commit


class CommitTool:
    def __init__(self, config, args, app_info):
        if "bundle_name" not in config:
            repo = config["repo"]
            config["bundle_name"] = repo.split("/")[-1]

        self.app_info = app_info
        self.config = config
        self.args = args
        self.queue = AsyncTaskQueue(
            max_concurrent_tasks=int(
                config.get("max_handler_commit_file_task", 1)
            )
        )
        self.repo = git.Repo(config["repo"])
        if "branch" in config and config["branch"] != "":
            # 切换到指定分支

            self.repo.git.checkout(config["branch"])

    def task_done(self, response, commits, progress_bar):
        # config = response["config"]
        res = response["result"]
        result, error = res
        if not error and result is not None:
            commits += result
        elif error:
            # TODO 重新添加任务重试
            pass
        progress_bar.update(1)

    # token 超限拆分多个任务后。得到结果将结果合并
    # def merge_commit_results(self, results):
    #     merged_context = {
    #         "id": results[0]["id"],
    #         "message": results[0]["message"],
    #         "files": [],
    #     }
    #     for result in results:
    #         if "files" not in result:
    #             continue
    #         merged_context["files"].extend(result["files"])
    #     return merged_context

    # TAG 08-27 调整：超出 token 限制的 commit 不处理。函数保留做参考
    # 单个文件判断 commit 和 file 的相关性。如果超出 token 拆分为多个任务
    # async def handler_commit_files_for_llm(self, commit_info):
    #     context = {
    #         "id": commit_info["id"],
    #         "message": commit_info["message"],
    #         "files": commit_info["files"],
    #     }
    #     tasks = []
    #     # 添加 prompt 长度限制
    #     # MAX_TOKENS = 128 * 1000
    #     MAX_TOKENS = 100 * 1000
    #     # 基础数据 token
    #     base_tokens = num_tokens_from_string(context["id"] + context["message"])
    #     # 累加 token
    #     current_tokens = base_tokens
    #     current_files = []
    #     for file in context["files"]:
    #         file_tokens = num_tokens_from_string(json.dumps(file))
    #         if current_tokens + file_tokens <= MAX_TOKENS:
    #             # token 在范围内，累加文件
    #             current_tokens += file_tokens
    #             current_files.append(file)
    #         else:
    #             # token 超出，增加一个任务，重置状态从当前文件开始再次累加
    #             tasks.append({**context, "files": current_files})
    #             current_tokens = base_tokens + file_tokens
    #             current_files = [file]
    #     if len(tasks) == 0:
    #         # 整个任务都没有超出, 添加作为一个任务
    #         tasks.append(context)
    #     results = await asyncio.gather(
    #         *[get_file_commit_related(task) for task in tasks]
    #     )
    #     res = self.merge_commit_results(results)
    #     return handler_files(commit_info["files"], res)

    # 获取 commit tokens
    def get_commit_tokens(self, commit_info):
        context = {
            "id": commit_info["id"],
            "message": commit_info["message"],
            "files": commit_info["files"],
        }
        current_tokens = num_tokens_from_string(
            context["id"] + context["message"]
        )
        for file in context["files"]:
            file_tokens = num_tokens_from_string(json.dumps(file))
            current_tokens += file_tokens
        return current_tokens

    def handler_commit_for_code(self, commit_info):
        message = commit_info["message"]
        # 去除特定前缀
        commit_info["message"] = remove_prefix(message)

    # 根据 llm 结果，获取 commit
    def get_commits_for_llm_res(self, llm_commit_res, commit_info):
        result = []
        commit_files = commit_info["files"]
        for index, llm_item in enumerate(llm_commit_res):
            llm_files = llm_item["files"]
            if not llm_item["is_valid"]:
                # 无用的 commit 跳过
                continue
            files = []
            for file in llm_files:
                # 与 commit 无关的文件跳过
                if not file["related"]:
                    continue
                commit_file = next(
                    (x for x in commit_files if x["name"] == file["name"]),
                    None,
                )
                if commit_file:
                    files.append({**commit_file, **file})
            if len(files) == 0:
                continue
            id = commit_info["id"]
            res_item = {
                "id": (f"{id}_{index}" if len(llm_commit_res) > 1 else id),
                "author": commit_info["author"],
                "email": commit_info["email"],
                "date": commit_info["date"],
                "message": llm_item["message"],
                "source_message": commit_info["message"],
                "hash": commit_info["hash"],
                "type": commit_info["type"],
                "bundle_name": commit_info["bundle_name"],
                "scene": llm_item["scene"],
                "action": llm_item["action"],
                "reason": llm_item["reason"],
                "is_valid": llm_item["is_valid"],
                "files": files,
            }
            result.append(res_item)
        return result

    # 使用模型处理 commit
    # 拆分、去除无用 commit、判断文件 files 关联性
    async def handler_commit_for_llm(self, commit_info):
        chat_handler_commit = self.config.get("chat_handler_commit", "False")
        chat_cache = self.config.get("chat_cache", "False")

        # 未开启。直接返回原数据
        if chat_handler_commit == "False":
            return commit_info

        # TAG 如果 token 超出限制的 token 上限。舍弃不处理
        # 添加 prompt 长度限制
        # MAX_TOKENS = 128 * 1000
        MAX_TOKENS = 100 * 1000
        commit_tokens = self.get_commit_tokens(commit_info)
        if commit_tokens > MAX_TOKENS:
            return None

        llm_commit_res = await handler_commit(
            commit_info, use_cache=chat_cache == "True"
        )
        # 拆分多个 chat 任务
        # llm_commit_res = await handler_commit_chain(commit_info, use_cache=False)
        # 根据结果处理 commit 数据
        commit_list = self.get_commits_for_llm_res(
            llm_commit_res=llm_commit_res, commit_info=commit_info
        )
        return commit_list if type(commit_list) == list else []

        # 判断文件 files 关联性
        # merge_files = await self.handler_commit_files_for_llm(commit_info)
        # if len(merge_files) > 0:
        #     commit_info["files"] = merge_files

    # 单个 commit 处理
    async def get_item_commit_data(self, index, commit):
        result = None
        error = None
        try:
            commit_info = parse_commit_info(
                commit=commit,
                repo_path=self.config["repo"],
                branch_name=self.config["branch"],
                bundle_name=self.config["bundle_name"],
            )
            # TAG 没有包含 js 等文件、git 命令执行异常等
            if commit_info is None:
                return None, None
            max_commit_file_count = self.config.get("max_commit_file_count", 10)
            max_commit_file_count = int(max_commit_file_count)
            # TAG 如果一个 commit 包含的文件过多，数据意义较小，不进行处理
            # 如果包含文件为 0 ，也不进行处理
            if (
                len(commit_info["files"]) > max_commit_file_count
                or len(commit_info["files"]) == 0
            ):
                return None, None

            commit_info["id"] = f"commit_{index}"
            # 使用 code 处理 commit
            self.handler_commit_for_code(commit_info)
            # 使用模型处理 commit
            result = await self.handler_commit_for_llm(commit_info)
        except Exception as e:
            print(f"Task failed with exception: {e}")
            error = e
            # 打印完整的异常堆栈信息
            traceback.print_exc()
        return result, error

    # 获取所有提交
    async def get_all_commits(self):
        commits = []
        folder_path = self.config.get("folder_path", None)
        # 获取特定时间，特定路径下的 commit
        iter_commits = list(
            self.repo.iter_commits(
                paths=folder_path, since=self.config["start_date"]
            )
        )
        current_commits = []
        # 先筛选过滤
        for commit in iter_commits:
            # 只处理特定前缀的 commit
            has_process = has_process_info(commit)
            if not has_process:
                continue
            # TAG 排除特定限制条件的 commit
            is_extend = check_is_extend_commit(commit, self.config)
            if is_extend:
                continue
            current_commits.append(commit)
        progress_bar = tqdm(
            total=len(current_commits), desc="handler commit list", ncols=100
        )
        self.queue.on_task_done(
            lambda x: self.task_done(x, commits, progress_bar)
        )
        # 按提交时间排序
        # 处理过滤后的 commits（分两步处理可以获取到真实的进度）
        for index, commit in enumerate(current_commits):
            self.queue.add_task(
                self.get_item_commit_data(index, commit),
                {"commit": commit, "index": index},
            )
        await self.queue.start()
        await self.queue.join()
        progress_bar.set_description("handler commit done")
        progress_bar.close()
        return commits

    # 生成 commit 图
    async def generate_commit_graph(self):
        bundle_name = self.config["bundle_name"]
        branch_name = self.config["branch"].replace(
            "/", "_"
        )  # 防止 release/xxx 切分目录
        commits_data = read_json_file(
            COMMIT_OUTPUT_DIR / f"{bundle_name}_{branch_name}_commits.json"
        )
        G = nx.DiGraph()
        node_map = {}
        for commit in commits_data:
            id = f"commit_{len(node_map)}"
            G.add_node(id, **commit, is_leaf=False, community_id=-1)
            node_map[commit["hash"]] = id
        if len(node_map) > 0:
            graph_path = (
                COMMIT_OUTPUT_DIR
                / f"commit_graph_{bundle_name}_{branch_name}.json"
            )
            save_json_to_file(nx.node_link_data(G), graph_path)
        else:
            print("no commit data")

    # 生成 commit 数据
    async def generate_commit_data(self):
        # 获取所有提交
        commits = await self.get_all_commits()
        commits = sorted(
            commits,
            key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d %H:%M:%S"),
            reverse=True,
        )
        bundle_name = self.config["bundle_name"]
        branch_name = self.config["branch"].replace(
            "/", "_"
        )  # 防止 release/xxx 切分目录
        save_json_to_file(
            commits,
            COMMIT_OUTPUT_DIR / f"{bundle_name}_{branch_name}_commits.json",
        )

    async def run(self):
        action = self.args.action or "generate"
        action_map = {
            "generate": self.generate_commit_data,
            "graph": self.generate_commit_graph,
        }
        action_handler = action_map.get(action)
        if not action_handler:
            raise ValueError(f"action {action} not found.")
        await action_handler()
