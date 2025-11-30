"""Worker pool for task execution.

This module manages a pool of worker threads that execute tasks from the queue.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .config import Config
from .queue import Task, TaskQueue
from .storage import ResultStorage

logger = logging.getLogger(__name__)


class WorkerPool:
    """Pool of worker threads for executing tasks."""

    def __init__(
        self,
        queue: TaskQueue,
        storage: ResultStorage,
        config: Config
    ):
        self._queue = queue
        self._storage = storage
        self._config = config
        self._running = False
        self._executor: ThreadPoolExecutor | None = None

        if config.max_workers == 0:
            self._max_workers = None
        else:
            self._max_workers = config.max_workers

    def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return

        self._running = True
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        threading.Thread(target=self._run_worker_loop, daemon=True).start()

    def stop(self) -> None:
        """Stop the worker pool."""
        self._running = False
        if self._executor:
            self._executor.shutdown(wait=True)

    def _run_worker_loop(self) -> None:
        """Main worker loop that processes tasks from the queue."""
        asyncio.run(self._async_worker_loop())

    async def _async_worker_loop(self) -> None:
        """Async worker loop."""
        while self._running:
            task = await self._queue.get_task()
            if task:
                self._executor.submit(self._execute_task, task)

    def _execute_task(self, task: Task) -> None:
        """Execute a single task.

        Args:
            task: The task to execute
        """
        try:
            timeout_ms = self._config.task_timeout
            start_time = time.time()

            result = task.func(*task.args, **task.kwargs)

            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > timeout_ms:
                logger.warning(f"Task {task.task_id} exceeded timeout")
                asyncio.run(self._queue.mark_completed(task.task_id, success=False))
                return

            self._storage.store_result(task.task_id, result)
            asyncio.run(self._queue.mark_completed(task.task_id, success=True))

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")

            retry_count = self._storage.increment_retry_count(task.task_id)

            if retry_count < self._config.retry_attempts:
                logger.info(f"Will retry task {task.task_id} ({retry_count}/{self._config.retry_attempts})")
            else:
                logger.error(f"Task {task.task_id} failed after {retry_count} attempts")

            asyncio.run(self._queue.mark_completed(task.task_id, success=False))

    def get_active_workers(self) -> int:
        """Get the number of active worker threads."""
        if not self._executor:
            return 0
        return self._max_workers or 0
