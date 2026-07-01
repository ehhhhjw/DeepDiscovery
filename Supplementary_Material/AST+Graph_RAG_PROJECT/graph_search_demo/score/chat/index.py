import time
import asyncio
import subprocess
from datetime import datetime
from const import ROOT_DIR, SCORE_DIR, SOURCE_LOG_DIR, SRC_CHAT_LOG_DIR
from utils.batch import AsyncTaskQueue
from utils.file import save_json_to_file, read_json_file, read_file
from utils import get_dict_value, generate_random_string
from typing import List, Dict


class Chat:
    def __init__(
        self,
        config: Dict[str, any],
        excel_list: List[Dict[str, any]],
        mark: str,
        args: Dict
    ):
        self.args = args
        formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        default_mark = f"{formatted_datetime}_{generate_random_string(10)}"
        _mark = config.get("mark", default_mark)
        self.mark = mark or _mark

        use_excel_answer = config.get("use_excel_answer", "False")
        self.use_excel_answer = use_excel_answer == "True"

        self.config = config
        self.excel_list = excel_list

        max_concurrent_tasks = config.get("max_concurrent_tasks", 1)
        max_concurrent_tasks = int(max_concurrent_tasks)
        self.queue = AsyncTaskQueue(max_concurrent_tasks=max_concurrent_tasks)

        self.data = {}
        print("mark: ", self.mark)

    # 解析 sh 脚本，拼接参数
    def format_sh_context(self, sub_querys=[]):
        # 读取对应的 shell 脚本
        shell_context = read_file(self.args.chat_script_path)
        shell_context = shell_context.replace("\\", "").replace('"', "")
        shell_command = shell_context.split()

        # chat 问答子问题拆分
        sub_querys_str = ",".join(sub_querys) if len(sub_querys) else ""
        if (
            self.config.get("use_excel_sub_querys", "False") == "True"
            and sub_querys_str
        ):
            shell_command += ["--sub_querys", sub_querys_str]

        # chat 问答执行阶段控制
        stage = self.config.get("stage", "")
        if stage:
            shell_command += ["--stage", stage]

        # chat 问答结构化输出字段筛选
        # default_chat_fields = "recall,sub_query,bm25_recall,bm25_sub_query,final_recall,rerank_output,chat"
        default_chat_fields = "final_recall,rerank_output,chat"
        search_res_fields = self.config.get(
            "search_res_fields", default_chat_fields
        )
        shell_command += ["--search_res_fields", search_res_fields]

        # 去除两边空白字符
        shell_command = [x.strip() for x in shell_command]
        return shell_command

    # 执行 sh 脚本，chat 对话
    async def chat_task(
        self,
        id: str,
        index: int,
        excel_item: Dict,
    ):
        start_time = time.time()
        question = excel_item["question"]
        excel_answer_type = self.config.get("excel_answer_type", "answer")
        sub_querys_str = excel_item.get("sub_querys", "")
        sub_querys = []
        if sub_querys_str:
            sub_querys = [
                q.strip() for q in sub_querys_str.split("\n") if q.strip()
            ]
        print(f"⏱️ 单个任务开始: Q: {question}, Id: {id}")

        # 如果使用 excel 中的答案
        if self.use_excel_answer:
            return excel_item[excel_answer_type], None, 0
        # 如果 mark 标识的问答已经存在，直接使用
        # TAG 任务如果中途执行失败，可以配置对应的 mark 直接使用已经成功的结果
        def check_cache_valid(mark_dir):
            item_cache_data_path = SOURCE_LOG_DIR / f"{mark_dir}/chat/{index}.json"
            result = {'valid': False}
            if item_cache_data_path.is_file():
                item_cache_data = read_json_file(item_cache_data_path)
                if item_cache_data is not None and "chat_info" in item_cache_data:
                    result['data'] = [item_cache_data["chat_info"], None, 0]
            return result

        if self.args.exe_type == "code_doc":
            result = check_cache_valid(f'{self.mark}/code')
            if result['valid']:
                result = check_cache_valid(f'{self.mark}/doc')
                if result['valid']:
                    return result['data']
        elif self.args.exe_type == "doc":
            result = check_cache_valid(f'{self.mark}/doc')
            if result['valid']:
                return result['data']
        else:
            result = check_cache_valid(f'{self.mark}/code')
            if result['valid']:
                return result['data']

                    

        shell_command = self.format_sh_context(sub_querys=sub_querys)
        # print("shell_command: ", shell_command)
        process = await asyncio.create_subprocess_exec(
            *shell_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT_DIR,
        )
        try:
            output, error = await process.communicate(
                input=excel_item["question"].encode("utf-8")
            )
            output = output.decode("utf-8")
            error = error.decode("utf-8") if error else None
        # except asyncio.TimeoutError:
        #     process.kill()
        #     output, error = await process.communicate()
        #     output = output.decode("utf-8")
        #     error = error.decode("utf-8") if error else None
        except Exception as e:
            process.kill()
            output = None
            error = str(e)

        end_time = time.time()
        elapsed_time = end_time - start_time

        return output, error, elapsed_time

    # 批量执行 chat 任务
    def batch_task_queue(self):
        """
        批量执行 chat 任务
        """
        print("开始添加任务 queue")
        for index, excel_item in enumerate(self.excel_list):
            id = f"{index}_{self.args.exe_type}"
            chat_task_config = {
                "id": id,
                "index": index,
                "mark": self.mark,
                "question": excel_item["question"],
                "excel_item": excel_item,
                "error_num": 0,  # 失败次数
            }
            self.queue.add_task(
                self.chat_task(
                    id=id,
                    index=index,
                    excel_item=excel_item,
                ),
                chat_task_config,
            )

    # 格式化 chat 答案
    def format_chat_answer(self, data: str):
        if self.use_excel_answer:
            return data or ""
        if "RAG Done!" not in data:
            return data
        _data = data.split("RAG Done!\n")[1]
        return _data

    # 从日志数据中获取 chat 结果
    def get_chat_data_from_log(self, data, r_file):
        result = {"chat": data or None}
        if isinstance(data, dict):
            # 从缓存中获取的数据
            return data
        elif not isinstance(data, str):
            # 一般不会出现这种情况。为异常数据
            return {"chat": None}
        if self.use_excel_answer:
            # 如果直接使用 excel 中的答案
            return result
        # 解析 chat 结果，获取 chat 执行 标识
        date_str = next(
            x for x in data.split("\n") if x.startswith("> start_time: ")
        )
        if not date_str:
            # 如果没有标识的话，无法读取结构化日志。尝试解析原始数据
            result["chat"] = self.format_chat_answer(data, False)
            return result
        mark_datetime = date_str.replace("> start_time: ", "")
        # 读取结构化日志数据
        chat_data = read_json_file(
            SRC_CHAT_LOG_DIR / f"{mark_datetime}/{r_file}"
            if self.args.exe_type == "doc"
            else SRC_CHAT_LOG_DIR / f"{mark_datetime}/{r_file}"
        )
        if chat_data is None:
            result["chat"] = self.format_chat_answer(data)
        return chat_data or result

    def parse_and_save_chat_index(self, result, w_dir, r_file, config, index, question, elapsed_time, error,id):
        dir_data = self.data.setdefault(w_dir, {})
        mark_dir = f'{self.mark}/{w_dir}'
        chat_result = self.get_chat_data_from_log(result, r_file)
        excel_item = config.get("excel_item", None)
        # query 信息
        query_info = chat_result.pop("query_info", {"user_question": question})
        # 执行过程信息
        execute_info = {
            "use_excel_answer": self.use_excel_answer,
            "type": self.config["excel_answer_type"],
            "elapsed_time": elapsed_time,
            "error_num": config["error_num"],
            "error": error,
        }
        # 标准答案信息
        standard_info = (
            {
                "standard": excel_item["standard"],
                "primary_files": excel_item["primary_files"],
            }
            if excel_item
            else {}
        )
        # 汇总记录数据
        data_item = {
            "id": id,
            "index": index,
            "query_info": query_info,
            "standard_info": standard_info,
            "execute_info": execute_info,
            "chat_info": chat_result,
        }
        # 单个任务的结果也保留，方便后续做缓存
        save_json_to_file(
            data_item, SCORE_DIR / f"log/{mark_dir}/chat/{index}.json"
        )
        # 去除一些信息，方便预览
        simple_data_item = {**data_item, "chat_info": chat_result}
        dir_data[id] = simple_data_item

    # 单个任务执行完成后的回调
    def task_done(self, response: Dict[str, any]):
        config = response["config"]
        res = response["result"]
        result, error, elapsed_time = res
        question = config["question"]
        index = config["index"]
        id = config["id"]
        error_num = config["error_num"]
        if error and error_num < 3:
            config["error_num"] += 1
            print(
                f"❌ 任务执行失败. {error}. Q: {question}, Id: {id}, index: {index}"
            )
            print(
                f"⏱️ 重试(error_num: {error_num}). Q: {question}, Id: {id}, index: {index}"
            )
            # 添加到任务队列。会添加到队尾
            self.queue.add_task(
                self.chat_task(
                    id=id, index=index, excel_item=config["excel_item"]
                ),
                config,
            )
            return
        print(
            f"✅ 单个任务执行完成. Q: {question}, Id: {id}, index: {index}, time: {elapsed_time}"
        )

        print(f"self.args.exe_type: {self.args.exe_type}")
        if self.args.exe_type == "code_doc":
            self.parse_and_save_chat_index(result, 'code', 'output.json', config, index, question, elapsed_time, error,id)
            self.parse_and_save_chat_index(result, 'doc', 'docs_output.json', config, index, question, elapsed_time, error,id)
        elif self.args.exe_type == "doc":
            self.parse_and_save_chat_index(result, 'doc','docs_output.json', config, index, question, elapsed_time, error,id)
        else:
            self.parse_and_save_chat_index(result, 'code', 'output.json', config, index, question, elapsed_time, error,id)

    # 任务队列清空后的回调
    def all_task_done(self, task_list):
        print("-------- all chat task done --------")
        if len(self.data.keys()) == 0:
            print("chat task data is empty")
        else:
            def save_chat_file(data, mark_dir):
                # 错误重试后的任务会添加到队尾，需要重新排序
                sorted_data = dict(
                    sorted(data.items(), key=lambda x: x[1]["index"])
                )
                save_json_to_file(
                    sorted_data, SCORE_DIR / f"log/{mark_dir}/chat.json"
                )

            if self.args.exe_type == "code_doc":
                save_chat_file(self.data["code"], f'{self.mark}/code')
                save_chat_file(self.data["doc"], f'{self.mark}/doc')
            elif self.args.exe_type == "doc":
                save_chat_file(self.data["doc"], f'{self.mark}/doc')
            else:
                save_chat_file(self.data["code"], f'{self.mark}/code')

    async def run(self):
        self.queue.on_task_done(lambda x: self.task_done(x))
        self.queue.on_all_tasks_done(lambda x: self.all_task_done(x))
        self.batch_task_queue()
        # 启动任务队列
        await self.queue.start()
        # 等待所有任务完成
        await self.queue.join()
