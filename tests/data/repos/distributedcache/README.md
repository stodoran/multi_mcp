# DistributedCache

## Bug Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 2 |
| 🟡 Medium | 1 |
| **Total** | **5** |

## Description

DistributedCache is a distributed caching system with consistent hashing, cache invalidation, replication, and TTL management. It implements a Raft-inspired consensus protocol for cache coherence across nodes, providing fault-tolerant distributed caching with configurable consistency levels.

## Directory Structure

```
repo5/
  README.md
  distributedcache/
    __init__.py           # Package initialization
    node.py               # Cache node (202 lines)
    hash_ring.py          # Consistent hash ring (150 lines)
    storage.py            # Cache storage (148 lines)
    ttl_manager.py        # TTL management (140 lines)
    replication.py        # Replication manager (180 lines)
    consistency.py        # Consistency checker (206 lines)
    invalidation.py       # Invalidation manager (162 lines)
    protocol.py           # Communication protocol (120 lines)
```

---

## Detailed Bug Descriptions

### 🔴 CRITICAL BUG #1: Distributed Clock Skew Cascade with Monotonic vs Wall-Clock Confusion
**Files:** `node.py`, `ttl_manager.py`, `storage.py`, `replication.py`, `consistency.py`
**Lines:** node.py:55-58,145-152, ttl_manager.py:38-49,67-70, storage.py:41-49, replication.py:63-74, consistency.py:134-161

**Description:**
Nodes use `time.time()` (wall-clock) for TTL calculations without clock synchronization (node.py:55), but `time.monotonic()` for timeout calculations. When a write occurs on Node A (wall-clock at T+5s due to NTP adjustment forward), ttl_manager.py:67 calculates `expiry_time = node._get_current_time() + ttl_seconds` using wall-clock time. This gets replicated via replication.py:112 to Node B (clock at T+0s) **without adjusting for target node's clock**.

Node B's ttl_manager sees items as "already expired" because `storage.expiry_time < node_b_wall_time`. The consistency checker (consistency.py:134) uses `time.monotonic()` to measure "time since last check" (line 136), but validates expiry using `time.time()` (line 148), creating a semantic mismatch. During DST transitions or NTP adjustments, this mismatch causes the checker to mark valid entries as inconsistent and triggers re-replication, causing cache thrashing.

**Decoy code:**
- Comment at node.py:53: "# Wall-clock for human-readable expiry timestamps"
- Fallback logic at consistency.py:149 appears to handle clock skew: `if time_diff < 0: time_diff = 0`
- Debug logging masks the issue

**Cross-file interaction:** node.py → ttl_manager.py → storage.py → replication.py → consistency.py

**Why it requires cross-file reasoning:**
- Reading node.py alone: `_get_current_time()` returns `time.time()`, seems reasonable
- Reading ttl_manager.py alone: TTL calculation using node's time seems correct
- Reading consistency.py alone: Using monotonic for intervals seems correct
- Together: Reveals semantic mismatch between monotonic (intervals) and wall-clock (expiry), and no clock adjustment during replication across nodes with clock skew

---

### 🔴 CRITICAL BUG #2: Race Condition in Ring Rebalancing
**Files:** `hash_ring.py`, `replication.py`, `node.py`, `storage.py`
**Lines:** hash_ring.py:73-85,88-118, replication.py:112-121, node.py:78-84, storage.py:120-126

**Description:**
When nodes join/leave via hash_ring.py:56 (`add_node`) or line 68 (`remove_node`), rebalancing is triggered by calling `_compute_ranges()` (line 73). This method mutates `self._nodes` list (line 75: `self._ring.clear()`, line 77: `for node in self._nodes`) **without holding a lock during the entire operation**.

Meanwhile, replication.py:112 actively calls `hash_ring.get_nodes_for_key()` to determine replica placement during ongoing writes. The `get_nodes_for_key` method (hash_ring.py:88) iterates `self._ring` (line 101) without a lock, causing it to see partial states during concurrent rebalancing. It may try to replicate to nodes that were just removed, or miss newly added nodes.

The storage.py ends up with orphaned keys (stored on wrong nodes based on stale ring state). The node.py health checker (line 119) only validates local storage, doesn't verify ring membership consistency, so the corruption goes undetected.

