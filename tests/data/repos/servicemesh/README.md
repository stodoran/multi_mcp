# Repo9: ServiceMesh

**Difficulty:** ⭐⭐⭐⭐⭐ (Advanced)
**Files:** 10
**LOC:** ~1,400
**Bugs:** 5 (2 CRITICAL, 2 HIGH, 1 MEDIUM)

## Overview

A microservices service mesh with service discovery, load balancing, circuit breakers, health checking, and distributed tracing. Implements client-side load balancing with multiple strategies, retry logic with exponential backoff, and coordinated circuit breaker state.

## Architecture

- `mesh.py` (180 LOC) - Main mesh client integrating all components
- `discovery.py` (160 LOC) - Service discovery with caching
- `load_balancer.py` (150 LOC) - Client-side load balancing
- `circuit_breaker.py` (140 LOC) - Circuit breaker pattern
- `health_checker.py` (130 LOC) - Endpoint health probing
- `retry_policy.py` (140 LOC) - Exponential backoff retry
- `tracing.py` (120 LOC) - Distributed tracing
- `metrics.py` (130 LOC) - Metrics collection
- `registry.py` (140 LOC) - Distributed service registry
- `endpoints.py` (110 LOC) - Endpoint management

## Bugs

### Bug #1 (CRITICAL): Split-Brain Service Discovery
**Severity:** CRITICAL
**Files:** `discovery.py:34` → `registry.py:56` → `mesh.py:78` → `load_balancer.py:91` → `endpoints.py:45`

**Description:**
Service discovery uses distributed registry with eventual consistency. When network partition occurs, `registry.py` maintains local state while central registry updates. After partition heals, `discovery.py` merges states using "last-write-wins" with wall-clock timestamps (not vector clocks).

**Root Cause:**
- `registry.py:56` - Uses `max(timestamp1, timestamp2)` for merge (wall-clock based)
- `registry.py:23` - Uses `time.time()` instead of monotonic or vector clock
- `config/mesh.yaml` - `registry_sync_interval: 5000` > `circuit_breaker_timeout: 3000`

**Manifestation:**
Only appears during network partitions when two instances of the same service have divergent endpoint lists. Circuit breaker opens but discovery refresh happens BEFORE state propagates, causing clients to keep trying dead endpoints.

**Detective Path:**
1. Start at `mesh.py:78`: Client requests endpoint list
2. Trace to `discovery.py:34`: Queries registry with `get_services(service_name)`
3. Follow to `registry.py:56`: Merges local + remote state using `max(timestamp1, timestamp2)`
4. Notice wall-clock usage at `registry.py:23`: `time.time()` instead of vector clock
5. Return to `load_balancer.py:91`: Round-robin doesn't check endpoint health freshness

---

### Bug #2 (CRITICAL): Retry Storm from Uncoordinated Exponential Backoff
**Severity:** CRITICAL
**Files:** `retry_policy.py:28` → `circuit_breaker.py:89` → `mesh.py:45` → `endpoints.py:67`

**Description:**
`retry_policy.py` implements exponential backoff: `delay = base * (2 ** attempt)`. However, when service becomes unhealthy and ALL clients start retrying simultaneously (synchronized clocks), they all back off and retry at the same time intervals (1s, 2s, 4s, 8s...). Without jitter, clients remain synchronized indefinitely, creating thundering herd.

**Root Cause:**
- `retry_policy.py:28` - `calculate_delay()` has no jitter
- `retry_policy.py:38-40` - Jitter code commented out with note "Disabled: causes non-deterministic test failures"
- `mesh.py:12` - `ENABLE_JITTER = os.getenv('ENABLE_JITTER', 'false')` defaults to disabled
- `circuit_breaker.py:103` - Test request sent after timeout expires (all instances simultaneously)

**Manifestation:**
Only visible with multiple clients starting at same time. When circuit opens, all clients wait for same timeout, then send test request simultaneously, overwhelming recovering service.

**Decoy Patterns:**
1. Comment at `retry_policy.py:34`: `# TODO: Add jitter to prevent thundering herd` suggests awareness
2. Commented code at `retry_policy.py:38-40` shows the fix but it's disabled
3. Feature flag at `mesh.py:12` exists but defaults to `false`

---

### Bug #3 (HIGH): Health Check Flapping from Probe Timing Mismatch
**Severity:** HIGH
**Files:** `health_checker.py:34` → `endpoints.py:78` → `load_balancer.py:45` → `metrics.py:92`

**Description:**
Health checker probes endpoints every 5 seconds with 2-second timeout. Under load, endpoint response time varies: p50=100ms, p95=1800ms, p99=2500ms. The timeout (2s) is shorter than p99, causing 1% false negatives. When health check fails, load redistributes to remaining endpoints, INCREASING their latency and pushing more endpoints over 2s threshold (cascading failures).

**Root Cause:**
- `health_checker.py:61` - Fixed `DEFAULT_TIMEOUT = 2.0` seconds
- `health_checker.py:56` - Comment says "Adaptive timeout" but uses fixed value
- `metrics.py:89` - Percentile tracking commented out (performance concerns)
- `config/mesh.yaml` - `health_check_timeout: 2000ms` < p99 latency (2500ms)

**Manifestation:**
Only manifests under specific load patterns where p99 latency exceeds timeout. Tests use fast responses, missing the issue.

