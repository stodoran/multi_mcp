"""Task scheduler for periodic and delayed task execution.

This module provides scheduling capabilities for recurring and one-time delayed tasks.
"""

import threading
import time
import uuid
from collections.abc import Callable

from .queue import TaskQueue


class ScheduledJob:
    """Represents a scheduled job."""

    def __init__(
        self,
        job_id: str,
        func: Callable,
        interval: float,
        args: tuple = (),
        kwargs: dict = None
    ):
        self.job_id = job_id
        self.func = func
        self.interval = interval
        self.args = args
        self.kwargs = kwargs or {}
        self.timer: threading.Timer | None = None
        self.paused = False


class Scheduler:
    """Scheduler for periodic and one-time tasks."""

    def __init__(self, queue: TaskQueue):
        self._queue = queue
        self._jobs: dict[str, ScheduledJob] = {}
        self._lock = threading.Lock()

    def schedule_periodic(
        self,
        func: Callable,
        interval: float,
        args: tuple = (),
        kwargs: dict = None,
        job_id: str = None
    ) -> str:
        """Schedule a function to run periodically.

        Args:
            func: The function to execute
            interval: Interval in seconds between executions
            args: Positional arguments
            kwargs: Keyword arguments
            job_id: Optional job identifier (generated if not provided)

        Returns:
            The job identifier
        """
        if job_id is None:
            job_id = str(uuid.uuid4())

        with self._lock:
            job = ScheduledJob(job_id, func, interval, args, kwargs)
            self._jobs[job_id] = job
            self._schedule_next_run(job)

        return job_id

    def _schedule_next_run(self, job: ScheduledJob) -> None:
        """Schedule the next run of a periodic job."""
        if job.paused:
            return

        job.timer = threading.Timer(job.interval, self._execute_job, args=(job,))
        job.timer.daemon = True
        job.timer.start()

    def _execute_job(self, job: ScheduledJob) -> None:
        """Execute a scheduled job."""
        if job.paused:
            return

        task_id = f"{job.job_id}_{int(time.time() * 1000)}"

        try:
            self._queue.add_task(
                task_id=task_id,
                func=job.func,
                args=job.args,
                kwargs=job.kwargs
            )
        except Exception as e:
            print(f"Failed to enqueue job {job.job_id}: {e}")

        if not job.paused:
            self._schedule_next_run(job)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job.

        Args:
            job_id: The job identifier

        Returns:
            True if job was canceled, False if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            job.paused = True

            if job.timer:
                job.timer.cancel()

            return True

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: The job identifier

        Returns:
            True if job was resumed, False if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            job.paused = False
            self._schedule_next_run(job)
            return True

    def remove_job(self, job_id: str) -> bool:
        """Permanently remove a job.

        Args:
            job_id: The job identifier

        Returns:
            True if job was removed, False if not found
        """
        with self._lock:
            job = self._jobs.pop(job_id, None)
            if not job:
                return False

            if job.timer:
                job.timer.cancel()

            return True

    def get_all_jobs(self) -> dict[str, ScheduledJob]:
        """Get all scheduled jobs."""
        with self._lock:
            return dict(self._jobs)
