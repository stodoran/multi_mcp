"""Snapshot manager for event store optimization."""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages snapshots for event replay optimization."""

    def __init__(self):
        """Initialize snapshot manager."""
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized snapshot manager")

    def create_snapshot(self, aggregate_id: str, sequence: int, state: Dict[str, Any]) -> str:
        """Create a snapshot of current state."""
        snapshot_id = f"snap_{sequence}"

        self._snapshots[aggregate_id] = {
            "snapshot_id": snapshot_id,
            "sequence": sequence,
            "state": state,
        }

        logger.info(f"Created snapshot {snapshot_id} for {aggregate_id}")
        return snapshot_id

    def get_snapshot(self, aggregate_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest snapshot for an aggregate."""
        return self._snapshots.get(aggregate_id)
