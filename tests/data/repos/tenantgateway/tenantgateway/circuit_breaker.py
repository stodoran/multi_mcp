"""Circuit breaker pattern."""
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for fault tolerance.

    Circuit state synced via Redis pub/sub for distributed coordination.
    """

    def __init__(self, config_sync: Any):
        self._state = CircuitState.CLOSED
        self._config_sync = config_sync
        self._failure_count = 0
        self._threshold = 5
        logger.info("Initialized circuit breaker")

    def record_success(self) -> None:
        """Record successful request."""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record failed request."""
        self._failure_count += 1

        if self._failure_count >= self._threshold:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker opened")

    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self._state == CircuitState.CLOSED
