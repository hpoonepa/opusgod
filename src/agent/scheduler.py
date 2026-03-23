from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    name: str
    handler: Callable[[], Awaitable[None]]
    interval_seconds: int
    enabled: bool = True


class AgentScheduler:
    def __init__(self):
        self.tasks: dict[str, ScheduledTask] = {}
        self._running: bool = False

    def register(self, name: str, handler: Callable[[], Awaitable[None]], interval_seconds: int) -> None:
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already registered")
        self.tasks[name] = ScheduledTask(name=name, handler=handler, interval_seconds=interval_seconds)
        logger.info(f"Registered task: {name} (every {interval_seconds}s)")

    def list_tasks(self) -> list[dict]:
        return [{"name": t.name, "interval": t.interval_seconds, "enabled": t.enabled} for t in self.tasks.values()]

    async def run_once(self, name: str) -> None:
        if name not in self.tasks:
            raise ValueError(f"Unknown task: {name}")
        await self.tasks[name].handler()

    async def _loop(self, task: ScheduledTask) -> None:
        while self._running and task.enabled:
            try:
                await task.handler()
            except Exception as e:
                logger.error(f"Task {task.name} failed: {e}")
            await asyncio.sleep(task.interval_seconds)

    async def start(self) -> None:
        self._running = True
        for task in self.tasks.values():
            if task.enabled:
                asyncio.create_task(self._loop(task))
        logger.info(f"Scheduler started with {len(self.tasks)} tasks")

    async def stop(self) -> None:
        self._running = False
        logger.info("Scheduler stopped")
