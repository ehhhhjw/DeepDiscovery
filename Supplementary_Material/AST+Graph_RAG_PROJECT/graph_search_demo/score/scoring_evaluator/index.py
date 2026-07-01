import re
import traceback
from langchain.evaluation import load_evaluator
from score.const import SCORE_DIR, chat_model
from utils.batch import AsyncTaskQueue
from utils.file import save_json_to_file, read_json_file
from utils.excel import check_excel_field_invalid
from utils import get_dict_value, statistics_mean
from typing import Dict, List, Optional
from prompt.score import KWARGS, ACCURACY_CRITERIA
from constants import ScoreType

class ScoringEvaluator:
    def __init__(
        self,
        mark: str,
        config: Dict[str, any],
        excel_list: List[Dict[str, any]],
        max_concurrent_tasks: Optional[int] = 2,
        args:Dict = None,
        score_type:ScoreType = ScoreType.CODE,
    ):
        self.score_type = score_type
        self.args = args
        self.mark = mark
        chat_json_path = SCORE_DIR / f"log/{self.get_mark_dir()}/chat.json"
        chat_data = read_json_file(chat_json_path)

        self.chat_data = chat_data
        self.config = config
        self.queue = AsyncTaskQueue(
            max_concurrent_tasks=int(max_concurrent_tasks)
        )
        self.excel_list = excel_list
        self.evaluator = load_evaluator(
            "labeled_score_string",
            criteria=ACCURACY_CRITERIA,
            llm=chat_model,
            # normalize_by=10,
        )

    def get_mark_dir(self):
        if self.score_type == ScoreType.DOCS:
            return f"{self.mark}/doc"
        else:
            return f"{self.mark}/code"

    # 提取关键词为细粒度的一个一个元素
    def extract_keywords(self, text):
        # 用于存储拆分和去重后的数据
        unique_elements = set()

        lines = text.strip().split("\n")
        # 对每一行进行处理
        for line in lines:
            # 按照逗号分割并去除空格
            elements = [elem.strip() for elem in line.split(",")]

            # 对每个元素进行分割并添加到集合中去重
            for element in elements:
                parts = element.split(".")
                len_parts = len(parts)
                if len_parts == 1 or len_parts == 2:
                    unique_elements.add(parts[0])
                elif len_parts == 3:
                    unique_elements.add(parts[0])  # 文件名部分
                    unique_elements.add(parts[2])  # 方法名部分

        # 将集合转换为列表
        keywords = list(unique_elements)

        return keywords

    # 查询是否有关键元素
    def match_elements_in_document(self, document, elements):
        results = []

        for element in elements:
            # Create a regex pattern with negative lookahead and lookbehind
            pattern = r"(?<![\w$])" + re.escape(element) + r"(?![\w$])"
            matches = re.findall(pattern, document)
            results.append((element, len(matches) > 0))

        ratio = self.calculate_true_ratio(results)
        return results, ratio

    # 获取关键词为 true 的比例
    def calculate_true_ratio(self, matches):
        # 检查输入是否为空列表
        if not matches:
            return 0

        # 计算True的数量
        true_count = sum(1 for _, is_matched in matches if is_matched)
        # 计算总数量
        total_count = len(matches)
        # 计算True的比例
        true_ratio = true_count / total_count

        return true_ratio

    # 多次调用 LLM，求均值
    async def get_llm_score_average(
        self, prediction, reference, input, iterations=2
    ):
        try:
            results = []
            for _ in range(iterations):
                res_item = await self.evaluator.aevaluate_strings(
                    prediction=prediction,  # 生成的答案
                    reference=reference,  # 参考答案
                    input=input,  # 原始问题
                    # kwargs 附加参数
                    **KWARGS,
                )
                results.append(res_item)

            scores = [int(x["score"]) for x in results if x["score"]]
            # 计算均值
            llm_score = statistics_mean(scores)
            return llm_score, results
        except Exception as e:
            print("get_llm_score_average error:", e)
            return None, None

    # 是否使用缓存数据
    def get_cache_score_data(self, log_path):
        use_cache = self.config["score"].get("use_cache", "False")
        if use_cache == "False":
            # 是否使用缓存数据配置
            return None
        cache_data = read_json_file(log_path)
        score_info = cache_data.get("score_info", None)
        if score_info is not None:
            return score_info
        return None

    # 解析 primary 答案
    def process_primary(self, primary_str):
        # 按照换行符分割输入文本，得到每一行
        lines = primary_str.strip().split("\n")

        # 定义一个结果列表
        result = []

        for line in lines:
            # 按照逗号分割每一行
            sub_items = line.split(",")
            # 去掉每个子项的前后空格
            sub_items = [item.strip() for item in sub_items]

            result.append(sub_items)
        return result

    def get_position_score(self, positions, max_position):
        """
        获取位置评分
        :param positions: 位置列表
        :param max_position: 最大位置
        """
        # 所有位置的总和最大值. 从 0 开始
        position_all = len(positions) * max_position
        # 实体位置的和
        position_sum = sum(positions)
        # 计算最终的位置百分比
        position_ratio = position_sum / position_all if position_all else 0
        # 将的到的百分比分数 * 10，然后用 10 减去。归整为 10 分制，分数越高越好
        position_score = 10 - (position_ratio * 10)
        # 去除掉没有找到的实体的索引
        exist_position = [x for x in positions if x <= max_position]
        result = {
            "score": position_score if position_score > 0 else 0,
            "entity_len": max_position + 1,
            # 此处需要去掉没有找到实体的 position，否则 max 没有意义
            "max_position": max(exist_position) if exist_position else None,
            "min_position": min(exist_position) if exist_position else None,
            "positions": positions,
        }
        return result

    # 根据召回实体列表获取分数
    def get_score_item(self, id, primary_str, entity_list):
        # 获取类型
        type = "rag"
        if isinstance(entity_list[0], str):
            # rerank 召回，只有文本
            type = "rerank"
        elif isinstance(entity_list[0], dict):
            # rag 召回，{ score, name, id, type }
            type = "rag"
        else:
            return None
        # 标准答案关键元素列表
        primary_file_list = self.process_primary(primary_str)
        # 召回实体的最差位置
        entity_len = len(entity_list) - 1

        scores = []
        positions = []
        not_find_list = []
        for primary_files in primary_file_list:
            _scores, _positions, _not_find_list = self.get_primary_item_score(
                primary_files=primary_files, entity_list=entity_list, type=type
            )
            scores += _scores
            positions += _positions
            if _not_find_list:
                not_find_list.append(
                    {
                        "id": id,
                        "not_find_list": _not_find_list,
                    }
                )
        position_score_dict = self.get_position_score(positions, entity_len)

        find_score = statistics_mean(scores)
        position_score = position_score_dict["score"]
        score = statistics_mean([find_score, position_score])
        return {
            "score": score,
            "find_score": find_score,
            "position_score": position_score_dict["score"],
            "find_scores": scores,
            "not_find_list": not_find_list,
            "position": position_score_dict,
        }

    def nofind_condition(self, score, type):
        return score == 0 and type != "rerank"

    def primary_contains_name(self, primary_file, name):
        return primary_file.startswith(name)

    def get_primary_item_score(self, primary_files, entity_list, type):
        # 实体最差位置
        entity_len = len(entity_list) - 1
        scores = []
        positions = []
        not_find_list = []
        # 查询得分，完全匹配任意一个得 5 分，部分匹配任意一个得 3 分。
        # 即使多次部分匹配，也为 3 分
        find_score = 0
        # 查找到的数量，完全匹配 +1，部分匹配 + 0.5
        find_num = 0
        for primary_file in primary_files:
            score = 0
            index = entity_len + 1  # 默认位置为实体的总列表位置 + 1
            for i, entity_item in enumerate(entity_list):
                name = entity_item if type == "rerank" else entity_item["name"]
                # 其他情况（rag）完全匹配
                # rerank 的情况下。完全匹配或者 name 召回到了文件名层级
                if name == primary_file or (
                    type == "rerank" and primary_file.startswith(name)
                ):
                    # 如果完全匹配
                    score = 5
                    find_num += 1
                    index = i
                    break
            if self.nofind_condition(score, type):
                # 如果没有完全匹配的元素，尝试部分匹配
                for i, entity_item in enumerate(entity_list):
                    name = (
                        entity_item if type == "rerank" else entity_item["name"]
                    )
                    # 关键元素 a.js.get，name a.js 这样的可以算部分匹配到
                    # 但是反之，不能算对
                    if self.primary_contains_name(primary_file, name):
                        # 如果是部分匹配. 算找到一部分，加一部分分
                        score = 3
                        find_num += 0.5
                        index = i
                        break
            find_score = max(find_score, score)
            positions.append(index)
            if score == 0:
                not_find_list.append({"name": primary_file, "score": score})
        ratio_score = (
            find_num if find_num == 0 else find_num / len(primary_files) * 5
        )
        final_score = score + ratio_score
        scores.append(final_score)
        return scores, positions, not_find_list

    # 计算 rag 得分。原问题、子问题、rerank input
    async def get_rag_score(self, chat_data_item: Dict[str, any]):
        # 参考答案
        reference = get_dict_value(
            chat_data_item, "standard_info.primary_files"
        )
        if not reference:
            return None
        result = {
            "final_recall": None,
        }
        # final_recall 评分
        final_recall = get_dict_value(chat_data_item, "chat_info.final_recall")
        id = get_dict_value(chat_data_item, "id")
        if final_recall:
            final_recall_res = self.get_score_item(id, reference, final_recall)
            result["final_recall"] = final_recall_res

        return result

    # 计算 rerank 得分
    async def get_rerank_score(self, chat_data_item: Dict[str, any]):
        # 参考答案
        reference = get_dict_value(
            chat_data_item, "standard_info.primary_files"
        )
        if not reference:
            return None

        # 生成的答案, 实体列表
        prediction = get_dict_value(chat_data_item, "chat_info.rerank_output")
        if not prediction or not isinstance(prediction, list):
            return None

        id = get_dict_value(chat_data_item, "id")
        rerank_score_res = self.get_score_item(id, reference, prediction)
        return {"rerank": rerank_score_res}

    # 计算 chat 得分
    async def get_chat_score(self, chat_data_item: Dict[str, any]):
        # 优先使用改写后的问题
        input = (
            get_dict_value(chat_data_item, "question")
            or get_dict_value(chat_data_item, "query_info.question")
            or get_dict_value(chat_data_item, "query_info.user_question")
        )
        # 参考答案. excel 或 chat 生成
        reference = get_dict_value(
            chat_data_item, "standard"
        ) or get_dict_value(chat_data_item, "standard_info.standard")

        # 关键元素
        keywords_str = get_dict_value(
            chat_data_item, "primary_files"
        ) or get_dict_value(chat_data_item, "standard_info.primary_files")
        keywords = self.extract_keywords(keywords_str)

        # 生成的答案
        prediction = get_dict_value(chat_data_item, "answer") or get_dict_value(
            chat_data_item, "chat_info.chat"
        )

        if not reference or not prediction:
            return None

        kw_match, ratio = self.match_elements_in_document(prediction, keywords)
        # 关键词基础分数
        keyword_base_score = int(self.config["score"]["keyword_base_score"])
        keyword_score = ratio * keyword_base_score
        # 将 kw 分数标准化到 10 分制。确保两者的可比性
        standardized_kw_score = round((keyword_score / keyword_base_score) * 10)
        # 获取 llm 多次调用均值
        llm_score, llm_score_res = await self.get_llm_score_average(
            prediction=prediction,  # 生成的答案
            reference=reference,  # 参考答案
            input=input,  # 原始问题
        )
        if llm_score is None or llm_score_res is None:
            return None
        # 加权值
        score_ratio = 10 / keyword_base_score
        # 加权平均值
        weighted_average = (
            (llm_score * score_ratio) + standardized_kw_score
        ) / (1 + score_ratio)
        weighted_average = round(weighted_average)
        # 如果有关键词，则使用加权平均值，否则使用 LLM 得分
        final_score = weighted_average if len(keywords) > 0 else llm_score
        result = {
            "chat": {
                "score": {
                    "weighted_avg": weighted_average,
                    "llm": llm_score,
                    "keyword": standardized_kw_score,
                    "final": final_score,
                },
                "keywords": {
                    "keywords": keywords,  # 标准答案中的关键词（js 变量或调用链）
                    "list": kw_match,
                    "ratio": ratio,
                },
                "reasoning": llm_score_res,
            }
        }
        return result

    # 获取 chat、rag、rerank 得分
    async def get_all_score(self, chat_data_item: Dict[str, any]):
        rag_score_res = await self.get_rag_score(chat_data_item) or {}
        rerank_score_res = await self.get_rerank_score(chat_data_item) or {}
        chat_score_res = await self.get_chat_score(chat_data_item) or {}
        result = {**rag_score_res, **rerank_score_res, **chat_score_res}
        return result

    # 计算 excel 某一行的得分
    async def get_excel_item_score(self, chat_data_item: Dict[str, any]):
        # excel 数据校验
        for key in chat_data_item:
            if check_excel_field_invalid(chat_data_item[key]):
                return None
        result = await self.get_chat_score(chat_data_item)
        if not result:
            return None
        chat_score_data = result.get("chat", None)
        return {"excel": chat_score_data} if chat_score_data else None

    # 数据可用性校验
    def check_data_availability(self, chat_data_item: Dict):
        # 如果没有 query
        if check_excel_field_invalid(
            get_dict_value(chat_data_item, "query_info.user_question")
        ):
            print("user_question is None")
            return False

        # 如果没有标准答案
        if check_excel_field_invalid(
            get_dict_value(chat_data_item, "standard_info.standard")
        ):
            print("standard is None")
            return False

        # 如果没有关键元素答案
        if check_excel_field_invalid(
            get_dict_value(chat_data_item, "standard_info.primary_files"),
        ):
            print("primary_files is None")
            return False

        return True

    # 单个评分任务
    async def evaluate_item(
        self, chat_data_item: Dict[str, any], type: str = None
    ):
        """
        评估问答分数
        :param chat_data_item: 数据
        :param type: all、chat、rag、rerank、excel。all 为不包含 excel 的全部
        :return: 分数
        """
        result = None
        error = None
        try:
            # 优先使用传入的 type 配置
            type = self.config["score"]["score_type"] if type is None else type
            id = chat_data_item.get("id", None)
            id = f"Id: {id}" if id else ""
            input = get_dict_value(
                chat_data_item, "query_info.question"
            ) or get_dict_value(chat_data_item, "query_info.user_question")
            print(f"⏱️ 单个 score 任务开始. Q: {input}, Id: {id}, type: {type}")

            score_handler_map = {
                "all": self.get_all_score,
                "chat": self.get_chat_score,
                "rag": self.get_rag_score,
                "rerank": self.get_rerank_score,
                "excel": self.get_excel_item_score,
            }
            if type not in score_handler_map:
                return None, None
            handler = score_handler_map.get(type)
            result = await handler(chat_data_item)
        except Exception as e:
            print(f"evaluate_item_error: {e}")
            error = f"「{type}」{str(e)}"
            traceback.print_exc()
        return result, error

    # 批量添加任务
    def batch_score_task(self):
        print("开始添加评分任务 queue")
        if self.chat_data is None:
            return print("chat_data is None")
        for key in self.chat_data:
            chat_data_item = self.chat_data[key]
            # 数据可用性校验
            available = self.check_data_availability(chat_data_item)
            if not available:
                continue
            score_task_config = {
                "mark": self.mark,
                "chat_data_item": chat_data_item,
                "config": self.config,
                "error_num": 0,
            }
            self.queue.add_task(
                self.evaluate_item(chat_data_item),
                score_task_config,
            )

    # rerank input
    def generate_final_recall_report(self):
        final_recall_scores = []
        final_recall_position_scores = []
        final_recall_position = []  # 未打平的 position
        final_recall_position_list = []  # 打平后的 position
        not_find_list = []

        for id in self.chat_data:
            chat_data_item = self.chat_data[id]
            if "score_info" not in chat_data_item:
                continue
            score_info = chat_data_item["score_info"]
            final_recall = get_dict_value(
                chat_data_item, "chat_info.final_recall"
            )
            # 召回实体的最差位置
            entity_last_position = len(final_recall) - 1

            # 添加 final rag 得分
            final_recall = score_info.get("final_recall")
            if final_recall:
                final_recall_scores.append(final_recall["find_score"])
                final_recall_position_scores.append(
                    final_recall["position_score"]
                )
                final_recall_position_list.append(
                    final_recall["position"]["positions"]
                )
                final_recall_position += final_recall["position"]["positions"]

                _not_find_list = final_recall["not_find_list"]
                if _not_find_list:
                    not_find_list.append(_not_find_list)

        # 过滤掉未找到的实体
        exist_positions = [
            x for x in final_recall_position if x <= entity_last_position
        ]
        find_score = statistics_mean(final_recall_scores)
        position_score = statistics_mean(final_recall_position_scores)
        final_recall_score = statistics_mean([find_score, position_score])
        result = {
            "score": final_recall_score,
            "find_score": find_score,
            "position_score": position_score,
            "position_info": {
                "position": statistics_mean(final_recall_position),
                "max_position": (
                    max(exist_positions) if exist_positions else None
                ),
                "min_position": (
                    min(exist_positions) if exist_positions else None
                ),
                "find_ratio": len(exist_positions) / len(final_recall_position),
                "not_find_list": not_find_list,
                "sorted_positions": sorted(final_recall_position),
                "positions": final_recall_position_list,
            },
        }
        return result

    # rerank output
    def generate_rerank_report(self):
        rerank_scores = []
        rerank_position_scores = []
        rerank_position = []
        exist_positions = []
        not_find_list = []

        for id in self.chat_data:
            chat_data_item = self.chat_data[id]
            if "score_info" not in chat_data_item:
                continue
            score_info = chat_data_item["score_info"]
            rerank_output = get_dict_value(
                chat_data_item, "chat_info.rerank_output"
            )
            # 召回实体的最差位置
            entity_last_position = len(rerank_output) - 1

            # 添加 rerank 得分
            rerank_item = score_info.get("rerank")
            if rerank_item:
                rerank_scores.append(rerank_item["find_score"])
                rerank_position_scores.append(rerank_item["position_score"])
                _positions = get_dict_value(rerank_item, "position.positions")
                rerank_position += _positions
                _not_find_list = rerank_item["not_find_list"]
                if _not_find_list:
                    not_find_list.append(_not_find_list)
                # 过滤掉未找到的实体
                exist_positions += [
                    x for x in _positions if x <= entity_last_position
                ]
        if not rerank_scores:
            return None

        find_score = statistics_mean(rerank_scores)
        position_score = statistics_mean(rerank_position_scores)
        final_rerank_score = statistics_mean([find_score, position_score])
        return {
            "score": final_rerank_score,
            "find_score": find_score,
            "position_score": position_score,
            "position_info": {
                "position": statistics_mean(rerank_position, None),
                "max_position": (
                    max(exist_positions) if exist_positions else None
                ),
                "min_position": (
                    min(exist_positions) if exist_positions else None
                ),
                "find_ratio": len(exist_positions) / len(rerank_position),
                "not_find_list": not_find_list,
                "sorted_positions": sorted(rerank_position),
                "positions": [rerank_position],
            },
        }

    # 获取性能相关报告
    def generate_performance_report(self):
        elapsed_times = []
        for id in self.chat_data:
            chat_data_item = self.chat_data[id]
            if (
                "score_info" not in chat_data_item
                or "execute_info" not in chat_data_item
            ):
                continue
            execute_info = chat_data_item["execute_info"]
            if isinstance(execute_info["elapsed_time"], float):
                elapsed_times.append(execute_info["elapsed_time"])
        return {
            "elapsed_time": statistics_mean(elapsed_times),
            "elapsed_times": elapsed_times,
        }

    # chat
    def generate_chat_report(self):
        chat_scores = []
        for id in self.chat_data:
            chat_data_item = self.chat_data[id]
            if "score_info" not in chat_data_item:
                continue
            chat_item = get_dict_value(chat_data_item, "score_info.chat")
            # 添加 chat 得分
            if chat_item:
                chat_scores.append(chat_item["score"]["final"])
        return {
            "score": statistics_mean(chat_scores),
            "scores": chat_scores,
        }

    # 生成报告
    def generate_report(self):
        result = [
            {
                "id": item["id"],
                "index": item["index"],
                "score_info": item["score_info"],
                "execute_info": item["execute_info"],
            }
            for item in self.chat_data.values()
            if "score_info" in item
        ]

        final_recall_report = self.generate_final_recall_report()
        rerank_report = self.generate_rerank_report()
        chat_report = self.generate_chat_report()
        performance_report = self.generate_performance_report()
        all_report = {
            "final_recall": final_recall_report,
            "rerank": rerank_report,
            "chat": chat_report,
            "performance": performance_report,
        }
        return {"report": all_report, "list": result}

    def task_done(self, response: Dict):
        if self.chat_data is None:
            return print("chat_data is None")
        config = response["config"]
        res = response["result"]
        result, error = res
        chat_data_item = config["chat_data_item"]
        id = get_dict_value(config, "chat_data_item.id")
        index = get_dict_value(config, "chat_data_item.index")
        # 重试
        if error and config["error_num"] < 3:
            config["error_num"] += 1
            print(f"❌ 任务执行失败. Id: {id}, index: {index}")
            print(f"⏱️ 开始重试. Id: {id}, index: {index}")
            self.queue.add_task(
                self.evaluate_item(chat_data_item),
                config,
            )
            return
        print(f"✅ 单个任务完成. Id: {id}, index: {index}")
        chat_data_item = config["chat_data_item"]
        chat_data_item["score_info"] = result
        save_json_to_file(
            chat_data_item, SCORE_DIR / f"log/{self.get_mark_dir()}/chat/{index}.json"
        )

    def all_task_done(self, config: Dict):
        try:
            print("-------- all score task done --------")
            # 更新分数
            save_json_to_file(
                self.chat_data, SCORE_DIR / f"log/{self.get_mark_dir()}/chat.json"
            )
            report_data = self.generate_report()
            # 生成简略报告
            save_json_to_file(
                report_data, SCORE_DIR / f"log/{self.get_mark_dir()}/report.json"
            )
        except Exception as e:
            print(f"all_task_done_error: {e}")
            traceback.print_exc()

    async def run(self):
        self.queue.on_task_done(lambda x: self.task_done(x))
        self.queue.on_all_tasks_done(lambda x: self.all_task_done(x))
        self.batch_score_task()

        await self.queue.start()
        await self.queue.join()

    # 对 excel 中的某一行执行评分，测试用
    def execute_excel_row(
        self, row_index: int = 0, answer_type: str = "answer"
    ):
        """
        对 excel 数据评估问答分数
        :param row_index: excel 行索引
        :param answer_type: 回答类型，answer、aone_copilot、tongyi
        """
        row_item = self.excel_list[row_index]
        input = row_item["question"]
        prediction = row_item[answer_type]
        reference = row_item["standard"]
        if not input or not prediction or not reference:
            return print("input or prediction or reference is None")
        chat_data_item = {
            "question": input,
            "answer": prediction,
            "standard": reference,
        }
        return self.evaluate_item(chat_data_item, "excel")
