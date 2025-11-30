"""Metrics collection for gateway."""
import logging

logger = logging.getLogger(__name__)

class GatewayMetrics:
    """Collects gateway metrics."""

    def __init__(self):
        self._metrics: dict[tuple, int] = {}
        logger.info("Initialized gateway metrics")

    def record_request(self, tenant_id: str, endpoint: str, method: str, request_id: str = None, status: int = 200) -> None:
        """Record a request.

        Add request_id for error requests to aid debugging.
        """
        if status >= 400 and request_id:
            labels = (tenant_id, endpoint, method, request_id)
        else:
            labels = (tenant_id, endpoint, method)

        if labels not in self._metrics:
            self._metrics[labels] = 0

        self._metrics[labels] += 1
