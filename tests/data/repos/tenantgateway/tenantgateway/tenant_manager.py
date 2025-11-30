"""Tenant management."""
import logging
from typing import Any

logger = logging.getLogger(__name__)

class TenantManager:
    """Manages tenant configurations."""

    def __init__(self):
        self._tenants: dict[str, dict[str, Any]] = {}
        logger.info("Initialized tenant manager")

    def register_tenant(self, tenant_id: str, config: dict[str, Any]) -> None:
        """Register a tenant."""
        self._tenants[tenant_id] = config
        logger.info(f"Registered tenant {tenant_id}")

    def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        """Get tenant configuration."""
        return self._tenants.get(tenant_id)

    def delete_tenant(self, tenant_id: str) -> None:
        """Delete tenant configuration."""
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]

        logger.info(f"Deleted tenant {tenant_id}")
