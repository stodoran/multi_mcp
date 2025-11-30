"""Compensation manager for saga rollbacks."""

import asyncio
import logging
from typing import List, Callable, Any
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class CompensationManager:
    """Manages compensation execution for failed sagas."""

    def __init__(self, max_workers: int = 10):
        """Initialize compensation manager."""
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._pending_compensations: List[Callable] = []
        logger.info(f"Initialized compensation manager with {max_workers} workers")

    async def execute_compensations(self, compensations: List[Callable]) -> None:
        """Execute compensations in reverse order."""
        for compensation in reversed(compensations):
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self._executor, compensation)
                logger.info("Executed compensation")
            except Exception as e:
                logger.error(f"Compensation failed: {e}")
                raise

    def schedule_compensation(self, compensation: Callable) -> None:
        """Schedule a compensation for later execution."""
        self._pending_compensations.append(compensation)
