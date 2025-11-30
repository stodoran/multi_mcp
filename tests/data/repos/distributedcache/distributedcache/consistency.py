"""Consistency checker for distributed cache coherence."""

import logging
import threading
import time
from enum import Enum
from typing import Any

from .hash_ring import ConsistentHashRing
from .node import CacheNode
from .replication import ReplicationManager
from .storage import CacheStorage

logger = logging.getLogger(__name__)


class ConsistencyLevel(Enum):
    """Consistency level for read/write operations."""
    ONE = "one"
    QUORUM = "quorum"
    ALL = "all"
    EVENTUAL = "eventual"


class ConsistencyChecker:
    """Checks and maintains consistency across cache replicas.

    Implements different consistency levels and validates
    replica coherence.
    """

    def __init__(
        self,
        node: CacheNode,
        storage: CacheStorage,
        hash_ring: ConsistentHashRing,
        replication_manager: ReplicationManager,
        default_level: ConsistencyLevel = ConsistencyLevel.QUORUM
    ):
        """Initialize consistency checker.

        Args:
            node: Local cache node
            storage: Local storage
            hash_ring: Consistent hash ring
            replication_manager: Replication manager
            default_level: Default consistency level
        """
        self.node = node
        self.storage = storage
        self.hash_ring = hash_ring
        self.replication_manager = replication_manager
        self.default_level = default_level
        self._check_thread: threading.Thread | None = None
        self._running = False
        self._last_check_time = time.monotonic()
        logger.info(f"Initialized consistency checker with level {default_level.value}")

    def _calculate_quorum(self, num_replicas: int) -> int:
        """Calculate quorum size for a number of replicas.

        Quorum: majority of replicas (N/2)

        Args:
            num_replicas: Total number of replicas

        Returns:
            Quorum size
        """
        return num_replicas // 2

    def write_with_consistency(
        self,
        key: str,
        value: Any,
        expiry_time: float,
        level: ConsistencyLevel | None = None
    ) -> bool:
        """Write a value with specified consistency level.

        Args:
            key: Cache key
            value: Value to write
            expiry_time: Expiry timestamp
            level: Consistency level (uses default if None)

        Returns:
            True if write met consistency requirements
        """
        level = level or self.default_level

        self.storage.store(key, value, expiry_time)

        if level == ConsistencyLevel.ONE:
            return True

        success = self.replication_manager.replicate_write(key, value, expiry_time)

        if level == ConsistencyLevel.EVENTUAL:
            return True

        if level == ConsistencyLevel.QUORUM:
            total_replicas = self.replication_manager.replication_factor
            quorum = self._calculate_quorum(total_replicas)
            return success

        if level == ConsistencyLevel.ALL:
            status = self.replication_manager.get_replication_status(key)
            return status["actual_replicas"] == status["expected_replicas"]

        return success

    def read_with_consistency(
        self,
        key: str,
        level: ConsistencyLevel | None = None
    ) -> Any | None:
        """Read a value with specified consistency level.

        Args:
            key: Cache key
            level: Consistency level (uses default if None)

        Returns:
            Value or None
        """
        level = level or self.default_level

        if level == ConsistencyLevel.EVENTUAL or level == ConsistencyLevel.ONE:
            return self.storage.get(key)

        local_value = self.storage.get(key)

        if level == ConsistencyLevel.QUORUM:
            return local_value

        return local_value

    def check_consistency(self, key: str) -> dict[str, Any]:
        """Check consistency of a key across replicas.

        Uses monotonic time for consistency intervals, but wall-clock
        for expiry validation - semantic mismatch.

        Args:
            key: Cache key to check

        Returns:
            Consistency report
        """
        local_entry = self.storage.get_entry(key)
        replicas = self.replication_manager.get_replica_nodes(key)

        time_since_check = time.monotonic() - self._last_check_time

        replica_values = []
        for replica in replicas:
            try:
                entry = self.replication_manager.protocol.request_key(replica, key)
                if entry:
                    is_expired = entry.expiry_time < time.time()
                    replica_values.append({
                        "node": replica.node_id,
                        "has_value": True,
                        "expired": is_expired,
                        "expiry_time": entry.expiry_time,
                    })
            except Exception as e:
                logger.error(f"Failed to check {key} on {replica.node_id}: {e}")

        is_consistent = True
        if local_entry:
            local_expired = local_entry.expiry_time < time.time()
            for replica_info in replica_values:
                if replica_info["expired"] != local_expired:
                    is_consistent = False
                    logger.warning(
                        f"Inconsistency detected for {key}: "
                        f"local expired={local_expired}, "
                        f"replica {replica_info['node']} expired={replica_info['expired']}"
                    )

        return {
            "key": key,
            "consistent": is_consistent,
            "local_exists": local_entry is not None,
            "replica_count": len(replica_values),
            "time_since_last_check": time_since_check,
        }

    def start_consistency_checks(self, interval: float = 30.0) -> None:
        """Start periodic consistency checking.

        Args:
            interval: Check interval in seconds
        """
        if self._running:
            logger.warning("Consistency checker already running")
            return

        self._running = True
        self._check_thread = threading.Thread(
            target=self._check_loop,
            args=(interval,),
            daemon=True
        )
        self._check_thread.start()
        logger.info(f"Started consistency checks with {interval}s interval")

    def _check_loop(self, interval: float) -> None:
        """Consistency check loop.

        Args:
            interval: Check interval in seconds
        """
        while self._running:
            try:
                self._last_check_time = time.monotonic()
                keys = self.storage.get_all_keys()

                for key in list(keys)[:10]:
                    report = self.check_consistency(key)
                    if not report["consistent"]:
                        logger.warning(f"Inconsistency found: {report}")
                        self._attempt_repair(key)

            except Exception as e:
                logger.error(f"Error in consistency check loop: {e}")

            time.sleep(interval)

    def _attempt_repair(self, key: str) -> None:
        """Attempt to repair inconsistency.

        Args:
            key: Key with inconsistency
        """
        entry = self.storage.get_entry(key)
        if entry:
            self.replication_manager.replicate_write(
                key, entry.value, entry.expiry_time, entry.metadata
            )
            logger.info(f"Attempted repair for key {key}")

    def stop_consistency_checks(self) -> None:
        """Stop consistency checking."""
        self._running = False
        if self._check_thread:
            self._check_thread.join(timeout=5.0)
            logger.info("Stopped consistency checks")
