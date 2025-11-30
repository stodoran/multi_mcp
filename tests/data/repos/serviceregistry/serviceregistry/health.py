"""Health checking for service instances.

This module performs health checks on registered services.
"""

import logging
import urllib.request

from .discovery import ServiceDiscovery

logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs health checks on service instances."""

    def __init__(
        self,
        discovery: ServiceDiscovery,
        check_timeout: float = 5.0,
        check_interval: float = 30.0
    ):
        """Initialize health checker.

        Args:
            discovery: Service discovery instance
            check_timeout: Timeout for individual health checks in seconds
            check_interval: Interval between checks in seconds
        """
        self._discovery = discovery
        self._check_timeout = check_timeout
        self._check_interval = check_interval
        self._health_status: dict[str, bool] = {}

    async def check_service_health(
        self,
        service_id: str,
        host: str,
        port: int
    ) -> bool:
        """Check health of a single service.

        Args:
            service_id: Service identifier
            host: Service host
            port: Service port

        Returns:
            True if service is healthy, False otherwise
        """
        health_url = f"http://{host}:{port}/health"

        try:
            response = urllib.request.urlopen(
                health_url,
                timeout=self._check_timeout
            )

            is_healthy = response.getcode() == 200
            self._health_status[service_id] = is_healthy

            if not is_healthy:
                logger.warning(f"Service {service_id} health check failed")
                self._discovery.mark_service_down(service_id)
            else:
                self._discovery.mark_service_up(service_id)

            return is_healthy

        except Exception as e:
            logger.error(f"Health check failed for {service_id}: {e}")
            self._health_status[service_id] = False
            self._discovery.mark_service_down(service_id)
            return False

    async def check_all_services(
        self,
        services: dict[str, dict[str, any]]
    ) -> dict[str, bool]:
        """Check health of all services.

        Args:
            services: Dictionary mapping service IDs to service info

        Returns:
            Dictionary mapping service IDs to health status
        """
        results = {}

        for service_id, info in services.items():
            healthy = await self.check_service_health(
                service_id,
                info['host'],
                info['port']
            )
            results[service_id] = healthy

        return results

    def get_health_status(self, service_id: str) -> bool | None:
        """Get cached health status for a service.

        Args:
            service_id: Service identifier

        Returns:
            True if healthy, False if unhealthy, None if unknown
        """
        return self._health_status.get(service_id)

    def get_all_health_status(self) -> dict[str, bool]:
        """Get health status for all checked services.

        Returns:
            Dictionary mapping service IDs to health status
        """
        return dict(self._health_status)
