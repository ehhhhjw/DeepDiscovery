import json
import asyncio
from services.global_search_chain import (
    llm_global_search_map,
    llm_global_search_reduce,
)
from utils import num_tokens_from_string


class GlobalSearch:
    def __init__(self, query, community_path, concurrent_num):
        print(f"用户提问: {query} \n\n")
        self.query = query
        self.token_num = 0
        self.max_tokens = 90 * 1000
        self.current_context = ""
        self.map_response_data = []
        self.semaphore = asyncio.Semaphore(concurrent_num)
        with open(community_path, "r") as f:
            self.community = json.load(f)

    async def get_context(self):
        await self.global_search_map()
        self.sort_map_response_data()
        final_prompt, context = await self.global_search_reduce()
        return final_prompt, context

    def add_new_context(self, new_context):
        current_token_num = num_tokens_from_string(new_context)
        if self.token_num + current_token_num >= self.max_tokens:
            return False
        self.current_context += new_context + "\n"
        self.token_num += current_token_num
        return True

    async def worker(self, semaphore, prompt_input, index):
        async with semaphore:
            print(f"Processing Batch {index} ......")
            result = await llm_global_search_map(prompt_input)
            self.map_response_data += result["points"]
            print(f"Batch {index} Done!")

    async def global_search_map(self):
        prompt_inputs = []
        self.current_context = ""
        last_add_id = -1
        last_id = -1
        for community_id in self.community:
            reports = {
                "community_id": community_id,
                "reports": self.community[community_id]["reports"],
            }
            reports = json.dumps(reports, ensure_ascii=False)
            flag = self.add_new_context(reports)
            if not flag:
                prompt_inputs.append(
                    {
                        "user_question": self.query,
                        "context_data": self.current_context,
                    }
                )
                self.current_context = reports
                self.token_num = 0
                last_add_id = last_id
            last_id = community_id
        if last_add_id != last_id:
            prompt_inputs.append(
                {
                    "user_question": self.query,
                    "context_data": self.current_context,
                }
            )
        print(f"There are {len(prompt_inputs)} batches to be process.")
        tasks = [
            asyncio.create_task(self.worker(self.semaphore, prompt, index))
            for index, prompt in enumerate(prompt_inputs)
        ]
        await asyncio.gather(*tasks)

    def sort_map_response_data(self):
        self.map_response_data = sorted(
            self.map_response_data, key=lambda x: x["score"], reverse=True
        )

    async def global_search_reduce(self):
        self.current_context = ""
        for report in self.map_response_data:
            flag = self.add_new_context(json.dumps(report, ensure_ascii=False))
            if not flag:
                break
        prompt_input = {}
        prompt_input["user_question"] = self.query
        prompt_input["context_data"] = self.current_context
        context = await llm_global_search_reduce(prompt_input)
        return prompt_input, context
