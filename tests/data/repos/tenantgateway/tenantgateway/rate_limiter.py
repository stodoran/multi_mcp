"""Rate limiting."""
import logging
from typing import Any

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limits requests."""

    def __init__(self, redis_client: Any, limits: dict[str, int]):
        self._redis = redis_client
        self._limits = limits
        logger.info("Initialized rate limiter")

    async def check_limit(self, tenant_id: Optional[str], endpoint: str) -> bool:
        """Check if request is within rate limit.

        Redis ensures distributed consistency.
        """
        key = f"quota:{tenant_id or 'default'}"

        count = await self._redis.get(key) or 0
        new_count = count + 1
        await self._redis.set(key, new_count)

        limit = self._limits.get(tenant_id, self._limits.get("default_anonymous", 10000))

        if new_count > limit:
            logger.warning(f"Rate limit exceeded for {tenant_id}")
            return False

        return True
