# MultiTenantGateway

## Bug Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 2 |
| 🟡 Medium | 1 |
| **Total** | **5** |

## Description

MultiTenantGateway is an API gateway with tenant isolation, rate limiting, request routing, authentication, and quota management. Supports dynamic tenant configuration and multi-level rate limits (per-tenant, per-endpoint, global) with circuit breaker pattern for fault tolerance.

## Directory Structure

```
repo8/
  README.md
  tenantgateway/
    __init__.py           # Package initialization
    gateway.py            # Main API gateway (39 lines)
    tenant_manager.py     # Tenant management (27 lines)
    auth.py               # Authentication (39 lines)
    rate_limiter.py       # Rate limiting (32 lines)
    router.py             # Request routing (42 lines)
    quota_tracker.py      # Quota tracking (21 lines)
    circuit_breaker.py    # Circuit breaker (46 lines)
    middleware.py         # Middleware chain (36 lines)
    metrics_collector.py  # Gateway metrics (27 lines)
    config_sync.py        # Config synchronization (21 lines)
```

---

## Detailed Bug Descriptions

### 🔴 CRITICAL BUG #1: Tenant Isolation Breach via Shared Cache Key
**Files:** `gateway.py`, `auth.py`, `tenant_manager.py`, `quota_tracker.py`, `rate_limiter.py`
**Lines:** gateway.py:14-22, auth.py:21-38, tenant_manager.py:13-24, quota_tracker.py:13-21, rate_limiter.py:17-32

**Description:**
AuthenticationManager caches tokens using hash (auth.py:25): `token_hash = hash(token) % 10000`. The hash space is **only 10,000 buckets** for potentially millions of tokens, making collisions likely (birthday paradox).

**Attack scenario:**
1. Tenant A authenticates with token_A, hash = 5432
2. Cache stores: `cache["token:5432"] = {tenant_id: "A", ...}` (auth.py:34)
3. Attacker (Tenant B) tries tokens until finding token_B where `hash(token_B) % 10000 = 5432`
4. Gateway.handle_request() retrieves from cache (gateway.py:17)
5. Tenant B gets cache hit with `tenant_id = "A"`
6. Tenant B now operates as Tenant A, accessing their data

QuotaTracker charges Tenant A for Tenant B's requests (quota_tracker.py:17). RateLimiter thinks Tenant A is over quota and blocks them (rate_limiter.py:26).

**Decoy code:**
- Comment at auth.py:24: "# Hash token for privacy and cache key normalization"
- Cache TTL at auth.py:34: `ttl=300` suggests freshness
- Validation that's circular: `if cached_tenant_id != expected` (but expected derived from cached value)

**Cross-file interaction:** gateway.py → auth.py → tenant_manager.py → quota_tracker.py → rate_limiter.py

**Why it requires cross-file reasoning:**
- Reading auth.py alone: Hashing for cache keys seems normal
- Reading gateway.py alone: Using cached auth seems efficient
- Reading quota_tracker.py alone: Charging based on tenant_id seems correct
- Together: Reveals small hash space (10K) causes collisions, cache poisoning enables tenant impersonation

---

### 🔴 CRITICAL BUG #2: Distributed Rate Limit Race Causing Quota Overflow
**Files:** `rate_limiter.py`, `quota_tracker.py`, `config_sync.py`, `gateway.py`
**Lines:** rate_limiter.py:17-32, quota_tracker.py:13-21, config_sync.py:13-21, gateway.py:14-22

**Description:**
Multiple gateway instances share quota via Redis. RateLimiter does **read-modify-write without atomicity** (rate_limiter.py:21-24):

```python
count = await self._redis.get(key) or 0  # Read
new_count = count + 1                     # Modify
await self._redis.set(key, new_count)     # Write
```

**Race sequence (2 gateways, limit=100):**
1. Gateway 1: reads count=99
2. Gateway 2: reads count=99 (before Gateway 1 writes)
3. Gateway 1: writes count=100
4. Gateway 2: writes count=100 (overwrites!)
5. Actual requests: 2, but counter shows: 1 increment