**Decoy Patterns:**
1. Adaptive timeout comment at `health_checker.py:56` but implementation uses fixed timeout
2. Retry logic at `health_checker.py:72` retries within 2s window (doesn't extend it)
3. Percentile tracking code exists but is disabled

---

### Bug #4 (HIGH): Load Balancer Bias from Sticky Session Hash Collision
**Severity:** HIGH
**Files:** `load_balancer.py:115` → `mesh.py:67` → `endpoints.py:89` → `tracing.py:56`

**Description:**
Load balancer implements sticky sessions using `hash(session_id) % num_endpoints`. For 10 endpoints, some get 15% of traffic while others get 5% (birthday paradox + poor hash distribution). When scaling from 10 to 11 endpoints, old sessions stay on old endpoints, creating 90/10 split.

**Root Cause:**
- `load_balancer.py:115` - Uses simple modulo `hash(session_id) % num_endpoints`, not consistent hashing
- `load_balancer.py:123` - Comment claims "consistent hashing" but implementation is wrong
- `load_balancer.py:145` - Rebalancing disabled when `_session_stickiness_enabled`
- `load_balancer.py:98` - `PYTHONHASHSEED=0` makes hash distribution worse

**Manifestation:**
Only visible with large session counts and endpoint changes. Birthday paradox causes uneven distribution that worsens during scaling.

**Decoy Patterns:**
1. Comment suggests consistent hashing but uses simple modulo
2. Rebalancing logic exists but is disabled by feature flag
3. Hash seeding "for reproducibility" actually makes distribution worse

---

### Bug #5 (MEDIUM): Distributed Tracing Span ID Collision with Mixed Bit-Width
**Severity:** MEDIUM
**Files:** `tracing.py:34` → `mesh.py:123` → `metrics.py:67`

**Description:**
Legacy services use 32-bit span IDs: `random.randint(0, 2**32-1)`. Newer services use 64-bit. When 64-bit span IDs are truncated to 32-bit for storage, collision rate skyrockets. Additionally, span ID generation is seeded with `os.getpid() + int(time.time())`, causing services started in same second with sequential PIDs to generate correlated span IDs.

**Root Cause:**
- `tracing.py:28` - Legacy mode uses 32-bit: `random.randint(0, 2**32 - 1)`
- `tracing.py:34` - New mode uses 64-bit but gets truncated
- `tracing.py:156` - Truncation: `span_id & 0xFFFFFFFF` before sending to metrics
- `tracing.py:12` - Seeding: `random.seed(os.getpid() + int(time.time()))`
- `mesh.py:123` - Propagates as 32-bit hex (8 chars)
- `metrics.py:67` - Database schema: `span_id INT UNSIGNED` (32-bit)

**Manifestation:**
With millions of requests per day across 100 services, birthday paradox causes collisions. Birthday paradox: 50% collision at sqrt(2^32) ≈ 65,536 spans. Production volume: 100 services × 100 req/sec = 36M req/hour >> 65K.

**Decoy Patterns:**
1. Comment at `tracing.py:45`: "UUID4 considered but random.randint is faster"
2. Collision detection at `tracing.py:89` only works within single instance
3. Seed randomization comment claims "high-entropy" but PID+timestamp has low entropy

---

## Configuration Files

### `config/mesh.yaml`
```yaml
registry_sync_interval: 5000  # 5 seconds - BUG: > circuit_breaker_timeout
circuit_breaker_timeout: 3000  # 3 seconds - BUG: < registry_sync_interval
health_check_timeout: 2000     # 2 seconds - BUG: < p99 latency
legacy_compatibility: true     # BUG: Enables 32-bit span IDs
ENABLE_JITTER: false          # BUG: Disabled, causes thundering herd
```

## Testing Challenges

These bugs evade standard testing because:

- **Unit tests** use single registry instance (`ENABLE_DISTRIBUTED_MODE=False`)
- **Small data volumes** can't trigger birthday paradox (need millions of events)
- **Homogeneous environments** miss mixed 32/64-bit issues
- **Fast operations** - mocked infrastructure is instant
- **Fixed seeds** make collisions impossible (`PYTHONHASHSEED=0`, `random.seed(42)`)
- **Short durations** - tests run for seconds, bugs manifest over hours/days
- **Generous timeouts** - test config uses 10s timeout vs 2s in production

## Detection Requirements

- Understanding of distributed consensus and CAP theorem
- Knowledge of clock synchronization (NTP, monotonic vs wall-clock)
- Understanding of circuit breaker patterns and coordination
- Knowledge of load balancing algorithms and hash distribution
- Familiarity with retry storms, jitter, and thundering herds
- Statistical understanding of birthday paradox
- Understanding of bit-width truncation and PID correlation

## Original Buggy config:
```yaml
# Service Mesh Configuration

# Registry settings
registry_sync_interval: 5000  # 5 seconds - BUG: > circuit_breaker_timeout
enable_distributed_mode: true

# Circuit breaker settings
circuit_breaker_timeout: 3000  # 3 seconds - BUG: < registry_sync_interval

# Load balancer
load_balancer_strategy: round_robin
enable_sticky_sessions: true
rebalance_on_scale: false  # BUG: Prevents session rebalancing

# Health checking
health_check_interval: 5000  # 5 seconds
health_check_timeout: 2000   # 2 seconds - BUG: < p99 latency
unhealthy_threshold: 2

# Tracing
legacy_compatibility: true  # BUG: Enables 32-bit span IDs for 30% of services
span_id_column_type: INT   # BUG: Forces 32-bit storage

# Jitter
ENABLE_JITTER: false  # BUG: Disabled, causes thundering herd
```