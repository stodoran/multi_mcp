"""Result storage for completed tasks.

This module manages storage of task execution results and statistics.
"""

from datetime import datetime
from typing import Any


class ResultStorage:
    """Storage for task results and execution statistics."""

    def __init__(self):
        self._results: dict[str, Any] = {}
        self._retry_counts: dict[str, int] = {}
        self._timestamps: dict[str, datetime] = {}

    def store_result(self, task_id: str, result: Any) -> None:
        """Store the result of a completed task.

        Args:
            task_id: Unique task identifier
            result: The task result to store
        """
        self._results[task_id] = result
        self._timestamps[task_id] = datetime.now()

    def get_result(self, task_id: str) -> Any | None:
        """Retrieve a stored result.

        Args:
            task_id: Unique task identifier

        Returns:
            The stored result or None if not found
        """
        return self._results.get(task_id)

    def increment_retry_count(self, task_id: str) -> int:
        """Increment and return the retry count for a task.

        Args:
            task_id: Unique task identifier

        Returns:
            The updated retry count
        """
        current_count = self._retry_counts.get(task_id, 0)
        new_count = current_count + 1
        self._retry_counts[task_id] = new_count
        return new_count

    def get_retry_count(self, task_id: str) -> int:
        """Get the current retry count for a task.

        Args:
            task_id: Unique task identifier

        Returns:
            The retry count (0 if not found)
        """
        return self._retry_counts.get(task_id, 0)

    def clear_task(self, task_id: str) -> None:
        """Clear all data for a task.

        Args:
            task_id: Unique task identifier
        """
        self._results.pop(task_id, None)
        self._retry_counts.pop(task_id, None)
        self._timestamps.pop(task_id, None)

    def get_all_results(self) -> dict[str, Any]:
        """Get all stored results.

        Returns:
            Dictionary mapping task IDs to results
        """
        return dict(self._results)
