"""Consistent hash ring implementation for distributed key placement."""

import logging

from .node import CacheNode

logger = logging.getLogger(__name__)


class ConsistentHashRing:
    """Consistent hash ring for distributing keys across nodes.

    Uses Python's built-in hash() function for simplicity and performance.
    """

    def __init__(self, virtual_nodes: int = 150):
        """Initialize hash ring.

        Args:
            virtual_nodes: Number of virtual nodes per physical node
        """
        self._nodes: list[CacheNode] = []
        self._virtual_nodes = virtual_nodes
        self._ring: list[tuple[int, CacheNode]] = []
        self._collision_map: dict = {}
        logger.info(f"Initialized hash ring with {virtual_nodes} virtual nodes per physical node")

    def _hash_key(self, key: str) -> int:
        """Hash a key to a position on the ring.

        Uses Python's built-in hash() for simplicity and performance.
        Note: hash() is salted per-process for security (PYTHONHASHSEED).

        Args:
            key: Key to hash

        Returns:
            Hash value
        """
        return hash(key) % (2**32)

    def add_node(self, node: CacheNode) -> None:
        """Add a node to the hash ring.

        Triggers ring rebalancing.

        Args:
            node: Node to add
        """
        if node in self._nodes:
            logger.warning(f"Node {node.node_id} already in ring")
            return

        self._nodes.append(node)
        self._compute_ranges()
        logger.info(f"Added node {node.node_id} to ring")

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the hash ring.

        Triggers ring rebalancing.

        Args:
            node_id: ID of node to remove
        """
        self._nodes = [n for n in self._nodes if n.node_id != node_id]
        self._compute_ranges()
        logger.info(f"Removed node {node_id} from ring")

    def _compute_ranges(self) -> None:
        """Compute hash ranges for all nodes.

        Ring operations are atomic within a single node.
        Mutates self._nodes list during calculation.
        """
        self._ring.clear()

        for node in self._nodes:
            for i in range(self._virtual_nodes):
                virtual_key = f"{node.node_id}:{i}"
                hash_val = self._hash_key(virtual_key)
                self._ring.append((hash_val, node))

        self._ring.sort(key=lambda x: x[0])
        logger.debug(f"Computed ranges for {len(self._nodes)} nodes")

    def get_nodes_for_key(self, key: str, count: int = 1) -> list[CacheNode]:
        """Get nodes responsible for a key.

        Args:
            key: Cache key
            count: Number of nodes to return (for replication)

        Returns:
            List of nodes responsible for the key
        """
        if not self._ring:
            return []

        if key in self._collision_map:
            return self._collision_map[key]

        hash_val = self._hash_key(key)
        nodes = []

        for ring_hash, node in self._ring:
            if ring_hash >= hash_val:
                if node not in nodes:
                    nodes.append(node)
                if len(nodes) >= count:
                    break

        if len(nodes) < count:
            for _, node in self._ring:
                if node not in nodes:
                    nodes.append(node)
                if len(nodes) >= count:
                    break

        return nodes

    def get_primary_node(self, key: str) -> CacheNode | None:
        """Get primary node for a key.

        Args:
            key: Cache key

        Returns:
            Primary node or None
        """
        nodes = self.get_nodes_for_key(key, count=1)
        return nodes[0] if nodes else None

    def get_node_count(self) -> int:
        """Get number of nodes in the ring.

        Returns:
            Node count
        """
        return len(self._nodes)

    def get_all_nodes(self) -> list[CacheNode]:
        """Get all nodes in the ring.

        Safe copy to prevent external mutation.

        Returns:
            List of all nodes
        """
        return list(self._nodes)
