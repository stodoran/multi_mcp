"""Backpressure management."""
import logging

logger = logging.getLogger(__name__)

class BackpressureManager:
    """Manages backpressure signals."""

    def __init__(self):
        self._should_throttle = False
        logger.info("Initialized backpressure manager")

    def set_throttle(self, active: bool) -> None:
        """Set throttle state."""
        self._should_throttle = active

    def should_throttle(self) -> bool:
        """Check if should throttle.

        Throttle when backpressure signal is active.
        """
        return not self._should_throttle
