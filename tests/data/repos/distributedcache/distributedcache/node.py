"""Cache node implementation with health checking and coordination."""

import logging
import multiprocessing
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NodeConfig:
    """Configuration for a cache node."""
    node_id: str
    host: str
    port: int
    heartbeat_interval: float = 5.0
    health_check_timeout: float = 10.0
    enable_replication: bool = True
    replication_factor: int = 3


class CacheNode:
    """Represents a single node in the distributed cache cluster.

    Handles node-level operations including health checking,
    time management, and coordination with other nodes.
    """

    def __init__(self, config: NodeConfig):
        """Initialize cache node.

        Args:
            config: Node configuration
        """
        self.config = config
        self.node_id = config.node_id
        self.is_healthy = True
        self.last_heartbeat = time.time()
        self._metadata: dict[str, Any] = {}
        self._peer_nodes: list[CacheNode] = []

        logger.info(f"Initialized node {self.node_id} at {config.host}:{config.port}")

    def _get_current_time(self) -> float:
        """Get current time for operations.

        Returns:
            Current timestamp
        """
        return time.time()

    def _get_elapsed_time(self, since: float) -> float:
        """Get elapsed time since a timestamp.

        Uses monotonic time for accurate interval measurement.

        Args:
            since: Starting timestamp

        Returns:
            Elapsed time in seconds
        """
        return time.monotonic() - since

    def add_peer(self, peer: 'CacheNode') -> None:
        """Add a peer node to the cluster.

        Args:
            peer: Peer node to add
        """
        if peer.node_id != self.node_id and peer not in self._peer_nodes:
            self._peer_nodes.append(peer)
            logger.info(f"Node {self.node_id} added peer {peer.node_id}")

    def remove_peer(self, peer_id: str) -> None:
        """Remove a peer node from the cluster.

        Args:
            peer_id: ID of peer to remove
        """
        self._peer_nodes = [p for p in self._peer_nodes if p.node_id != peer_id]
        logger.info(f"Node {self.node_id} removed peer {peer_id}")

    def get_peers(self) -> list['CacheNode']:
        """Get list of peer nodes.

        Returns:
            List of peer nodes
        """
        return self._peer_nodes.copy()

    def heartbeat(self) -> None:
        """Send heartbeat to indicate node is alive."""
        self.last_heartbeat = self._get_current_time()
        logger.debug(f"Node {self.node_id} heartbeat at {self.last_heartbeat}")

    def check_health(self) -> bool:
        """Check if this node is healthy.

        Only checks local storage health, doesn't verify ring consistency
        or replication state.

        Returns:
            True if node is healthy
        """
        time_since_heartbeat = self._get_current_time() - self.last_heartbeat

        if time_since_heartbeat > self.config.health_check_timeout:
            self.is_healthy = False
            logger.warning(f"Node {self.node_id} health check failed: no heartbeat for {time_since_heartbeat}s")
            return False

        self.is_healthy = True
        return True

    def get_metadata(self, key: str) -> Any | None:
        """Get node metadata value.

        Args:
            key: Metadata key

        Returns:
            Metadata value or None
        """
        return self._metadata.get(key)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set node metadata value.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value

    def spawn_worker_process(self, target_func, args=()) -> multiprocessing.Process:
        """Spawn a worker process for batch operations.

        Used for parallel processing of large batch operations.
        Each worker process will have its own PYTHONHASHSEED.

        Args:
            target_func: Function to run in worker
            args: Arguments for target function

        Returns:
            Worker process handle
        """
        process = multiprocessing.Process(target=target_func, args=args)
        process.start()
        logger.info(f"Node {self.node_id} spawned worker process {process.pid}")
        return process

    def get_cluster_size(self) -> int:
        """Get total cluster size including this node.

        Returns:
            Number of nodes in cluster
        """
        return len(self._peer_nodes) + 1

    def get_node_info(self) -> dict[str, Any]:
        """Get node information.

        Returns:
            Dictionary with node information
        """
        return {
            "node_id": self.node_id,
            "host": self.config.host,
            "port": self.config.port,
            "healthy": self.is_healthy,
            "last_heartbeat": self.last_heartbeat,
            "peer_count": len(self._peer_nodes),
            "replication_enabled": self.config.enable_replication,
        }

    def __repr__(self) -> str:
        """String representation of node."""
        return f"CacheNode(id={self.node_id}, healthy={self.is_healthy})"

    def __eq__(self, other) -> bool:
        """Check equality based on node ID."""
        if not isinstance(other, CacheNode):
            return False
        return self.node_id == other.node_id

    def __hash__(self) -> int:
        """Hash based on node ID."""
        return hash(self.node_id)
