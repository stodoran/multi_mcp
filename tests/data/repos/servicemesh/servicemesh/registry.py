"""
Service registry with distributed state management
Handles service registration and state synchronization
"""

import logging
import time

from .endpoints import Endpoint

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Distributed service registry with eventual consistency
    """

    def __init__(self, node_id: str, enable_distributed: bool = True):
        self.node_id = node_id
        self.enable_distributed = enable_distributed
        # Local state: service_name -> {endpoint_key -> (endpoint, timestamp)}
        self._local_state: dict[str, dict[str, tuple]] = {}
        # Remote registries for distributed mode
        self._remote_registries: list[ServiceRegistry] = []
        self._sync_interval = 5.0  # 5 seconds

    def register_service(self, service_name: str, endpoint: Endpoint):
        """Register a service endpoint"""
        if service_name not in self._local_state:
            self._local_state[service_name] = {}

        endpoint_key = f"{endpoint.host}:{endpoint.port}"
        # BUG #1: Using wall-clock timestamp (not vector clocks)
        timestamp = time.time()
        self._local_state[service_name][endpoint_key] = (endpoint, timestamp)

        logger.debug(f"Registered {service_name} at {endpoint_key} with timestamp {timestamp}")

    def deregister_service(self, service_name: str, host: str, port: int):
        """Deregister a service endpoint"""
        if service_name in self._local_state:
            endpoint_key = f"{host}:{port}"
            if endpoint_key in self._local_state[service_name]:
                del self._local_state[service_name][endpoint_key]

    def get_endpoints(self, service_name: str) -> list[Endpoint]:
        """Get all endpoints for a service"""
        if not self.enable_distributed:
            return self._get_local_endpoints(service_name)

        # In distributed mode, merge local + remote state
        merged_state = self._merge_distributed_state(service_name)
        return [endpoint for endpoint, _ in merged_state.values()]

    def _get_local_endpoints(self, service_name: str) -> list[Endpoint]:
        """Get endpoints from local state only"""
        if service_name not in self._local_state:
            return []
        return [endpoint for endpoint, _ in self._local_state[service_name].values()]

    def _merge_distributed_state(self, service_name: str) -> dict[str, tuple]:
        """
        Merge local and remote registry states
        BUG #1: Uses last-write-wins with wall-clock timestamps
        This causes split-brain during network partitions
        """
        merged = {}

        # Start with local state
        if service_name in self._local_state:
            merged = self._local_state[service_name].copy()

        # Merge remote states - BUG: uses max(timestamp1, timestamp2)
        for remote_registry in self._remote_registries:
            remote_state = remote_registry._get_local_state(service_name)
            for endpoint_key, (endpoint, remote_timestamp) in remote_state.items():
                if endpoint_key not in merged:
                    merged[endpoint_key] = (endpoint, remote_timestamp)
                else:
                    local_endpoint, local_timestamp = merged[endpoint_key]
                    # Last-write-wins based on wall-clock time
                    # BUG: No vector clocks, no causality tracking
                    if remote_timestamp > local_timestamp:
                        merged[endpoint_key] = (endpoint, remote_timestamp)

        return merged

    def _get_local_state(self, service_name: str) -> dict[str, tuple]:
        """Get local state for distributed sync"""
        return self._local_state.get(service_name, {})

    def add_remote_registry(self, registry: 'ServiceRegistry'):
        """Add a remote registry for distributed mode"""
        if registry not in self._remote_registries:
            self._remote_registries.append(registry)

    def sync_with_remotes(self):
        """
        Synchronize state with remote registries
        Note: Sync happens but doesn't prevent split-brain
        """
        for remote in self._remote_registries:
            # Pull remote state and merge
            for service_name in remote._local_state:
                remote_state = remote._get_local_state(service_name)
                self._merge_remote_state(service_name, remote_state)

    def _merge_remote_state(self, service_name: str, remote_state: dict[str, tuple]):
        """Merge remote state into local state"""
        if service_name not in self._local_state:
            self._local_state[service_name] = {}

        for endpoint_key, (endpoint, remote_timestamp) in remote_state.items():
            if endpoint_key not in self._local_state[service_name]:
                self._local_state[service_name][endpoint_key] = (endpoint, remote_timestamp)
            else:
                _, local_timestamp = self._local_state[service_name][endpoint_key]
                if remote_timestamp > local_timestamp:
                    self._local_state[service_name][endpoint_key] = (endpoint, remote_timestamp)

    def get_service_count(self, service_name: str) -> int:
        """Get count of registered endpoints"""
        endpoints = self.get_endpoints(service_name)
        return len(endpoints)

    def clear_stale_entries(self, max_age: float = 300.0):
        """Remove entries older than max_age seconds"""
        current_time = time.time()
        for service_name in list(self._local_state.keys()):
            for endpoint_key in list(self._local_state[service_name].keys()):
                _, timestamp = self._local_state[service_name][endpoint_key]
                if current_time - timestamp > max_age:
                    del self._local_state[service_name][endpoint_key]
