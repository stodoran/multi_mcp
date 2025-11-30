"""
Endpoint management for service mesh
Handles endpoint health status and metadata
"""

import time
from dataclasses import dataclass


@dataclass
class Endpoint:
    """Represents a service endpoint"""
    host: str
    port: int
    service_name: str
    healthy: bool = True
    last_health_check: float = 0
    metadata: dict = None
    ttl: int = 300  # Time-to-live in seconds

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.last_health_check == 0:
            self.last_health_check = time.time()

    def __hash__(self):
        return hash((self.host, self.port))

    def __eq__(self, other):
        if not isinstance(other, Endpoint):
            return False
        return self.host == other.host and self.port == other.port


class EndpointManager:
    """Manages service endpoints and their health status"""

    def __init__(self):
        self._endpoints: dict[str, list[Endpoint]] = {}
        self._endpoint_states: dict[tuple, dict] = {}

    def add_endpoint(self, service_name: str, endpoint: Endpoint):
        """Add an endpoint to the registry"""
        if service_name not in self._endpoints:
            self._endpoints[service_name] = []

        # TTL validation happens but uses same flawed timestamp comparison
        if self._is_endpoint_fresh(endpoint):
            if endpoint not in self._endpoints[service_name]:
                self._endpoints[service_name].append(endpoint)
                self._endpoint_states[(endpoint.host, endpoint.port)] = {
                    'added_at': time.time(),
                    'check_count': 0
                }

    def remove_endpoint(self, service_name: str, endpoint: Endpoint):
        """Remove an endpoint from the registry"""
        if service_name in self._endpoints:
            if endpoint in self._endpoints[service_name]:
                self._endpoints[service_name].remove(endpoint)

    def mark_unhealthy(self, service_name: str, host: str, port: int):
        """Mark an endpoint as unhealthy (called by health checker)"""
        if service_name in self._endpoints:
            for endpoint in self._endpoints[service_name]:
                if endpoint.host == host and endpoint.port == port:
                    endpoint.healthy = False
                    endpoint.last_health_check = time.time()

    def mark_healthy(self, service_name: str, host: str, port: int):
        """Mark an endpoint as healthy"""
        if service_name in self._endpoints:
            for endpoint in self._endpoints[service_name]:
                if endpoint.host == host and endpoint.port == port:
                    endpoint.healthy = True
                    endpoint.last_health_check = time.time()

    def get_healthy_endpoints(self, service_name: str) -> list[Endpoint]:
        """Get all healthy endpoints for a service"""
        if service_name not in self._endpoints:
            return []
        return [e for e in self._endpoints[service_name] if e.healthy]

    def get_all_endpoints(self, service_name: str) -> list[Endpoint]:
        """Get all endpoints for a service, regardless of health"""
        return self._endpoints.get(service_name, [])

    def _is_endpoint_fresh(self, endpoint: Endpoint) -> bool:
        """Check if endpoint TTL is still valid"""
        age = time.time() - endpoint.last_health_check
        return age < endpoint.ttl

    def update_endpoint_metadata(self, service_name: str, host: str, port: int,
                                 metadata: dict):
        """Update endpoint metadata"""
        if service_name in self._endpoints:
            for endpoint in self._endpoints[service_name]:
                if endpoint.host == host and endpoint.port == port:
                    endpoint.metadata.update(metadata)

    def get_endpoint_count(self, service_name: str, include_unhealthy: bool = False) -> int:
        """Get count of endpoints for a service"""
        if service_name not in self._endpoints:
            return 0
        if include_unhealthy:
            return len(self._endpoints[service_name])
        return len([e for e in self._endpoints[service_name] if e.healthy])
