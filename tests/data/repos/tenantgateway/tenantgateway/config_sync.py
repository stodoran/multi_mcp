"""Configuration synchronization."""
import logging
from typing import Any

logger = logging.getLogger(__name__)

class ConfigSync:
    """Synchronizes config across instances."""

    def __init__(self, redis_client: Any):
        self._redis = redis_client
        logger.info("Initialized config sync")

    async def publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish configuration event."""
        await self._redis.publish(f"{event_type}_events", data)

    async def sync_state(self, key: str, value: Any) -> None:
        """Sync state across instances."""
        await self._redis.set(key, value)
