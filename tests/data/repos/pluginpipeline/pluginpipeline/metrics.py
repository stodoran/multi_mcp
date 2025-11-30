"""Metrics collection."""
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects metrics from pipeline."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = {}
        return cls._instance

    def increment(self, name: str, labels: dict) -> None:
        """Increment a metric."""
        key = (name, tuple(sorted(labels.items())))

        if key not in self._metrics:
            self._metrics[key] = 0

        self._metrics[key] += 1
