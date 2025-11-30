"""
Health checker for monitoring endpoint availability
Probes endpoints at regular intervals
"""

import logging
import time

from .endpoints import Endpoint, EndpointManager

logger = logging.getLogger(__name__)

# Default timeout - BUG #3: Too short for p99 latency
DEFAULT_TIMEOUT = 2.0  # 2 seconds


class HealthChecker:
    """
    Periodic health checker for service endpoints
    BUG #3: Fixed timeout causes false negatives under load
    """

    def __init__(self, endpoint_manager: EndpointManager,
                 interval: float = 5.0,
                 timeout: float = DEFAULT_TIMEOUT,
                 unhealthy_threshold: int = 2):
        self.endpoint_manager = endpoint_manager
        self.interval = interval
        self.timeout = timeout
        self.unhealthy_threshold = unhealthy_threshold

        self._check_history: dict[str, list] = {}
        self._detailed_metrics_enabled = False  # BUG #3: Disabled by default

    def probe_endpoint(self, service_name: str, endpoint: Endpoint) -> bool:
        """
        Probe a single endpoint
        BUG #3: Timeout (2s) < p99 latency (2.5s) causes false negatives
        """
        endpoint_key = f"{endpoint.host}:{endpoint.port}"

        try:
            # Simulate HTTP health check with timeout
            start_time = time.time()

            # In real implementation, this would be an HTTP GET /health
            # For simulation, we'll add artificial latency
            response = self._make_health_request(endpoint)

            duration = time.time() - start_time

            # BUG #3: Timeout check - under load, p99 > 2.5s
            if duration > self.timeout:
                logger.warning(f"Health check timeout for {endpoint_key}: {duration:.2f}s")
                self._record_failure(service_name, endpoint)
                return False

            # Track latency if detailed metrics enabled
            # BUG #3: This is disabled in production for "performance"
            # if self._detailed_metrics_enabled:
            #     self._latency_histogram.observe(duration)

            self._record_success(service_name, endpoint)
            return True

        except Exception as e:
            logger.error(f"Health check failed for {endpoint_key}: {e}")
            self._record_failure(service_name, endpoint)
            return False

    def _make_health_request(self, endpoint: Endpoint):
        """Make health check request (placeholder)"""
        # In real implementation: requests.get(f"http://{endpoint.host}:{endpoint.port}/health", timeout=self.timeout)
        # Simulate variable latency: p50=100ms, p95=1800ms, p99=2500ms
        import random
        latency = random.gauss(0.1, 0.5)  # Mean 100ms, but can spike
        time.sleep(max(0, latency))
        return {"status": "healthy"}

    def _record_success(self, service_name: str, endpoint: Endpoint):
        """Record successful health check"""
        endpoint_key = f"{endpoint.host}:{endpoint.port}"
        if endpoint_key not in self._check_history:
            self._check_history[endpoint_key] = []

        self._check_history[endpoint_key].append({
            'timestamp': time.time(),
            'success': True
        })

        # Mark endpoint healthy
        self.endpoint_manager.mark_healthy(service_name, endpoint.host, endpoint.port)

    def _record_failure(self, service_name: str, endpoint: Endpoint):
        """
        Record failed health check
        BUG #3: Marks unhealthy, causing load redistribution and cascading failures
        """
        endpoint_key = f"{endpoint.host}:{endpoint.port}"
        if endpoint_key not in self._check_history:
            self._check_history[endpoint_key] = []

        self._check_history[endpoint_key].append({
            'timestamp': time.time(),
            'success': False
        })

        # Check if we've hit unhealthy threshold
        recent_failures = self._count_recent_failures(endpoint_key)
        if recent_failures >= self.unhealthy_threshold:
            logger.warning(f"Marking {endpoint_key} as unhealthy after {recent_failures} failures")
            self.endpoint_manager.mark_unhealthy(service_name, endpoint.host, endpoint.port)

    def _count_recent_failures(self, endpoint_key: str) -> int:
        """Count recent consecutive failures"""
        if endpoint_key not in self._check_history:
            return 0

        history = self._check_history[endpoint_key]
        consecutive_failures = 0
        for check in reversed(history[-10:]):  # Look at last 10 checks
            if not check['success']:
                consecutive_failures += 1
            else:
                break
        return consecutive_failures

    def check_all_endpoints(self, service_name: str):
        """
        Check all endpoints for a service
        Called periodically by health check loop
        """
        endpoints = self.endpoint_manager.get_all_endpoints(service_name)
        logger.debug(f"Checking health of {len(endpoints)} endpoints for {service_name}")

        for endpoint in endpoints:
            self.probe_endpoint(service_name, endpoint)

    def get_health_stats(self, service_name: str) -> dict:
        """Get health check statistics"""
        endpoints = self.endpoint_manager.get_all_endpoints(service_name)
        healthy_count = len([e for e in endpoints if e.healthy])

        return {
            'total_endpoints': len(endpoints),
            'healthy_endpoints': healthy_count,
            'unhealthy_endpoints': len(endpoints) - healthy_count,
        }

    def enable_detailed_metrics(self, enabled: bool = True):
        """Enable detailed latency tracking"""
        # BUG #3: Even if enabled, percentile tracking isn't implemented properly
        self._detailed_metrics_enabled = enabled
