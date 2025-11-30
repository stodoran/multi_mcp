"""Request router for distributing requests to service instances.

This module routes requests to healthy service instances.
"""

import asyncio
import logging
from typing import Any

from .health import HealthChecker
from .registry import ServiceRegistry

logger = logging.getLogger(__name__)


class Router:
    """Routes requests to healthy service instances."""

    def __init__(
        self,
        registry: ServiceRegistry,
        health_checker: HealthChecker
    ):
        """Initialize router.

        Args:
            registry: Service registry instance
            health_checker: Health checker instance
        """
        self._registry = registry
        self._health_checker = health_checker
        self._instance_cache: dict[str, list[dict[str, Any]]] = {}
        self._cache_initialized = False

    async def route_request(
        self,
        service_type: str,
        request_data: Any
    ) -> dict[str, Any] | None:
        """Route a request to an available service instance.

        Args:
            service_type: Type of service to route to
            request_data: The request data

        Returns:
            Response from service or None if routing failed
        """
        if service_type not in self._instance_cache:
            services = self._registry.list_services()
            instances = [
                s for s in services
                if s.get('metadata', {}).get('type') == service_type
            ]
            self._instance_cache[service_type] = instances
            logger.info(f"Cached {len(instances)} instances for {service_type}")
        else:
            instances = self._instance_cache[service_type]

        if not instances:
            logger.error(f"No instances found for service type {service_type}")
            return None

        for instance in instances:
            service_id = instance['service_id']

            is_healthy = await self._health_checker.check_service_health(
                service_id,
                instance['host'],
                instance['port']
            )

            if is_healthy:
                logger.info(f"Routing request to {service_id}")
                return await self._forward_request(instance, request_data)

        logger.error(f"No healthy instances for {service_type}")
        return None

    async def _forward_request(
        self,
        instance: dict[str, Any],
        request_data: Any
    ) -> dict[str, Any]:
        """Forward request to service instance.

        This is a stub that would make actual HTTP request.
        """
        await asyncio.sleep(0.1)
        return {
            'status': 'success',
            'service_id': instance['service_id'],
            'data': f"Processed by {instance['service_id']}"
        }

    def clear_cache(self) -> None:
        """Clear the instance cache."""
        self._instance_cache.clear()
        logger.info("Cleared instance cache")

    def get_cached_instances(self, service_type: str) -> list[dict[str, Any]]:
        """Get cached instances for a service type.

        Args:
            service_type: Service type

        Returns:
            List of cached instances
        """
        return self._instance_cache.get(service_type, [])
