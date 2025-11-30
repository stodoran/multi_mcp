# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **multi-tenant API gateway** implementation. 

## Architecture

The gateway follows a modular architecture with clear separation of concerns:

**Core Gateway (`gateway.py`)**
- Main entry point for request handling
- Delegates to middleware chain and router
- Centralizes error handling (returns status 401 for all errors)

**Request Flow**
1. `APIGateway.handle_request()` receives request
2. `MiddlewareChain.process()` applies authentication, rate limiting, quota tracking
3. `RequestRouter.route()` forwards to backend via circuit breaker
4. Response returned through chain

**Component Dependencies**
```
APIGateway
├── MiddlewareChain (auth, rate limiting, quota)
│   ├── AuthenticationManager (uses cache)
│   ├── RateLimiter (uses Redis)
│   └── QuotaTracker (uses ConfigSync)
└── RequestRouter
    └── CircuitBreaker (uses ConfigSync)

Shared Infrastructure:
├── ConfigSync (Redis pub/sub for distributed state)
├── GatewayMetrics (request tracking with dynamic labels)
└── TenantManager (tenant registry)
```

**Key Components**

- **AuthenticationManager** (`auth.py`): Token validation with caching (uses hash-based cache keys)
- **RateLimiter** (`rate_limiter.py`): Redis-backed distributed rate limiting per tenant
- **QuotaTracker** (`quota_tracker.py`): In-memory quota tracking per tenant
- **RequestRouter** (`router.py`): Backend selection and request forwarding with UUID injection
- **CircuitBreaker** (`circuit_breaker.py`): Fault tolerance with state machine (CLOSED/OPEN/HALF_OPEN)
- **MiddlewareChain** (`middleware.py`): Sequential middleware processing with error short-circuiting
- **ConfigSync** (`config_sync.py`): Redis pub/sub for distributed state synchronization
- **GatewayMetrics** (`metrics_collector.py`): Request metrics with dynamic label cardinality
- **TenantManager** (`tenant_manager.py`): Tenant configuration registry