Tenant gets 200 requests instead of limit=100. QuotaTracker eventually detects overflow (quota_tracker.py:20), but damage done. ConfigSync tries to compensate (config_sync.py:17), making it worse.

**Decoy code:**
- Comment at rate_limiter.py:20: "# Redis ensures distributed consistency"
- Retry logic doesn't fix race: `for _ in range(3): ...`
- "Atomic" operation that isn't: three separate Redis calls

**Cross-file interaction:** rate_limiter.py ↔ quota_tracker.py ↔ config_sync.py ↔ gateway.py

**Why it requires cross-file reasoning:**
- Reading rate_limiter.py alone: Using Redis suggests distributed coordination
- Reading quota_tracker.py alone: Tracking usage seems straightforward
- Reading config_sync.py alone: Sync logic seems helpful
- Together: Reveals read-modify-write lacks atomicity (should use INCR), runs on multiple instances

---

### 🟠 HIGH BUG #3: Circuit Breaker State Inconsistency Across Instances
**Files:** `circuit_breaker.py`, `router.py`, `config_sync.py`, `gateway.py`
**Lines:** circuit_breaker.py:25-50, router.py:19-38, config_sync.py:15-18, gateway.py:14-22

**Description:**
When backend fails 5 times, CircuitBreaker opens on Gateway 1 (circuit_breaker.py:45: `self._state = CircuitState.OPEN`). State stored in **local memory** (line 27). Gateway 2 doesn't know (different process, different memory).

ConfigSync propagates state via Redis pub/sub (config_sync.py:16: `publish()`), but pub/sub is **at-most-once delivery** — messages can be lost if subscriber temporarily disconnected.

**Sequence:**
1. Gateway 1: backend fails 5 times, opens circuit (circuit_breaker.py:45)
2. ConfigSync publishes event (config_sync.py:16)
3. Gateway 2: subscriber disconnected during network blip (message lost)
4. Router on Gateway 2 checks: `circuit.is_closed()` (router.py:29) returns True (stale local state)
5. Gateway 2 continues sending traffic, making outage worse

**Decoy code:**
- Comment at circuit_breaker.py:25: "# Circuit state synced via Redis pub/sub for distributed coordination"
- Heartbeat mechanism checks connection but doesn't guarantee message delivery
- Fallback to local state defeats distributed consistency

**Cross-file interaction:** circuit_breaker.py ↔ router.py ↔ config_sync.py ↔ gateway.py

**Why it requires cross-file reasoning:**
- Reading circuit_breaker.py alone: Local state with sync comment suggests it's handled
- Reading config_sync.py alone: Pub/sub seems like distributed messaging
- Reading router.py alone: Checking circuit state seems correct
- Together: Reveals pub/sub is at-most-once (lossy), local state isn't updated on message loss

---

### 🟠 HIGH BUG #4: Middleware Chain Short-Circuit Bypass
**Files:** `middleware.py`, `gateway.py`, `auth.py`, `router.py`
**Lines:** middleware.py:18-37, gateway.py:14-22, auth.py:29-30, router.py:25-38

**Description:**
Middleware chain: auth → rate limit → routing. If `auth.py` raises `AuthenticationError` (line 30), middleware catches exception (middleware.py:24), calls error handler (line 26).

**The bug**: In `finally` block (line 28), middleware **still calls next middleware** even after exception. Rate limiter sees unauthenticated request, doesn't have tenant info, uses **default bucket**.

**Sequence:**
1. Auth raises AuthenticationError (auth.py:30)
2. Middleware catches, sets response=401 (middleware.py:26)
3. `finally` block (line 28) still executes next middleware
4. Rate limiter has no tenant_id, uses default (rate_limiter.py:27: `"default_anonymous": 10000`)
5. Attacker bypasses tenant limits by sending invalid auth

