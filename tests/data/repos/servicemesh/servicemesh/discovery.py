"""
Service discovery client
Queries service registry and caches endpoint lists
"""

import logging
import time

from .endpoints import Endpoint
from .registry import ServiceRegistry

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """
    Service discovery with caching and retry logic
    """

    def __init__(self, registry: ServiceRegistry, cache_ttl: int = 30):
        self.registry = registry
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple] = {}  # service_name -> (endpoints, timestamp)
        self._query_count = 0

    def get_services(self, service_name: str, use_cache: bool = True) -> list[Endpoint]:
        """
        Query registry for service endpoints
        BUG #1: Part of split-brain chain - gets divergent endpoint lists
        """
        self._query_count += 1

        if use_cache:
            cached_result = self._get_from_cache(service_name)
            if cached_result is not None:
                logger.debug(f"Cache hit for {service_name}")
                return cached_result

        # Query registry - may return split-brain results
        endpoints = self.registry.get_endpoints(service_name)

        # Update cache
        self._cache[service_name] = (endpoints, time.time())

        logger.info(f"Discovered {len(endpoints)} endpoints for {service_name}")
        return endpoints

    def _get_from_cache(self, service_name: str) -> list[Endpoint] | None:
        """Get endpoints from cache if not expired"""
        if service_name not in self._cache:
            return None

        endpoints, timestamp = self._cache[service_name]
        age = time.time() - timestamp
        if age < self.cache_ttl:
            return endpoints

        # Cache expired
        return None

    def refresh_service(self, service_name: str):
        """
        Force refresh of service endpoint list
        BUG #1: Refresh happens BEFORE circuit breaker state propagates
        """
        logger.debug(f"Refreshing service discovery for {service_name}")
        # Invalidate cache
        if service_name in self._cache:
            del self._cache[service_name]

        # Query registry with fresh data
        return self.get_services(service_name, use_cache=False)

    def refresh_all(self):
        """Refresh all cached services"""
        service_names = list(self._cache.keys())
        for service_name in service_names:
            self.refresh_service(service_name)

    def subscribe_to_updates(self, service_name: str, callback):
        """
        Subscribe to service endpoint updates
        Note: Callback-based updates, not real-time
        """
        # Placeholder for pub/sub pattern
        # In reality, would need change detection
        pass

    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'cached_services': len(self._cache),
            'total_queries': self._query_count,
        }

    def invalidate_cache(self, service_name: str | None = None):
        """Invalidate cache for specific service or all services"""
        if service_name:
            if service_name in self._cache:
                del self._cache[service_name]
        else:
            self._cache.clear()

    def watch_service(self, service_name: str, interval: float = 5.0):
        """
        Watch a service for endpoint changes
        Polls at regular intervals
        """
        # Simplified polling-based watch
        # Real implementation would use event-driven updates
        pass

    def register_endpoint(self, service_name: str, endpoint: Endpoint):
        """Register an endpoint through discovery client"""
        self.registry.register_service(service_name, endpoint)
        # Invalidate cache to force refresh
        self.invalidate_cache(service_name)

    def deregister_endpoint(self, service_name: str, host: str, port: int):
        """Deregister an endpoint"""
        self.registry.deregister_service(service_name, host, port)
        self.invalidate_cache(service_name)
