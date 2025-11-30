"""Service registry for tracking microservice instances.

This module maintains a registry of available services and their metadata.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from .auth import TokenManager
from .cache import Cache

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for tracking service instances and metadata."""

    def __init__(
        self,
        cache: Cache,
        token_manager: TokenManager,
        persistence_path: str | None = None
    ):
        """Initialize service registry.

        Args:
            cache: Cache instance for service metadata
            token_manager: Token manager for auth
            persistence_path: Optional path to persist service list
        """
        self._services: dict[str, dict[str, Any]] = {}
        self._cache = cache
        self._token_manager = token_manager
        self._persistence_path = persistence_path
        self._last_update = 0.0

        if persistence_path and Path(persistence_path).exists():
            self._load_from_file()

    def register_service(
        self,
        service_id: str,
        host: str,
        port: int,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Register a new service instance.

        Args:
            service_id: Unique service identifier
            host: Service host
            port: Service port
            metadata: Optional service metadata
        """
        service_info = {
            'service_id': service_id,
            'host': host,
            'port': port,
            'metadata': metadata or {},
            'registered_at': time.time()
        }

        token = self._token_manager.get_token(service_id)
        if token:
            service_info['auth_token'] = token

        self._last_update = time.time()
        self._services[service_id] = service_info
        self._cache.invalidate(f"service:{service_id}")

        logger.info(f"Registered service {service_id} at {host}:{port}")

        if self._persistence_path:
            self._save_to_file()

    def get_service(self, service_id: str) -> dict[str, Any] | None:
        """Get service information.

        Args:
            service_id: Service identifier

        Returns:
            Service information or None if not found
        """
        cache_key = f"service:{service_id}"

        cached = self._cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {service_id}")
            return cached

        service_info = self._services.get(service_id)
        if service_info:
            self._cache.set(cache_key, service_info, ttl=300)

        return service_info

    def deregister_service(self, service_id: str) -> bool:
        """Deregister a service.

        Args:
            service_id: Service identifier

        Returns:
            True if service was deregistered, False if not found
        """
        if service_id not in self._services:
            return False

        self._last_update = time.time()
        del self._services[service_id]
        self._cache.invalidate(f"service:{service_id}")

        if self._persistence_path:
            self._save_to_file()

        logger.info(f"Deregistered service {service_id}")
        return True

    def reload_from_file(self) -> None:
        """Reload service list from persistence file."""
        if not self._persistence_path:
            return

        self._load_from_file()
        logger.info("Reloaded services from file")

    def _load_from_file(self) -> None:
        """Load services from persistence file."""
        try:
            with open(self._persistence_path) as f:
                data = json.load(f)
                self._services = data.get('services', {})
                self._last_update = time.time()
                logger.info(f"Loaded {len(self._services)} services from file")
        except Exception as e:
            logger.error(f"Failed to load services from file: {e}")

    def _save_to_file(self) -> None:
        """Save services to persistence file."""
        if not self._persistence_path:
            return

        try:
            with open(self._persistence_path, 'w') as f:
                json.dump({'services': self._services}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save services to file: {e}")

    def list_services(self) -> list[dict[str, Any]]:
        """List all registered services.

        Returns:
            List of service information dictionaries
        """
        return list(self._services.values())

    def get_service_count(self) -> int:
        """Get count of registered services."""
        return len(self._services)
