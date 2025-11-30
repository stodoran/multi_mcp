"""Snapshot manager for event store optimization."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages snapshots for event replay optimization."""

    def __init__(self):
        """Initialize snapshot manager."""
        self._snapshots: dict[str, dict[str, Any]] = {}
        logger.info("Initialized snapshot manager")

    def create_snapshot(self, aggregate_id: str, sequence: int, state: dict[str, Any]) -> str:
        """Create a snapshot of current state."""
        snapshot_id = f"snap_{sequence}"

        self._snapshots[aggregate_id] = {
            "snapshot_id": snapshot_id,
            "sequence": sequence,
            "state": state,
        }

        logger.info(f"Created snapshot {snapshot_id} for {aggregate_id}")
        return snapshot_id

    def get_snapshot(self, aggregate_id: str) -> dict[str, Any] | None:
        """Get the latest snapshot for an aggregate."""
        return self._snapshots.get(aggregate_id)
