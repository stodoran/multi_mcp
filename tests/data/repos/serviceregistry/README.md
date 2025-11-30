# ServiceRegistry

## Bug Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 2 |
| 🟡 Medium | 1 |
| 🟢 Low | 1 |
| **Total** | **6** |

## Description

ServiceRegistry is a microservice discovery and caching layer that tracks service instances, performs health monitoring, and routes requests to available backends. The system provides service registration and deregistration, caching layer for metadata and discovery results, health checking with configurable intervals, request routing to healthy instances, service discovery with availability tracking, and authentication token management.

The architecture enables microservices to register themselves with metadata, clients to discover available service instances, health checks to monitor service availability, automatic routing to healthy instances, caching to reduce lookup overhead, and token-based authentication for secure service communication.

## Directory Structure

```
repo3/
  README.md
  serviceregistry/
    __init__.py           # Package exports
    registry.py           # Service registry and persistence
    cache.py              # Caching layer for metadata
    health.py             # Health checking service
    router.py             # Request routing to instances
    discovery.py          # Service discovery and tracking
    auth.py               # Authentication token management
```

## Component Overview

- **registry.py**: Maintains the central registry of service instances. Handles registration, deregistration, and persistence to file. Integrates with cache and token manager to provide complete service information.

- **cache.py**: Provides caching for service metadata and discovery results to reduce lookups. Supports configurable TTL values and timestamp-based freshness checking. Stores service information including authentication tokens.

- **health.py**: Performs periodic health checks on registered services. Makes HTTP requests to service health endpoints and updates service availability status through the discovery module.

- **router.py**: Routes incoming requests to healthy service instances. Maintains a cache of available instances and checks health status before forwarding requests. Implements load distribution across healthy backends.

- **discovery.py**: Tracks service availability and provides discovery capabilities. Maintains in-memory status of which services are up or down. Caches discovery results with configurable TTL.

- **auth.py**: Manages authentication tokens for service-to-service communication. Handles token refresh, expiration tracking, and validation. Stores current tokens for each registered service.

## Known Issues

⚠️ **This repository contains intentional bugs for testing bug detection systems.**

### 🔴 Critical Issues (2 total)

1. **Cache invalidation race condition allowing stale data**: The registry updates its internal timestamp before updating the actual service list, then signals the cache to invalidate. The cache checks the timestamp to determine data freshness. Under concurrent access, the timestamp update happens before data is actually modified, causing the cache to serve stale service entries that appear fresh based on timestamp alone.

2. **Token refresh cache desynchronization causing authentication failures**: The token manager refreshes authentication tokens and updates its internal state when tokens expire. However, the cache stores service metadata including authentication tokens from earlier queries. When the registry retrieves service information, it queries the cache which returns metadata with old tokens. Requests use these stale tokens despite fresh tokens existing in the token manager, resulting in 401 authentication errors.

### 🟠 High Issues (2 total)

3. **Health check blocking event loop freezing concurrent requests**: Health checker uses synchronous blocking I/O operations for HTTP requests to service health endpoints. This runs inside async functions called from the router's async request handler. When health checks take time due to slow or timing-out services, the blocking I/O freezes the entire event loop, preventing all other concurrent requests from progressing until the health check completes or times out.

4. **Service resurrection from file reload overwriting runtime state**: Service discovery marks services as down in its in-memory tracking when health checks fail. The registry periodically reloads its service list from a persistence file which still lists these services as up. This file reload overwrites the in-memory down status, causing dead services to come back to life and receive traffic again despite being unhealthy.

### 🟡 Medium Issues (1 total)

5. **TTL unit mismatch between discovery and cache**: Service discovery sets cache TTL values intending them to be interpreted as minutes for longer cache retention. The cache implementation interprets all TTL values as seconds. A configured 5-minute TTL becomes 5 seconds in practice, causing excessive cache misses and hammering the discovery service with repeated lookups.

### 🟢 Low Issues (1 total)

6. **Inconsistent return types preventing error distinction**: The discovery find_services() method returns an empty dictionary when no services are found for a requested type but returns an empty list when the discovery operation itself fails. Callers cannot distinguish between "no services currently available" and "discovery system is broken" due to the type difference.

## Expected Behavior

The registry should provide consistent service information with proper cache invalidation. Token refresh should propagate to all components using authentication. Health checks should run asynchronously without blocking other operations. Service status should be consistently tracked across file persistence and in-memory state. TTL values should have consistent units across all components. API methods should have consistent return types for error handling.

## Usage Example

```python
import asyncio
from serviceregistry import (
    ServiceRegistry, Cache, HealthChecker,
    Router, ServiceDiscovery, TokenManager
)

async def main():
    # Create components
    cache = Cache()
    token_manager = TokenManager(token_ttl=3600)
    discovery = ServiceDiscovery(cache)
    health_checker = HealthChecker(discovery)

    registry = ServiceRegistry(
        cache=cache,
        token_manager=token_manager,
        persistence_path="./services.json"
    )

    router = Router(registry, health_checker)

    # Register a service
    registry.register_service(
        service_id="api-1",
        host="localhost",
        port=8080,
        metadata={"type": "api", "version": "1.0"}
    )

    # Set authentication token
    token_manager.set_token("api-1", "secret-token-123")

    # Discover services
    services = discovery.find_services("api")
    print(f"Found {len(services)} API services")

    # Route a request
    response = await router.route_request(
        service_type="api",
        request_data={"action": "list"}
    )
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```
