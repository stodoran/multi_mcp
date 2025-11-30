"""
Retry policy with exponential backoff
Handles request retry logic with configurable strategies
"""

import logging
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Feature flag for jitter (defaults to disabled)
ENABLE_JITTER = os.getenv('ENABLE_JITTER', 'false').lower() == 'true'


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    base_delay_ms: int = 1000
    max_attempts: int = 5
    timeout_ms: int = 30000
    exponential_base: int = 2
    jitter_enabled: bool = False


class RetryPolicy:
    """
    Implements exponential backoff retry policy
    BUG #2: No jitter, causing synchronized retries and thundering herd
    """

    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()
        self._attempt_count = 0
        self._last_attempt_time = 0

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate retry delay using exponential backoff
        BUG #2: No jitter added to break synchronization
        """
        # Exponential backoff: delay = base * (2 ** attempt)
        delay_ms = self.config.base_delay_ms * (self.config.exponential_base ** attempt)

        # Cap at max reasonable value
        delay_ms = min(delay_ms, self.config.timeout_ms)

        # TODO: Add jitter to prevent thundering herd
        # BUG: This is the critical missing piece!
        # Without jitter, all clients retry at same intervals (1s, 2s, 4s, 8s, 16s)

        # DECOY: Commented-out code that would fix the bug
        # jitter = random.uniform(0, 0.1 * delay_ms)
        # delay_ms = delay_ms + jitter
        # return delay_ms / 1000.0
        # Disabled: causes non-deterministic test failures

        # DECOY: Feature flag check (but defaults to False)
        if ENABLE_JITTER or self.config.jitter_enabled:
            jitter = random.uniform(0, 0.1 * delay_ms)
            delay_ms = delay_ms + jitter

        return delay_ms / 1000.0  # Convert to seconds

    def execute_with_retry(self, func: Callable, *args, **kwargs):
        """
        Execute a function with retry logic
        Returns result or raises last exception
        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                self._attempt_count = attempt
                self._last_attempt_time = time.time()

                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Request succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_attempts} attempts failed")

        raise last_exception

    def should_retry(self, exception: Exception) -> bool:
        """Determine if an exception is retryable"""
        # Retry on network errors, timeouts, 5xx errors
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            OSError,
        )
        return isinstance(exception, retryable_exceptions)

    def get_attempt_count(self) -> int:
        """Get current attempt count"""
        return self._attempt_count

    def reset(self):
        """Reset retry state"""
        self._attempt_count = 0
        self._last_attempt_time = 0

    def get_stats(self) -> dict:
        """Get retry statistics"""
        return {
            'total_attempts': self._attempt_count,
            'last_attempt_time': self._last_attempt_time,
            'max_attempts': self.config.max_attempts,
            'jitter_enabled': self.config.jitter_enabled or ENABLE_JITTER,
        }

    def with_jitter(self, enabled: bool = True):
        """Enable or disable jitter (chainable)"""
        self.config.jitter_enabled = enabled
        return self
