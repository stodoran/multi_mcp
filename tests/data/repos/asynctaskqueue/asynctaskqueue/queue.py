"""Task queue management.

This module manages the task queue and task lifecycle.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a task in the queue."""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING


class QueueFullError(Exception):
    """Raised when attempting to add a task to a full queue."""
    pass


class TaskNotFoundError(Exception):
    """Raised when a task is not found in the queue."""
    pass


class TaskQueue:
    """Manages a queue of tasks for asynchronous execution."""

    def __init__(self, max_size: int = 1000):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size

    async def add_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None
    ) -> None:
        """Add a task to the queue.

        Args:
            task_id: Unique task identifier
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function

        Raises:
            QueueFullError: If the queue is at maximum capacity
        """
        async with self._lock:
            if len(self._tasks) >= self._max_size:
                raise QueueFullError(f"Queue is full (max size: {self._max_size})")

            task = Task(
                task_id=task_id,
                func=func,
                args=args,
                kwargs=kwargs or {}
            )
            self._tasks[task_id] = task
            await self._queue.put(task)

    async def get_task(self) -> Task | None:
        """Get the next task from the queue.

        Returns:
            The next task, or None if queue is empty (with timeout)
        """
        try:
            task = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            async with self._lock:
                if task.task_id in self._tasks:
                    self._tasks[task.task_id].status = TaskStatus.RUNNING
            return task
        except TimeoutError:
            return None

    async def mark_completed(self, task_id: str, success: bool = True) -> None:
        """Mark a task as completed or failed.

        Args:
            task_id: The task identifier
            success: Whether the task completed successfully
        """
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = (
                    TaskStatus.COMPLETED if success else TaskStatus.FAILED
                )

    async def remove_task(self, task_id: str) -> None:
        """Remove a task from the queue (cancels it).

        Args:
            task_id: The task identifier

        Raises:
            TaskNotFoundError: If task is not found
        """
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError(f"Task {task_id} not found")
            self._tasks[task_id].status = TaskStatus.CANCELLED
            del self._tasks[task_id]

    def get_status(self, task_id: str) -> TaskStatus | None:
        """Get the status of a task.

        Args:
            task_id: The task identifier

        Returns:
            The task status or None if not found
        """
        task = self._tasks.get(task_id)
        return task.status if task else None

    def get_pending_count(self) -> int:
        """Get the number of pending tasks."""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)

    def get_running_count(self) -> int:
        """Get the number of running tasks."""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