**Decoy code:**
- Comment at middleware.py:22: "# Error handler short-circuits middleware chain"
- Try/except structure looks correct
- Default bucket labeled misleadingly: config says "10" but actual value is 10,000

**Cross-file interaction:** middleware.py → gateway.py → auth.py → router.py

**Why it requires cross-file reasoning:**
- Reading middleware.py alone: `finally` block seems like cleanup
- Reading auth.py alone: Raising exception seems correct
- Reading rate_limiter.py alone: Default bucket seems reasonable
- Together: Reveals `finally` executes next middleware despite exception, default bucket has wrong value

---

### 🟡 MEDIUM BUG #5: Metrics Cardinality Explosion via Error-Path Request IDs
**Files:** `metrics_collector.py`, `gateway.py`, `tenant_manager.py`, `router.py`
**Lines:** metrics_collector.py:13-27, gateway.py:14-22, tenant_manager.py:13-24, router.py:24-38

**Description:**
Metrics labeled with `{tenant_id, endpoint, method}` for normal requests. Cardinality: 100 tenants × 50 endpoints × 5 methods = 25,000 time series (acceptable).

However, **error-path adds `request_id` label** (gateway.py:18, metrics_collector.py:18-21):
```python
if status >= 400 and request_id:
    labels = (tenant_id, endpoint, method, request_id)
```

Request IDs are UUIDs (router.py:27: `uuid.uuid4()`), unique per request. Over months:
- Normal requests: 25,000 time series (bounded)
- Error requests: 100 × 50 × 5 × **1M unique request_ids** = 25 **billion** time series (unbounded)

Router retry logic (router.py:29) generates new request_id each retry, multiplying time series.

**Decoy code:**
- Comment at metrics_collector.py:17: "# Add request_id for error requests to aid debugging"
- Cardinality limit at metrics_collector.py:24 logs warning but doesn't stop growth
- Cleanup cron exists but is disabled in config

**Cross-file interaction:** metrics_collector.py → gateway.py → tenant_manager.py → router.py

**Why it requires cross-file reasoning:**
- Reading metrics_collector.py alone: Adding request_id for errors seems helpful
- Reading gateway.py alone: Recording errors with details seems thorough
- Reading router.py alone: Generating request_ids seems standard
- Together: Reveals error path adds unbounded dimension (request_id), retry multiplies cardinality

---

## Expected Behavior

The system should provide secure multi-tenant API gateway with:
- Proper cache key construction that avoids tenant isolation breaches (use full token, not hash)
- Atomic distributed counter operations (Redis INCR, not read-modify-write)
- Reliable circuit breaker state propagation (Redis key with polling, not pub/sub)
- Correct middleware exception handling (stop chain after error, not continue in finally)
- Bounded metrics cardinality (error-path metrics without high-cardinality labels like request_id)
- Health checks that verify distributed state consistency

## Usage Example

```python
import asyncio
from tenantgateway import (
    APIGateway, TenantManager, AuthenticationManager,
    RateLimiter, RequestRouter, CircuitBreaker,
    MiddlewareChain, GatewayMetrics
)

async def main():
    cache = {}  # Mock cache
    redis = {}  # Mock Redis

    tenant_mgr = TenantManager()
    tenant_mgr.register_tenant("tenant1", {"tier": "premium"})

    auth = AuthenticationManager(cache)
    rate_limiter = RateLimiter(redis, {"tenant1": 1000, "default_anonymous": 10})
    circuit_breaker = CircuitBreaker(None)
    router = RequestRouter(circuit_breaker)
    metrics = GatewayMetrics()

    gateway = APIGateway({"host": "0.0.0.0", "port": 8080})

    middleware = MiddlewareChain()
    gateway.set_middleware(middleware)
    gateway.set_router(router)

    request = {
        "method": "GET",
        "path": "/api/users",
        "headers": {"Authorization": "Bearer token123"}
    }

    response = await gateway.handle_request(request)
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```
