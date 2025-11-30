"""DistributedCache - A distributed caching system with consistent hashing.

This package implements a distributed caching system with:
- Consistent hashing for key distribution
- Raft consensus protocol for cache coherence
- TTL management and cache invalidation
- Multi-node replication
"""

from .consistency import ConsistencyChecker
from .hash_ring import ConsistentHashRing
from .invalidation import InvalidationManager
from .node import CacheNode
from .protocol import CacheProtocol
from .replication import ReplicationManager
from .storage import CacheStorage
from .ttl_manager import TTLManager

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
