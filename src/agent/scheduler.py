from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    name: str
    handler: Callable[[], Awaitable[None]]
    interval_seconds: int
    enabled: bool = True
    run_count: int = 0
    last_error: str | None = None
    _task: asyncio.Task | None = field(default=None, repr=False)


class AgentScheduler:
    def __init__(self):
        self.tasks: dict[str, ScheduledTask] = {}
        self._running: bool = False

    def register(self, name: str, handler: Callable[[], Awaitable[None]], interval_seconds: int) -> None:
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already registered")
        self.tasks[name] = ScheduledTask(name=name, handler=handler, interval_seconds=interval_seconds)
        logger.info(f"Registered task: {name} (every {interval_seconds}s)")

    def cancel(self, name: str) -> bool:
        """Cancel a running scheduled task."""
        if name not in self.tasks:
            return False
        task = self.tasks[name]
        task.enabled = False
        if task._task and not task._task.done():
            task._task.cancel()
        logger.info(f"Cancelled task: {name}")
        return True

    def list_tasks(self) -> list[dict]:
        return [
            {"name": t.name, "interval": t.interval_seconds, "enabled": t.enabled,
             "run_count": t.run_count, "last_error": t.last_error}
            for t in self.tasks.values()
        ]

    async def run_once(self, name: str) -> None:
        if name not in self.tasks:
            raise ValueError(f"Unknown task: {name}")
        await self.tasks[name].handler()

    async def _loop(self, task: ScheduledTask) -> None:
        while self._running and task.enabled:
            try:
                await task.handler()
                task.run_count += 1
                task.last_error = None
            except Exception as e:
                task.run_count += 1
                task.last_error = str(e)
                logger.error(f"Task {task.name} failed (run #{task.run_count}): {e}")
            await asyncio.sleep(task.interval_seconds)

    async def start(self) -> None:
        self._running = True
        for task in self.tasks.values():
            if task.enabled:
                task._task = asyncio.create_task(self._loop(task))
        logger.info(f"Scheduler started with {len(self.tasks)} tasks")

    async def stop(self) -> None:
        self._running = False
        for task in self.tasks.values():
            if task._task and not task._task.done():
                task._task.cancel()
        logger.info("Scheduler stopped")
