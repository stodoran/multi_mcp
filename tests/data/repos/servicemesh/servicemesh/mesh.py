"""
Service mesh client
Main entry point for service-to-service communication
"""

import logging
import time
from collections.abc import Callable
from typing import Any

from .circuit_breaker import CircuitBreaker
from .discovery import ServiceDiscovery
from .endpoints import Endpoint, EndpointManager
from .health_checker import HealthChecker
from .load_balancer import LoadBalancer
from .metrics import MetricsCollector
from .registry import ServiceRegistry
from .retry_policy import RetryConfig, RetryPolicy
from .tracing import DistributedTracing

logger = logging.getLogger(__name__)


class MeshClient:
    """
    Service mesh client with discovery, load balancing, and fault tolerance
    Integrates all mesh components
    """

    def __init__(self, service_name: str, node_id: str = "node-1",
                 enable_distributed: bool = True):
        self.service_name = service_name

        # Initialize components
        self.registry = ServiceRegistry(node_id, enable_distributed)
        self.endpoint_manager = EndpointManager()
        self.discovery = ServiceDiscovery(self.registry)
        self.load_balancer = LoadBalancer(strategy="round_robin")
        self.circuit_breaker = CircuitBreaker()
        self.retry_policy = RetryPolicy()
        self.tracing = DistributedTracing(service_name)
        self.metrics = MetricsCollector()
        self.health_checker = HealthChecker(self.endpoint_manager)

    def call_service(self, target_service: str, operation: str,
                    func: Callable, *args, session_id: str | None = None,
                    **kwargs) -> Any:
        """
        Call another service through the mesh
        Handles discovery, load balancing, retries, circuit breaking
        """
        # Start distributed trace
        span = self.tracing.start_span(f"call.{target_service}.{operation}")
        start_time = time.time()

        try:
            # BUG #1: Client requests endpoint list (may get split-brain results)
            endpoints = self.discovery.get_services(target_service)

            if not endpoints:
                raise Exception(f"No endpoints found for service: {target_service}")

            # Update endpoint manager
            for endpoint in endpoints:
                self.endpoint_manager.add_endpoint(target_service, endpoint)

            # BUG #4: Load balancer selects endpoint (may have hash bias)
            endpoint = self.load_balancer.select_endpoint(endpoints, session_id)

            if not endpoint:
                raise Exception(f"No healthy endpoints for service: {target_service}")

            # Execute with circuit breaker and retry
            # BUG #2: Request fails, triggers retry (may cause thundering herd)
            result = self._execute_with_fault_tolerance(
                target_service, endpoint, func, *args, **kwargs
            )

            # Record success metrics
            duration = time.time() - start_time
            self.metrics.record_request(target_service, f"{endpoint.host}:{endpoint.port}",
                                       200, duration)

            # Finish trace span
            self.tracing.finish_span(span.span_id)
            self.metrics.record_trace_span(span.span_id, duration, self.service_name)

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_request(target_service, "unknown", 500, duration)
            self.tracing.finish_span(span.span_id)
            raise e

    def _execute_with_fault_tolerance(self, service_name: str, endpoint: Endpoint,
                                      func: Callable, *args, **kwargs) -> Any:
        """Execute with circuit breaker and retry policy"""

        def wrapped_call():
            # BUG #2: Circuit breaker call (may open and cause synchronized test requests)
            return self.circuit_breaker.call(func, *args, **kwargs)

        # BUG #2: Execute with retry (no jitter causes synchronized retries)
        return self.retry_policy.execute_with_retry(wrapped_call)

    def register_service(self, host: str, port: int, metadata: dict | None = None):
        """Register this service instance"""
        endpoint = Endpoint(
            host=host,
            port=port,
            service_name=self.service_name,
            metadata=metadata or {}
        )
        self.registry.register_service(self.service_name, endpoint)
        self.endpoint_manager.add_endpoint(self.service_name, endpoint)

    def deregister_service(self, host: str, port: int):
        """Deregister this service instance"""
        self.registry.deregister_service(self.service_name, host, port)

    def start_health_checks(self, target_service: str, interval: float = 5.0):
        """
        Start periodic health checks for a service
        BUG #3: Health checker with fixed timeout (2s < p99 latency)
        """
        # In real implementation, this would run in background thread
        # For now, just demonstrate the integration
        self.health_checker.check_all_endpoints(target_service)

    def get_trace_context(self, span_id: int) -> dict[str, str]:
        """
        Get trace context headers for propagation
        BUG #5: Propagates trace context (span IDs may collide)
        """
        return self.tracing.inject_context(span_id)

    def get_mesh_stats(self) -> dict:
        """Get comprehensive mesh statistics"""
        return {
            'service_name': self.service_name,
            'circuit_breaker': self.circuit_breaker.get_stats(),
            'retry_policy': self.retry_policy.get_stats(),
            'load_balancer': self.load_balancer.get_stats(),
            'discovery': self.discovery.get_cache_stats(),
            'metrics': self.metrics.get_all_metrics(),
        }

    def enable_sticky_sessions(self, enabled: bool = True):
        """Enable sticky session routing"""
        self.load_balancer.enable_sticky(enabled)

    def update_load_balancer_strategy(self, strategy: str):
        """Update load balancing strategy"""
        self.load_balancer.update_strategy(strategy)

    def set_retry_config(self, config: RetryConfig):
        """Update retry configuration"""
        self.retry_policy = RetryPolicy(config)
