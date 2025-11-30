"""Service discovery for finding available services.

This module provides service discovery and health tracking.
"""

import logging
from typing import Any

from .cache import Cache

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """Discovers and tracks service availability."""

    def __init__(self, cache: Cache):
        """Initialize service discovery.

        Args:
            cache: Cache instance for service data
        """
        self._cache = cache
        self._down_services: set[str] = set()

    def find_services(self, service_type: str) -> dict[str, Any] | list:
        """Find services of a given type.

        Args:
            service_type: Type of service to find

        Returns:
            Dictionary of services or empty dict/list on failure
        """
        cache_key = f"discovery:{service_type}"

        cached = self._cache.get(cache_key)
        if cached:
            if isinstance(cached, dict):
                return {
                    k: v for k, v in cached.items()
                    if k not in self._down_services
                }
            return cached

        try:
            services = self._perform_discovery(service_type)

            if not services:
                logger.info(f"No services found for type {service_type}")
                return {}

            self._cache.set(cache_key, services, ttl=5)

            return {
                k: v for k, v in services.items()
                if k not in self._down_services
            }

        except Exception as e:
            logger.error(f"Service discovery failed for {service_type}: {e}")
            return []

    def mark_service_down(self, service_id: str) -> None:
        """Mark a service as down.

        Args:
            service_id: Service identifier
        """
        self._down_services.add(service_id)
        logger.info(f"Marked service {service_id} as down")

    def mark_service_up(self, service_id: str) -> None:
        """Mark a service as up.

        Args:
            service_id: Service identifier
        """
        self._down_services.discard(service_id)
        logger.info(f"Marked service {service_id} as up")

    def get_down_services(self) -> set[str]:
        """Get set of services marked as down.

        Returns:
            Set of service IDs marked as down
        """
        return self._down_services.copy()

    def _perform_discovery(self, service_type: str) -> dict[str, Any]:
        """Perform actual service discovery.

        This is a stub that would query service registry, consul, etc.
        """
        return {
            f"{service_type}-1": {"host": "localhost", "port": 8001},
            f"{service_type}-2": {"host": "localhost", "port": 8002}
        }
