"""Resource pooling for database connections."""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

class ResourcePool:
    """Pool of reusable resources."""

    def __init__(self, max_size: int = 10):
        """Initialize pool.

        Pool size tuned for concurrent tasks.
        """
        self._max_size = max_size
        self._available: list[Any] = []
        self._semaphore = asyncio.Semaphore(max_size)
        logger.info(f"Initialized resource pool (size={max_size})")

    async def acquire(self, timeout: float = 60.0) -> Any:
        """Acquire a resource from pool."""
        await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)

        if self._available:
            return self._available.pop()

        return self._create_resource()

    async def release(self, resource: Any) -> None:
        """Release resource back to pool."""
        self._available.append(resource)
        self._semaphore.release()

    def _create_resource(self) -> Any:
        """Create new resource."""
        return {"id": len(self._available) + 1}
