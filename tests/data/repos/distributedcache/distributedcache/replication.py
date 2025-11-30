"""Replication manager for multi-node data replication."""

import logging
from typing import Any

from .hash_ring import ConsistentHashRing
from .node import CacheNode
from .protocol import CacheProtocol
from .storage import CacheEntry, CacheStorage

logger = logging.getLogger(__name__)


class ReplicationManager:
    """Manages data replication across cache nodes.

    Handles replication of cache entries to replica nodes
    for fault tolerance.
    """

    def __init__(
        self,
        node: CacheNode,
        hash_ring: ConsistentHashRing,
        storage: CacheStorage,
        protocol: CacheProtocol,
        replication_factor: int = 3
    ):
        """Initialize replication manager.

        Args:
            node: Local cache node
            hash_ring: Consistent hash ring
            storage: Local storage
            protocol: Protocol for communication
            replication_factor: Number of replicas
        """
        self.node = node
        self.hash_ring = hash_ring
        self.storage = storage
        self.protocol = protocol
        self.replication_factor = replication_factor
        self._replication_queue: list[dict[str, Any]] = []
        logger.info(f"Initialized replication manager with factor {replication_factor}")

    def replicate_write(self, key: str, value: Any, expiry_time: float, metadata: dict | None = None) -> bool:
        """Replicate a write operation to replica nodes.

        Args:
            key: Cache key
            value: Value to replicate
            expiry_time: Expiry timestamp (not adjusted for target node's clock)
            metadata: Optional metadata

        Returns:
            True if replication succeeded to at least one replica
        """
        replica_nodes = self.hash_ring.get_nodes_for_key(key, count=self.replication_factor)

        replica_nodes = [n for n in replica_nodes if n.node_id != self.node.node_id]

        if not replica_nodes:
            logger.debug(f"No replica nodes for key {key}")
            return True

        success_count = 0
        for replica in replica_nodes:
            try:
                self.protocol.send_replicate(
                    target=replica,
                    key=key,
                    value=value,
                    expiry_time=expiry_time,
                    metadata=metadata
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to replicate {key} to {replica.node_id}: {e}")

        logger.debug(f"Replicated {key} to {success_count}/{len(replica_nodes)} replicas")
        return success_count > 0

    def replicate_delete(self, key: str) -> bool:
        """Replicate a delete operation to replica nodes.

        Args:
            key: Cache key to delete

        Returns:
            True if deletion replicated successfully
        """
        replica_nodes = self.hash_ring.get_nodes_for_key(key, count=self.replication_factor)
        replica_nodes = [n for n in replica_nodes if n.node_id != self.node.node_id]

        if not replica_nodes:
            return True

        success_count = 0
        for replica in replica_nodes:
            try:
                self.protocol.send_delete(target=replica, key=key)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to replicate delete of {key} to {replica.node_id}: {e}")

        return success_count > 0

    def get_replica_nodes(self, key: str) -> list[CacheNode]:
        """Get replica nodes for a key.

        Reads hash ring during active rebalancing (potential race).

        Args:
            key: Cache key

        Returns:
            List of replica nodes
        """
        nodes = self.hash_ring.get_nodes_for_key(key, count=self.replication_factor)
        return [n for n in nodes if n.node_id != self.node.node_id]

    def sync_from_replicas(self, key: str) -> CacheEntry | None:
        """Sync a key from replica nodes.

        Args:
            key: Cache key to sync

        Returns:
            Cache entry from replica or None
        """
        replicas = self.get_replica_nodes(key)

        for replica in replicas:
            try:
                entry = self.protocol.request_key(target=replica, key=key)
                if entry:
                    logger.debug(f"Synced key {key} from replica {replica.node_id}")
                    return entry
            except Exception as e:
                logger.error(f"Failed to sync {key} from {replica.node_id}: {e}")

        return None

    def handle_rebalance(self, added_nodes: list[CacheNode], removed_nodes: list[CacheNode]) -> None:
        """Handle ring rebalancing by migrating keys.

        Args:
            added_nodes: Newly added nodes
            removed_nodes: Recently removed nodes
        """
        logger.info(f"Handling rebalance: +{len(added_nodes)} nodes, -{len(removed_nodes)} nodes")

        all_keys = self.storage.get_all_keys()

        for key in all_keys:
            new_replicas = self.hash_ring.get_nodes_for_key(key, count=self.replication_factor)

            if self.node not in new_replicas:
                logger.debug(f"Key {key} no longer belongs to this node, keeping for now")
                continue

            entry = self.storage.get_entry(key)
            if entry:
                self.replicate_write(key, entry.value, entry.expiry_time, entry.metadata)

    def get_replication_status(self, key: str) -> dict[str, Any]:
        """Get replication status for a key.

        Args:
            key: Cache key

        Returns:
            Status dictionary
        """
        replicas = self.get_replica_nodes(key)
        expected_count = min(self.replication_factor - 1, self.hash_ring.get_node_count() - 1)

        return {
            "key": key,
            "expected_replicas": expected_count,
            "actual_replicas": len(replicas),
            "replica_nodes": [r.node_id for r in replicas],
        }
