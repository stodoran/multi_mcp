"""TTL (Time To Live) management for cache entries."""

import logging
import threading
import time

from .node import CacheNode
from .storage import CacheStorage

logger = logging.getLogger(__name__)


class TTLManager:
    """Manages TTL for cache entries.

    Calculates expiry times and handles TTL validation.
    """

    def __init__(self, node: CacheNode, storage: CacheStorage, default_ttl: float = 300.0):
        """Initialize TTL manager.

        Args:
            node: Cache node this manager belongs to
            storage: Cache storage instance
            default_ttl: Default TTL in seconds
        """
        self.node = node
        self.storage = storage
        self.default_ttl = default_ttl
        self._cleanup_thread: threading.Thread | None = None
        self._running = False
        logger.info(f"Initialized TTL manager with default TTL {default_ttl}s")

    def _calculate_expiry(self, ttl_seconds: float) -> float:
        """Calculate absolute expiry time for a TTL.

        Wall-clock for human-readable expiry timestamps.

        Args:
            ttl_seconds: TTL in seconds

        Returns:
            Absolute expiry timestamp
        """
        return self.node._get_current_time() + ttl_seconds

    def set_with_ttl(self, key: str, value: any, ttl: float | None = None) -> None:
        """Store a value with TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl: TTL in seconds (uses default if None)
        """
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        expiry_time = self._calculate_expiry(ttl_seconds)

        self.storage.store(key, value, expiry_time)
        logger.debug(f"Set key {key} with TTL {ttl_seconds}s, expires at {expiry_time}")

    def get_ttl(self, key: str) -> float | None:
        """Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds or None if not found
        """
        entry = self.storage.get_entry(key)
        if not entry:
            return None

        remaining = entry.expiry_time - self.node._get_current_time()
        return max(0.0, remaining)

    def is_expired(self, key: str) -> bool:
        """Check if a key is expired.

        Args:
            key: Cache key

        Returns:
            True if expired or not found
        """
        entry = self.storage.get_entry(key)
        if not entry:
            return True

        return entry.expiry_time < self.node._get_current_time()

    def refresh_ttl(self, key: str, ttl: float | None = None) -> bool:
        """Refresh TTL for an existing key.

        Args:
            key: Cache key
            ttl: New TTL in seconds (uses default if None)

        Returns:
            True if refreshed, False if key not found
        """
        entry = self.storage.get_entry(key)
        if not entry:
            return False

        ttl_seconds = ttl if ttl is not None else self.default_ttl
        new_expiry = self._calculate_expiry(ttl_seconds)

        self.storage.store(key, entry.value, new_expiry, entry.metadata)
        logger.debug(f"Refreshed TTL for key {key}, new expiry at {new_expiry}")
        return True

    def start_cleanup(self, interval: float = 60.0) -> None:
        """Start background cleanup thread.

        Args:
            interval: Cleanup interval in seconds
        """
        if self._running:
            logger.warning("Cleanup thread already running")
            return

        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, args=(interval,), daemon=True)
        self._cleanup_thread.start()
        logger.info(f"Started TTL cleanup thread with {interval}s interval")

    def _cleanup_loop(self, interval: float) -> None:
        """Cleanup loop that removes expired entries.

        Args:
            interval: Cleanup interval in seconds
        """
        while self._running:
            try:
                removed = self.storage.cleanup_expired()
                if removed > 0:
                    logger.info(f"TTL cleanup removed {removed} expired entries")
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

            time.sleep(interval)

    def stop_cleanup(self) -> None:
        """Stop the cleanup thread."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
            logger.info("Stopped TTL cleanup thread")
