"""Configuration management for AsyncTaskQueue.

This module loads and manages configuration settings for the task queue system.
"""

from dataclasses import dataclass


@dataclass
class Config:
    """Configuration for the task queue system.

    Attributes:
        max_workers: Maximum number of worker threads.
                    0 means unlimited
        task_timeout: Task execution timeout in seconds
        queue_size: Maximum queue size
        retry_attempts: Number of retry attempts for failed tasks
    """

    max_workers: int = 0
    task_timeout: float = 30.0
    queue_size: int = 1000
    retry_attempts: int = 3

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'Config':
        """Create Config from dictionary."""
        return cls(
            max_workers=config_dict.get('max_workers', 0),
            task_timeout=config_dict.get('task_timeout', 30.0),
            queue_size=config_dict.get('queue_size', 1000),
            retry_attempts=config_dict.get('retry_attempts', 3)
        )

    def validate(self) -> bool:
        """Validate configuration values."""
        if self.queue_size <= 0:
            raise ValueError("queue_size must be positive")
        if self.task_timeout <= 0:
            raise ValueError("task_timeout must be positive")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")
        return True
