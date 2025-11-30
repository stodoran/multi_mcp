"""Task executor with connection pooling."""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

class Executor:
    """Executes plugin tasks."""

    def __init__(self, resource_pool: Any):
        self._pool = resource_pool
        self._queue = asyncio.Queue(maxsize=1000)
        logger.info("Initialized executor")

    async def execute(self, plugin: Any, data: Any) -> Any:
        """Execute plugin with resource."""
        conn = await self._pool.acquire()

        try:
            result = await plugin.process(data, conn)
            return result
        finally:
            await self._pool.release(conn)

    async def run_subtask(self, plugin: Any, data: Any) -> Any:
        """Run subtask (can cause nested acquisition)."""
        conn = await self._pool.acquire()

        try:
            result = await plugin.process_sub(data, conn)
            return result
        finally:
            await self._pool.release(conn)
