import asyncio
import traceback
from typing import Callable, Coroutine


# 异步任务队列
class AsyncTaskQueue:
    def __init__(self, max_concurrent_tasks: int = 1):
        self.queue = asyncio.Queue()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks_added = 0
        self.tasks_completed = 0
        self.task_done_event = asyncio.Event()
        self.all_tasks_done_event = asyncio.Event()
        self.all_done_list = []
        self.workers = None
        self.task_done_callbacks = []
        self.all_tasks_done_callbacks = []

    def add_task(self, task_coroutine: Coroutine, config: dict):
        self.tasks_added += 1
        self.queue.put_nowait((task_coroutine, config))
        # 清除所有任务完成事件，因为还有新任务添加
        if self.tasks_completed == self.tasks_added:
            self.tasks_completed = 0  # 重置已完成任务计数器

    async def worker(self):
        while True:
            task_coroutine, config = await self.queue.get()
            result = await self._execute_task(task_coroutine)
            self.queue.task_done()
            self._task_done(config, result)

    async def _execute_task(self, task_coroutine):
        try:
            # 确保进入事件循环至少一次，以防止同步任务阻塞
            await asyncio.sleep(0)
            result = await task_coroutine
            return result
        except Exception as e:
            print(f"Task failed with exception: {e}")
            # 打印完整的异常堆栈信息
            traceback.print_exc()
            return e  # 记录异常

    def _task_done(self, config, result):
        self.tasks_completed += 1

        task_done_data = {"config": config, "result": result}
        self.all_done_list.append(task_done_data)

        # 调用所有单个任务完成的回调函数
        for callback in self.task_done_callbacks:
            callback(task_done_data)
        # 检查是否所有任务都已完成
        if self.tasks_completed == self.tasks_added:
            for callback in self.all_tasks_done_callbacks:
                callback(self.all_done_list)
            self.all_done_list = []  # 清空所有任务完成列表

    async def start(self):
        if not self.workers:
            self.workers = [
                asyncio.create_task(self.worker())
                for _ in range(self.max_concurrent_tasks)
            ]

    # 等待所有任务完成
    async def join(self):
        # 阻塞，等待队列所有任务完成
        await self.queue.join()
        if self.workers:
            # 取消所有 worker 任务
            for worker in self.workers:
                worker.cancel()
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers = None

    # 事件监听
    def on_task_done(self, listener: Callable):
        self.task_done_callbacks.append(listener)

    def on_all_tasks_done(self, listener: Callable):
        self.all_tasks_done_callbacks.append(listener)

    # 队列清空的事件触发
    async def _event_listener_all(
        self, event: asyncio.Event, listener: Callable
    ):
        while True:
            await event.wait()
            listener(self.all_done_list)
            self.all_done_list = []
            event.clear()

    # 单个任务完成的事件触发
    async def _event_listener(self, event: asyncio.Event, listener: Callable):
        while True:
            await event.wait()
            listener(self.task_done_config)
            event.clear()


# 测试任务
async def sample_task(n):
    print(f"Task {n} started")
    await asyncio.sleep(n)
    print(f"Task {n} completed")


# TEST 测试代码
async def testFn():
    queue = AsyncTaskQueue(max_concurrent_tasks=1)
    queue.on_task_done(lambda x: print(f"one done: {x}"))
    queue.on_all_tasks_done(lambda x: print(f"all done: {x}"))
    for i in [10, 4, 1, 3, 2, 9, 1]:
        queue.add_task(sample_task(i), {"time": i})

    await queue.start()
    # await asyncio.sleep(5)
    # queue.add_task(sample_task(5), {"time": 5})
    await queue.join()  # 等待所有任务完成


if __name__ == "__main__":
    asyncio.run(testFn())
