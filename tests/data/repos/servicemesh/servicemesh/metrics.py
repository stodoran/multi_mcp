"""
Metrics collection and aggregation
Tracks service mesh performance metrics
"""

import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates metrics
    Used by health checker, tracing, circuit breaker
    """

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)

    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict] = None):
        """Increment a counter metric"""
        key = self._make_key(name, tags)
        self._counters[key] += value

    def set_gauge(self, name: str, value: float, tags: Optional[Dict] = None):
        """Set a gauge metric"""
        key = self._make_key(name, tags)
        self._gauges[key] = value

    def record_histogram(self, name: str, value: float, tags: Optional[Dict] = None):
        """Record a histogram value"""
        key = self._make_key(name, tags)
        self._histograms[key].append(value)

    def record_timer(self, name: str, duration: float, tags: Optional[Dict] = None):
        """Record a timing measurement"""
        key = self._make_key(name, tags)
        self._timers[key].append(duration)

    def _make_key(self, name: str, tags: Optional[Dict]) -> str:
        """Create metric key from name and tags"""
        if not tags:
            return name
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"

    def get_counter(self, name: str, tags: Optional[Dict] = None) -> float:
        """Get counter value"""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, tags: Optional[Dict] = None) -> Optional[float]:
        """Get gauge value"""
        key = self._make_key(name, tags)
        return self._gauges.get(key)

    def get_histogram_stats(self, name: str, tags: Optional[Dict] = None) -> Dict:
        """
        Get histogram statistics
        BUG #3: Aggregated metrics hide percentile distributions
        BUG #5: Tracks span IDs but stored as 32-bit INT in database
        """
        key = self._make_key(name, tags)
        values = self._histograms.get(key, [])

        if not values:
            return {'count': 0}

        # BUG #3: Returns mean/min/max but not p95/p99 percentiles
        # Percentile tracking would reveal health check timeout issues
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
            # BUG #3: Percentiles commented out (performance concerns)
            # 'p50': self._percentile(values, 50),
            # 'p95': self._percentile(values, 95),
            # 'p99': self._percentile(values, 99),
        }

    def get_timer_stats(self, name: str, tags: Optional[Dict] = None) -> Dict:
        """Get timer statistics"""
        key = self._make_key(name, tags)
        values = self._timers.get(key, [])

        if not values:
            return {'count': 0}

        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
        }

    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile (not used due to performance concerns)"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def record_trace_span(self, span_id: int, duration: float, service_name: str):
        """
        Record trace span metrics
        BUG #5: Stores span_id as 32-bit INT causing truncation
        """
        # In real implementation, this would write to database:
        # INSERT INTO spans (span_id, duration, service) VALUES (?, ?, ?)
        # WHERE span_id column is defined as: span_id INT UNSIGNED (32-bit)

        # BUG #5: Truncate 64-bit span_id to 32-bit for storage
        span_id_32bit = span_id & 0xFFFFFFFF

        # Record duration metric
        self.record_timer('trace.span.duration', duration, {
            'service': service_name,
            'span_id': str(span_id_32bit),
        })

    def record_health_check(self, service_name: str, endpoint: str, success: bool,
                           duration: float):
        """
        Record health check result
        BUG #3: Tracks results but not latency percentiles
        """
        self.increment_counter('health_check.total', tags={'service': service_name})
        if success:
            self.increment_counter('health_check.success', tags={'service': service_name})
        else:
            self.increment_counter('health_check.failure', tags={'service': service_name})

        # Record duration
        self.record_timer('health_check.duration', duration, {'service': service_name})

    def record_request(self, service_name: str, endpoint_id: str, status_code: int,
                      duration: float):
        """
        Record request metrics
        BUG #4: Aggregates across all endpoints, hiding load imbalance
        """
        self.increment_counter('requests.total', tags={'service': service_name})
        self.increment_counter('requests.by_endpoint', tags={
            'service': service_name,
            'endpoint': endpoint_id
        })

        # BUG #4: Per-endpoint counts tracked but no alerting on distribution
        self.record_timer('request.duration', duration, {'service': service_name})

    def get_all_metrics(self) -> Dict:
        """Get all collected metrics"""
        return {
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'histograms': {k: self.get_histogram_stats(k.split('[')[0])
                          for k in self._histograms.keys()},
            'timers': {k: self.get_timer_stats(k.split('[')[0])
                      for k in self._timers.keys()},
        }

    def reset_metrics(self):
        """Reset all metrics"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()
