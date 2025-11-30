"""Scheduler for long-running workflows."""

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """Scheduler for periodic and delayed workflow execution."""

    def __init__(self, max_workers: int = 10):
        """Initialize scheduler."""
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._scheduled_tasks: dict[str, Any] = []
        logger.info(f"Initialized scheduler with {max_workers} workers")

    async def schedule_delayed(self, task: Callable, delay: float) -> str:
        """Schedule a task with delay."""
        task_id = f"task_{len(self._scheduled_tasks)}"

        await asyncio.sleep(delay)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, task)

        logger.info(f"Executed delayed task {task_id}")
        return task_id
