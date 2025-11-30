"""
Distributed tracing with span tracking
Handles trace context propagation across services
"""

import logging
import os
import random
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# BUG #5: Seed RNG with PID + timestamp (low entropy for simultaneous starts)
# Initialize RNG with high-entropy seed for uniqueness
random.seed(os.getpid() + int(time.time()))


@dataclass
class Span:
    """Represents a trace span"""
    span_id: int
    trace_id: int
    parent_span_id: int | None = None
    service_name: str = ""
    operation_name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    tags: dict = field(default_factory=dict)


class DistributedTracing:
    """
    Distributed tracing system with span ID generation
    BUG #5: Mixed 32/64-bit span IDs + PID correlation causes collisions
    """

    def __init__(self, service_name: str, legacy_mode: bool = False):
        self.service_name = service_name
        self._legacy_mode = legacy_mode  # BUG: Some services use 32-bit IDs
        self._active_spans: dict[int, Span] = {}
        self._completed_spans: list[Span] = []

    def start_span(self, operation_name: str, parent_span_id: int | None = None,
                  trace_id: int | None = None) -> Span:
        """
        Start a new span
        BUG #5: Generates span IDs that may collide
        """
        span_id = self._generate_span_id()

        # DECOY: Collision detection (only works within single service instance!)
        if span_id in self._active_spans:
            logging.warning(f"Span ID collision detected: {span_id}")
            span_id = self._generate_span_id()  # Regenerate

        if trace_id is None:
            trace_id = self._generate_trace_id()

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            service_name=self.service_name,
            operation_name=operation_name,
        )

        self._active_spans[span_id] = span
        return span

    def _generate_span_id(self) -> int:
        """
        Generate span ID
        BUG #5: Mixed 32/64-bit IDs + birthday paradox causes collisions
        """
        # DECOY: Comment suggests using UUID but claims random.randint is faster
        # Considered using UUID4 but random.randint is faster and 64-bit should be enough

        if self._legacy_mode:
            # Legacy services use 32-bit span IDs
            return random.randint(0, 2**32 - 1)
        else:
            # New services use 64-bit span IDs
            # BUG: But these get truncated to 32-bit for storage/comparison
            return random.randint(0, 2**64 - 1)

    def _generate_trace_id(self) -> int:
        """Generate trace ID (always 128-bit)"""
        return random.randint(0, 2**128 - 1)

    def finish_span(self, span_id: int):
        """Finish a span"""
        if span_id in self._active_spans:
            span = self._active_spans[span_id]
            span.end_time = time.time()
            self._completed_spans.append(span)
            del self._active_spans[span_id]

    def get_span_context(self, span_id: int) -> dict | None:
        """
        Get span context for propagation
        BUG #5: Propagates span_id as 32-bit hex (truncates 64-bit IDs)
        """
        if span_id in self._active_spans:
            span = self._active_spans[span_id]
            # BUG: Formats as 8-char hex (32-bit), truncating 64-bit IDs
            return {
                'trace_id': format(span.trace_id, 'x'),
                'span_id': format(span.span_id & 0xFFFFFFFF, '08x'),  # Truncate to 32-bit
                'parent_span_id': format(span.parent_span_id, 'x') if span.parent_span_id else None,
            }
        return None

    def inject_context(self, span_id: int) -> dict[str, str]:
        """Create HTTP headers with trace context"""
        context = self.get_span_context(span_id)
        if context:
            return {
                'X-Trace-Id': context['trace_id'],
                'X-Span-Id': context['span_id'],  # 32-bit hex string (8 chars)
                'X-Parent-Span-Id': context['parent_span_id'] or '',
            }
        return {}

    def extract_context(self, headers: dict[str, str]) -> dict | None:
        """Extract trace context from HTTP headers"""
        if 'X-Trace-Id' in headers and 'X-Span-Id' in headers:
            return {
                'trace_id': int(headers['X-Trace-Id'], 16),
                'span_id': int(headers['X-Span-Id'], 16),  # Parse as 32-bit
                'parent_span_id': int(headers.get('X-Parent-Span-Id', '0'), 16) if headers.get('X-Parent-Span-Id') else None,
            }
        return None

    def add_span_tag(self, span_id: int, key: str, value: any):
        """Add tag to span"""
        if span_id in self._active_spans:
            self._active_spans[span_id].tags[key] = value

    def get_active_spans(self) -> list[Span]:
        """Get all active spans"""
        return list(self._active_spans.values())

    def get_completed_spans(self) -> list[Span]:
        """Get all completed spans"""
        return self._completed_spans

    def clear_completed_spans(self):
        """Clear completed spans (for memory management)"""
        self._completed_spans.clear()
