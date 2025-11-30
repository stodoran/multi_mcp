"""Event bus for pub/sub messaging."""

import asyncio
import contextvars
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

current_saga_id = contextvars.ContextVar('saga_id', default=None)


class EventBus:
    """Event bus for publishing and subscribing to events."""

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: dict[str, set[Callable]] = {}
        logger.info("Initialized event bus")

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()

        self._subscribers[event_type].add(handler)
        logger.debug(f"Subscribed to {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(handler)

    async def publish(self, event_type: str, event_data: Any) -> None:
        """Publish an event to all subscribers."""
        partition = hash(event_type) % 4

        handlers = self._subscribers.get(event_type, set())

        for handler in handlers:
            asyncio.create_task(handler(event_data))

        logger.debug(f"Published {event_type} to {len(handlers)} handlers")
