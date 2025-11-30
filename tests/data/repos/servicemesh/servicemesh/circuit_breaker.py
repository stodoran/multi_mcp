"""
Circuit breaker pattern implementation
Prevents cascading failures by opening circuit after threshold
"""

import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker with configurable failure thresholds
    BUG #2: Part of retry storm - doesn't coordinate test requests
    """

    def __init__(self, failure_threshold: int = 5, timeout_ms: int = 5000,
                 half_open_timeout_ms: int = 3000):
        self.failure_threshold = failure_threshold
        self.timeout_ms = timeout_ms
        self.half_open_timeout_ms = half_open_timeout_ms

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0
        self._opened_at = 0

        # Distributed state tracking (for coordination across instances)
        self._distributed_state: dict[str, any] = {
            'state': 'closed',
            'opened_at': 0,
        }

    def call(self, func, *args, **kwargs):
        """
        Execute function through circuit breaker
        Raises exception if circuit is open
        """
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit entering half-open state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info("Circuit closed after successful test")
        else:
            # Reset failure count on success
            self._failure_count = 0

    def _on_failure(self):
        """
        Handle failed call
        BUG #2: Opens circuit but doesn't prevent simultaneous test requests
        """
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                # Update distributed state (binary: opened/closed)
                # BUG: No "test request in flight" flag to prevent simultaneous tests
                self._distributed_state['state'] = 'opened'
                self._distributed_state['opened_at'] = self._opened_at
                logger.warning(f"Circuit opened after {self._failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt reset
        BUG #2: Multiple instances check simultaneously and all send test requests
        """
        if self._state != CircuitState.OPEN:
            return False

        elapsed = (time.time() - self._opened_at) * 1000  # Convert to ms
        # BUG: All circuit breakers across instances will attempt reset at same time
        # because they all opened at roughly the same time (synchronized failures)
        return elapsed >= self.timeout_ms

    def force_open(self):
        """Manually open the circuit"""
        self._state = CircuitState.OPEN
        self._opened_at = time.time()

    def force_close(self):
        """Manually close the circuit"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            'state': self._state.value,
            'failure_count': self._failure_count,
            'last_failure_time': self._last_failure_time,
            'opened_at': self._opened_at,
        }

    def is_closed(self) -> bool:
        """Check if circuit is closed (healthy)"""
        return self._state == CircuitState.CLOSED

    def is_open(self) -> bool:
        """Check if circuit is open (failing)"""
        return self._state == CircuitState.OPEN