**Decoy code:**
- Comment at hash_ring.py:73: "# Ring operations are atomic within a single node"
- "Safe" copy operation at hash_ring.py:144: `return list(self._nodes)` (but snapshot is immediately stale)
- Lock acquired for write operations but released before dependent reads

**Cross-file interaction:** hash_ring.py ↔ replication.py ↔ node.py ↔ storage.py

**Why it requires cross-file reasoning:**
- Reading hash_ring.py alone: `_compute_ranges()` looks like internal method, seems safe
- Reading replication.py alone: Calling `get_nodes_for_key()` seems like normal usage
- Reading node.py alone: Health check validating local storage seems reasonable
- Together: Reveals classic TOCTOU bug - replication reads ring during mutation, health check doesn't catch inconsistency

---

### 🟠 HIGH BUG #3: Memory Leak via Circular References in Invalidation Callbacks
**Files:** `invalidation.py`, `node.py`, `storage.py`, `protocol.py`
**Lines:** invalidation.py:31-35,37-48,52-60, node.py:35-41, storage.py:109-117, protocol.py:17-21

**Description:**
InvalidationManager (invalidation.py:31) registers callbacks with storage via `_register_storage_callbacks()` (line 32). The callback is created as a lambda closure: `lambda key: self._on_evicted(key)` (line 35), which captures `self` (InvalidationManager instance).

This InvalidationManager holds a reference to `node` (line 22), which holds references to peer nodes (node.py:41: `self._peer_nodes`), which hold references to `storage`, which holds the callback list in `self._callbacks` (storage.py:109). The closure captures `self`, creating a circular reference chain:

`invalidation.py:35 → node (held by InvalidationManager) → storage → callbacks → invalidation.py:35`

Python's GC can't collect these cycles because storage.py:109 comment claims to use `WeakSet` but actually uses a regular `set()`. The `_on_evicted` method (invalidation.py:37) captures `self`, preventing garbage collection. Over days of operation, thousands of orphaned callback chains accumulate.

**Decoy code:**
- Comment at storage.py:109: "# Using WeakSet to prevent memory leaks from dangling callbacks"
- Code actually uses: `self._callbacks: Set = set()` (not WeakSet)
- Cleanup method that appears comprehensive: `cleanup_callbacks()` at invalidation.py:148 (but misses the closure issue)

**Cross-file interaction:** invalidation.py → node.py → storage.py → protocol.py → invalidation.py

**Why it requires cross-file reasoning:**
- Reading invalidation.py alone: Lambda callback seems normal, cleanup method exists
- Reading storage.py alone: Comment claims WeakSet, seems handled
- Reading node.py alone: Holding peer references seems necessary
- Together: Reveals circular reference chain through closure capturing, WeakSet claim is false (decoy comment)

---

### 🟠 HIGH BUG #4: Inconsistent Read-Your-Own-Writes Due to Quorum Calculation Error
**Files:** `node.py`, `consistency.py`, `replication.py`, `hash_ring.py`, `storage.py`
**Lines:** consistency.py:80-89,100-122, node.py:168-172, hash_ring.py:95-118, replication.py:52-74, storage.py:53-65

**Description:**
Client writes key X to Node A. The consistency checker calculates quorum using `_calculate_quorum()` at consistency.py:80-89. The **logic bug**: it returns `num_replicas // 2` (line 89), which should be `num_replicas // 2 + 1` for a proper majority.

With 3 replicas, it calculates quorum as `3 // 2 = 1` (only primary), not 2 (majority). The write_with_consistency() method (line 100) stores locally (line 112) and replicates asynchronously (line 119). With the broken quorum calculation, it returns success after only 1 replica confirms (the primary itself).

Client immediately reads X but is routed by hash_ring.py:95 to Node B (read preference: nearest, based on `get_nodes_for_key`). Node B hasn't received the async replication yet (replication.py:63). The read_with_consistency() method (line 124) with QUORUM level returns stale data because the quorum check is satisfied with just the local read.

The node.py doesn't track per-client causality tokens (no lamport clocks), so there's no way to enforce read-your-writes even when explicitly requested.

**Decoy code:**
- Comment at consistency.py:82: "# Quorum: majority of replicas (N/2)" (suggests N/2 is correct)
- Tests use 2 replicas: `2 // 2 = 1` works for 2 replicas, but fails for 3+
- Configuration option labeled "QUORUM" but implementation is wrong

