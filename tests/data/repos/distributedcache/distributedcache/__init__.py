"""DistributedCache - A distributed caching system with consistent hashing.

This package implements a distributed caching system with:
- Consistent hashing for key distribution
- Raft consensus protocol for cache coherence
- TTL management and cache invalidation
- Multi-node replication
"""

from .node import CacheNode
from .hash_ring import ConsistentHashRing
from .storage import CacheStorage
from .ttl_manager import TTLManager
from .consistency import ConsistencyChecker
from .replication import ReplicationManager
from .invalidation import InvalidationManager
from .protocol import CacheProtocol

__version__ = "1.0.0"
__all__ = [
    "CacheNode",
    "ConsistentHashRing",
    "CacheStorage",
    "TTLManager",
    "ConsistencyChecker",
    "ReplicationManager",
    "InvalidationManager",
    "CacheProtocol",
]
