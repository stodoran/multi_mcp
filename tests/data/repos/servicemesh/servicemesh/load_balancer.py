"""
Load balancer with multiple strategies
Supports round-robin, random, and sticky session routing
"""

import os
import random

from .endpoints import Endpoint

# Set hash seed for "deterministic routing"
# BUG #4: PYTHONHASHSEED=0 makes hash distribution worse
if 'PYTHONHASHSEED' not in os.environ:
    os.environ['PYTHONHASHSEED'] = '0'


class LoadBalancer:
    """
    Client-side load balancer with multiple strategies
    BUG #4: Sticky sessions use hash(session_id) % N causing bias
    """

    def __init__(self, strategy: str = "round_robin", enable_sticky_sessions: bool = False):
        self.strategy = strategy
        self.enable_sticky_sessions = enable_sticky_sessions
        self._session_stickiness_enabled = enable_sticky_sessions
        self._session_map: dict = {}  # session_id -> endpoint_index
        self._round_robin_index = 0

    def select_endpoint(self, endpoints: list[Endpoint],
                       session_id: str | None = None) -> Endpoint | None:
        """
        Select an endpoint based on configured strategy
        BUG #4: Sticky sessions create uneven distribution
        """
        if not endpoints:
            return None

        # Remove unhealthy endpoints from rotation
        healthy_endpoints = [e for e in endpoints if e.healthy]
        if not healthy_endpoints:
            return None

        # Sticky session routing
        if session_id and self.enable_sticky_sessions:
            return self._select_sticky(healthy_endpoints, session_id)

        # Strategy-based selection
        if self.strategy == "round_robin":
            return self._select_round_robin(healthy_endpoints)
        elif self.strategy == "random":
            return self._select_random(healthy_endpoints)
        elif self.strategy == "least_connections":
            return self._select_least_connections(healthy_endpoints)
        else:
            return self._select_round_robin(healthy_endpoints)

    def _select_sticky(self, endpoints: list[Endpoint], session_id: str) -> Endpoint:
        """
        Sticky session selection using hash-based routing
        BUG #4: hash(session_id) % num_endpoints causes birthday paradox distribution
        """
        num_endpoints = len(endpoints)

        # DECOY: Comment suggests consistent hashing but implementation is simple modulo
        # Using consistent hashing for minimal disruption during rebalancing
        # BUG: This is NOT consistent hashing, just hash(key) % N

        # Calculate hash bucket
        # BUG: Birthday paradox causes collisions, uneven distribution (15% vs 5%)
        hash_value = hash(session_id)
        endpoint_index = hash_value % num_endpoints

        # BUG: When endpoints added/removed, sessions don't rebalance
        # Old sessions stay on old buckets, new sessions use all buckets
        # Creates 90/10 split when scaling from 10 to 11 endpoints

        return endpoints[endpoint_index]

    def _select_round_robin(self, endpoints: list[Endpoint]) -> Endpoint:
        """Round-robin selection"""
        endpoint = endpoints[self._round_robin_index % len(endpoints)]
        self._round_robin_index += 1
        return endpoint

    def _select_random(self, endpoints: list[Endpoint]) -> Endpoint:
        """Random selection"""
        return random.choice(endpoints)

    def _select_least_connections(self, endpoints: list[Endpoint]) -> Endpoint:
        """Least connections selection (simplified)"""
        # In real implementation, would track active connections per endpoint
        # For now, use random as fallback
        return random.choice(endpoints)

    def rebalance_sessions(self):
        """
        Gracefully migrate sessions to new endpoints
        DECOY: This looks like it would fix the bug, but it's disabled!
        """
        if self._session_stickiness_enabled:
            # BUG: Feature flag defeats rebalancing
            return  # Don't rebalance sticky sessions

        # Clear session map to force rehashing
        self._session_map.clear()

    def get_session_distribution(self, endpoints: list[Endpoint],
                                sessions: list[str]) -> dict:
        """
        Get distribution of sessions across endpoints
        Used for monitoring (but doesn't alert on imbalance)
        """
        distribution = dict.fromkeys(range(len(endpoints)), 0)

        for session_id in sessions:
            hash_value = hash(session_id)
            endpoint_index = hash_value % len(endpoints)
            distribution[endpoint_index] += 1

        return distribution

    def update_strategy(self, strategy: str):
        """Update load balancing strategy"""
        self.strategy = strategy

    def enable_sticky(self, enabled: bool = True):
        """Enable or disable sticky sessions"""
        self.enable_sticky_sessions = enabled
        self._session_stickiness_enabled = enabled
        if not enabled:
            self._session_map.clear()

    def get_stats(self) -> dict:
        """Get load balancer statistics"""
        return {
            'strategy': self.strategy,
            'sticky_sessions_enabled': self.enable_sticky_sessions,
            'session_count': len(self._session_map),
            'round_robin_index': self._round_robin_index,
        }
