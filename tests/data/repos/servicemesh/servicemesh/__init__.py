"""
ServiceMesh - Microservices service discovery and load balancing
"""

__version__ = "2.1.0"

from .mesh import MeshClient
from .discovery import ServiceDiscovery
from .load_balancer import LoadBalancer
from .circuit_breaker import CircuitBreaker
from .health_checker import HealthChecker
from .retry_policy import RetryPolicy
from .tracing import DistributedTracing
from .metrics import MetricsCollector
from .registry import ServiceRegistry
from .endpoints import EndpointManager

__all__ = [
    "MeshClient",
    "ServiceDiscovery",
    "LoadBalancer",
    "CircuitBreaker",
    "HealthChecker",
    "RetryPolicy",
    "DistributedTracing",
    "MetricsCollector",
    "ServiceRegistry",
    "EndpointManager",
]
