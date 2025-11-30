"""Cache storage implementation with TTL support."""

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    key: str
    value: Any
    expiry_time: float
    created_at: float
    metadata: dict[str, Any]


class CacheStorage:
    """Local storage for cache entries with TTL support.

    Stores cache data and expiry information.
    """

    def __init__(self):
        """Initialize cache storage."""
        self._data: dict[str, CacheEntry] = {}
        self._callbacks: set = set()
        logger.info("Initialized cache storage")

    def store(self, key: str, value: Any, expiry_time: float, metadata: dict | None = None) -> None:
        """Store a cache entry.

        Args:
            key: Cache key
            value: Value to cache
            expiry_time: Absolute expiry timestamp
            metadata: Optional metadata
        """
        entry = CacheEntry(
            key=key,
            value=value,
            expiry_time=expiry_time,
            created_at=time.time(),
            metadata=metadata or {}
        )
        self._data[key] = entry
        logger.debug(f"Stored key {key}, expires at {expiry_time}")

    def get(self, key: str) -> Any | None:
        """Retrieve a cache entry.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._data.get(key)
        if not entry:
            return None

        if entry.expiry_time < time.time():
            self._evict(key)
            return None

        return entry.value

    def get_entry(self, key: str) -> CacheEntry | None:
        """Get full cache entry including metadata.

        Args:
            key: Cache key

        Returns:
            Cache entry or None
        """
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        """Delete a cache entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        if key in self._data:
            self._evict(key)
            return True
        return False

    def _evict(self, key: str) -> None:
        """Evict an entry and notify callbacks.

        Args:
            key: Key to evict
        """
        if key in self._data:
            del self._data[key]
            for callback in self._callbacks:
                try:
                    callback(key)
                except Exception as e:
                    logger.error(f"Callback error during eviction of {key}: {e}")

    def register_eviction_callback(self, callback) -> None:
        """Register a callback for eviction events.

        Using WeakSet to prevent memory leaks from dangling callbacks.

        Args:
            callback: Callback function(key)
        """
        self._callbacks.add(callback)

    def size(self) -> int:
        """Get number of entries in storage.

        Returns:
            Number of entries
        """
        return len(self._data)

    def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            key for key, entry in self._data.items()
            if entry.expiry_time < now
        ]

        for key in expired_keys:
            self._evict(key)

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired entries")

        return len(expired_keys)

    def get_all_keys(self) -> set[str]:
        """Get all keys in storage.

        Returns:
            Set of all keys
        """
        return set(self._data.keys())

    def clear(self) -> None:
        """Clear all entries from storage."""
        count = len(self._data)
        self._data.clear()
        logger.info(f"Cleared {count} entries from storage")
