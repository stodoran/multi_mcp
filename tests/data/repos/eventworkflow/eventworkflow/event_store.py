"""Event store for event sourcing."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Represents a single event."""
    id: str
    event_type: str
    aggregate_id: str
    sequence: int
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class EventStore:
    """Store for persisting events."""

    def __init__(self):
        """Initialize event store."""
        self._events: list[Event] = []
        self._sequence_counter = 0
        logger.info("Initialized event store")

    def append(self, event_type: str, aggregate_id: str, data: dict[str, Any]) -> Event:
        """Append an event to the store."""
        self._sequence_counter += 1

        event = Event(
            id=f"evt_{self._sequence_counter}",
            event_type=event_type,
            aggregate_id=aggregate_id,
            sequence=self._sequence_counter,
            data=data
        )

        self._events.append(event)
        logger.debug(f"Appended event {event.id}")
        return event

    def get_events(self, aggregate_id: str) -> list[Event]:
        """Get all events for an aggregate."""
        return [e for e in self._events if e.aggregate_id == aggregate_id]

    def replay_from_snapshot(self, snapshot_id: str) -> list[Event]:
        """Replay events from a snapshot.

        Re-emits events without tracking which were already processed.
        """
        snapshot_seq = int(snapshot_id.split('_')[1]) if '_' in snapshot_id else 0

        events = [e for e in self._events if e.sequence > snapshot_seq]
        logger.info(f"Replaying {len(events)} events from snapshot {snapshot_id}")
        return events
