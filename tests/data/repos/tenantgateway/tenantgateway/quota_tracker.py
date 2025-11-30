"""Quota tracking."""
import logging

logger = logging.getLogger(__name__)

class QuotaTracker:
    """Tracks API quotas."""

    def __init__(self, config_sync: Any):
        self._config_sync = config_sync
        self._quotas = {}
        logger.info("Initialized quota tracker")

    def track_usage(self, tenant_id: str, amount: int = 1) -> None:
        """Track quota usage."""
        if tenant_id not in self._quotas:
            self._quotas[tenant_id] = 0

        self._quotas[tenant_id] += amount

    def check_quota(self, tenant_id: str, limit: int) -> bool:
        """Check if within quota."""
        usage = self._quotas.get(tenant_id, 0)
        return usage <= limit
