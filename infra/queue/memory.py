
import asyncio
from typing import Dict, Any

class TaskQueue:
    def __init__(self):
        self._queue = asyncio.Queue()

    async def put(self, task: Dict[str, Any]):
        await self._queue.put(task)

    async def get(self) -> Dict[str, Any]:
        return await self._queue.get()

    def task_done(self):
        self._queue.task_done()

# Singleton for MVP
task_queue = TaskQueue()