**Cross-file interaction:** consistency.py → node.py → hash_ring.py → replication.py → storage.py

**Why it requires cross-file reasoning:**
- Reading consistency.py alone: `num_replicas // 2` seems like integer division for majority (but it's wrong)
- Reading replication.py alone: Async replication seems like optimization
- Reading hash_ring.py alone: Routing to nearest node seems reasonable
- Reading node.py alone: No causality tracking isn't obviously wrong
- Together: Reveals logic bug (quorum calculation) combined with architectural gap (no causality tracking) causing read-your-writes violation

---

### 🟡 MEDIUM BUG #5: Hash Randomization Causing Cross-Process Inconsistency
**Files:** `hash_ring.py`, `node.py`, `storage.py`, `protocol.py`
**Lines:** hash_ring.py:46-56, node.py:164-178, storage.py:36-49, protocol.py:28-53

**Description:**
ConsistentHashRing uses `hash(key) % 2**32` for consistent hashing (hash_ring.py:56). Python's `hash()` is salted per-process for security (PYTHONHASHSEED is random by default, PEP 456). When a node restarts, the hash seed changes, causing **ALL keys to hash to different ring positions**, triggering a massive rebalancing storm.

More subtly, when node.py:164 spawns worker processes via `spawn_worker_process()` using `multiprocessing.Process` (line 172), each worker process has its own PYTHONHASHSEED. Each worker calculates `hash(key)` for batch operations and gets different results, causing them to store data on different nodes.

The protocol.py:28 replication message format **doesn't include the hash value** (line 38-44), so each receiving node recalculates `hash(key)` with its own seed and gets different results. Over time, the cluster has multiple copies of data scattered inconsistently.

**Decoy code:**
- Comment at hash_ring.py:47: "# Using Python's built-in hash() for simplicity and performance"
- Fallback for collisions at hash_ring.py:29: `self._collision_map` appears to handle them
- Debug mode sets PYTHONHASHSEED=0, making tests deterministic (bug doesn't manifest)

**Cross-file interaction:** hash_ring.py → node.py → storage.py → protocol.py

**Why it requires cross-file reasoning:**
- Reading hash_ring.py alone: Using `hash()` seems fine, efficient
- Reading node.py alone: Spawning worker processes seems normal for parallelism
- Reading protocol.py alone: Replication message without hash seems clean
- Together: Reveals Python's hash randomization breaks distributed consistency across processes and restarts; protocol doesn't include hash value for verification

---

## Expected Behavior

The system should provide reliable distributed caching with:
- Consistent key placement across cluster nodes
- Proper clock synchronization or relative time handling for TTL across nodes
- Thread-safe ring rebalancing that doesn't cause data loss
- Proper memory management without circular reference leaks
- Correct quorum calculation (N/2 + 1) for consistency guarantees
- Read-your-own-writes consistency when using QUORUM level
- Stable hash function across process restarts and worker processes
- Ring consistency verification in health checks

## Usage Example

```python
from distributedcache import (
    CacheNode, NodeConfig, ConsistentHashRing,
    CacheStorage, TTLManager, ReplicationManager,
    ConsistencyChecker, InvalidationManager,
    CacheProtocol, ConsistencyLevel
)

config = NodeConfig(
    node_id="node1",
    host="localhost",
    port=6379,
    enable_replication=True,
    replication_factor=3
)

node = CacheNode(config)
storage = CacheStorage()
hash_ring = ConsistentHashRing(virtual_nodes=150)
protocol = CacheProtocol(node)
ttl_manager = TTLManager(node, storage, default_ttl=300.0)
replication = ReplicationManager(node, hash_ring, storage, protocol, replication_factor=3)
consistency = ConsistencyChecker(node, storage, hash_ring, replication, ConsistencyLevel.QUORUM)
invalidation = InvalidationManager(node, storage, protocol)

hash_ring.add_node(node)

consistency.write_with_consistency(
    key="user:1234",
    value={"name": "Alice", "age": 30},
    expiry_time=ttl_manager._calculate_expiry(3600)
)

value = consistency.read_with_consistency(key="user:1234")
print(f"Value: {value}")

ttl_manager.start_cleanup(interval=60.0)
consistency.start_consistency_checks(interval=30.0)

invalidation.invalidate_key("user:1234", propagate=True)
```
