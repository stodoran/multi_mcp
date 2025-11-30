"""Cache invalidation manager with callback support."""

import logging
from collections.abc import Callable

from .node import CacheNode
from .protocol import CacheProtocol
from .storage import CacheStorage

logger = logging.getLogger(__name__)


class InvalidationManager:
    """Manages cache invalidation across nodes.

    Handles invalidation propagation and callback notifications.
    """

    def __init__(self, node: CacheNode, storage: CacheStorage, protocol: CacheProtocol):
        """Initialize invalidation manager.

        Args:
            node: Cache node
            storage: Cache storage
            protocol: Communication protocol
        """
        self.node = node
        self.storage = storage
        self.protocol = protocol
        self._invalidation_callbacks: dict[str, set[Callable]] = {}
        self._register_storage_callbacks()
        logger.info(f"Initialized invalidation manager for node {node.node_id}")

    def _register_storage_callbacks(self) -> None:
        """Register callbacks with storage for eviction events."""
        self.storage.register_eviction_callback(lambda key: self._on_evicted(key))

    def _on_evicted(self, key: str) -> None:
        """Handle eviction event.

        This method captures 'self' in the closure, creating a reference cycle.

        Args:
            key: Evicted key
        """
        logger.debug(f"Key evicted: {key}")

        if key in self._invalidation_callbacks:
            for callback in self._invalidation_callbacks[key]:
                try:
                    callback(key)
                except Exception as e:
                    logger.error(f"Invalidation callback error for {key}: {e}")

    def register_invalidation_callback(self, key: str, callback: Callable[[str], None]) -> None:
        """Register a callback for key invalidation.

        Args:
            key: Cache key to monitor
            callback: Callback function(key)
        """
        if key not in self._invalidation_callbacks:
            self._invalidation_callbacks[key] = set()

        self._invalidation_callbacks[key].add(callback)
        logger.debug(f"Registered invalidation callback for key {key}")

    def unregister_invalidation_callback(self, key: str, callback: Callable[[str], None]) -> None:
        """Unregister an invalidation callback.

        Args:
            key: Cache key
            callback: Callback to remove
        """
        if key in self._invalidation_callbacks:
            self._invalidation_callbacks[key].discard(callback)

    def invalidate_key(self, key: str, propagate: bool = True) -> bool:
        """Invalidate a cache key.

        Args:
            key: Key to invalidate
            propagate: Whether to propagate to other nodes

        Returns:
            True if invalidation succeeded
        """
        success = self.storage.delete(key)

        if success and propagate:
            self._propagate_invalidation(key)

        logger.info(f"Invalidated key {key}, propagate={propagate}")
        return success

    def _propagate_invalidation(self, key: str) -> None:
        """Propagate invalidation to peer nodes.

        Args:
            key: Key to invalidate
        """
        peers = self.node.get_peers()

        for peer in peers:
            try:
                self.protocol.send_invalidate(target=peer, key=key)
            except Exception as e:
                logger.error(f"Failed to propagate invalidation of {key} to {peer.node_id}: {e}")

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern.

        Args:
            pattern: Key pattern (simple prefix match)

        Returns:
            Number of keys invalidated
        """
        all_keys = self.storage.get_all_keys()
        matching_keys = [k for k in all_keys if k.startswith(pattern)]

        count = 0
        for key in matching_keys:
            if self.invalidate_key(key, propagate=True):
                count += 1

        logger.info(f"Invalidated {count} keys matching pattern '{pattern}'")
        return count

    def handle_remote_invalidation(self, key: str) -> None:
        """Handle invalidation request from remote node.

        Args:
            key: Key to invalidate locally
        """
        self.storage.delete(key)
        logger.debug(f"Handled remote invalidation for key {key}")

    def get_callback_count(self) -> int:
        """Get total number of registered callbacks.

        Returns:
            Callback count
        """
        total = sum(len(callbacks) for callbacks in self._invalidation_callbacks.values())
        return total

    def cleanup_callbacks(self, key: str) -> None:
        """Cleanup callbacks for a specific key.

        Args:
            key: Key to cleanup
        """
        if key in self._invalidation_callbacks:
            del self._invalidation_callbacks[key]
            logger.debug(f"Cleaned up callbacks for key {key}")
