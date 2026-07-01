# from typing import TypeVar, Awaitable
import asyncio


class AsyncTaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self._worker_task = None
        self._worker_running = False
        self._lock = asyncio.Lock()

    _sleep_time = 1
    _retry_sleep_time = 30
    _retry_times = 0

    async def _worker(self):
        while self._worker_running:
            await asyncio.sleep(AsyncTaskQueue._sleep_time)  # 确保任务之间的间隔
            task, future, retries, kwargs, dicargs = await self.queue.get()
            asyncio.create_task(self._execute_task(task, future, retries, kwargs, dicargs))
            if self.queue.empty():
                self._worker_running = False
            self.queue.task_done()

    async def _execute_task(self, task, future, retries, kwargs, dicargs):
        while retries >= 0:
            try:
                result = await task(*kwargs, **dicargs)
                if not future.done():
                    future.set_result(result)
                break
            except Exception as e:
                if retries == 0:
                    if not future.done():
                        future.set_exception(e)
                        break
                print(f"task执行失败, 等待{AsyncTaskQueue._retry_sleep_time}秒后开始重试, retries={retries}")
                await asyncio.sleep(AsyncTaskQueue._retry_sleep_time)  # 确保任务之间的间隔
                retries -= 1

    def _start_worker(self):
        self._worker_running = True
        self._worker_task = asyncio.create_task(self._worker())

    async def add_task(self, task, *kwargs, **dicargs):
        future = asyncio.get_event_loop().create_future()
        retries = AsyncTaskQueue._retry_times  # 设定重试次数
        async with self._lock:
            await self.queue.put((task, future, retries, kwargs, dicargs))
            if not self._worker_running:
                self._start_worker()
        return future

TaskQueue = AsyncTaskQueue()
