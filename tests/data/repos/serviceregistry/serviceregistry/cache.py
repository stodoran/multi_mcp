"""Caching layer for service metadata.

This module provides caching to reduce lookups to the service registry.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class Cache:
    """Cache for service metadata and discovery information."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._timestamps: dict[str, float] = {}
        self._ttl: dict[str, float] = {}

    def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None

        timestamp = self._timestamps.get(key, 0)
        ttl = self._ttl.get(key, 300)

        if time.time() - timestamp > ttl:
            logger.debug(f"Cache entry {key} expired")
            return None

        return self._cache[key]

    def set(self, key: str, value: Any, ttl: float = 300) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live
        """
        self._cache[key] = value
        self._timestamps[key] = time.time()
        self._ttl[key] = ttl

        logger.debug(f"Cached {key} with TTL {ttl}")

    def invalidate(self, key: str) -> None:
        """Invalidate a cache entry.

        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
            self._ttl.pop(key, None)
            logger.debug(f"Invalidated cache entry {key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()
        self._ttl.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            'total_entries': len(self._cache),
            'expired_entries': sum(
                1 for key in self._cache
                if time.time() - self._timestamps.get(key, 0) > self._ttl.get(key, 300)
            )
        }
