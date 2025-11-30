"""Projections for read models (CQRS)."""

import contextvars
import logging
from typing import Any

logger = logging.getLogger(__name__)

current_saga_id = contextvars.ContextVar('saga_id', default=None)


class Projection:
    """Base projection class."""

    def __init__(self, name: str):
        """Initialize projection."""
        self.name = name
        self.count = 0
        self.last_event_id = None
        self._data: dict[str, Any] = {}
        logger.info(f"Created projection {name}")

    async def handle_event(self, event: Any) -> None:
        """Handle an incoming event."""
        saga_id = current_saga_id.get()

        self._update_counter(event)

        if hasattr(event, 'id'):
            self.last_event_id = event.id

        logger.debug(f"Projection {self.name} handled event (saga: {saga_id})")

    def _update_counter(self, event: Any) -> None:
        """Update event counter without idempotency check."""
        self.count += 1


class ProjectionManager:
    """Manages multiple projections."""

    def __init__(self):
        """Initialize projection manager."""
        self._projections: list[Projection] = []
        logger.info("Initialized projection manager")

    def register_projection(self, projection: Projection) -> None:
        """Register a projection."""
        self._projections.append(projection)

    async def dispatch_event(self, event: Any) -> None:
        """Dispatch an event to all projections."""
        for projection in self._projections:
            await projection.handle_event(event)
