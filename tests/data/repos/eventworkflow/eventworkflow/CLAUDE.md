# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EventWorkflowEngine is an event-driven workflow orchestration library implementing the Saga pattern for distributed transactions. It provides event sourcing, CQRS (Command Query Responsibility Segregation), and compensation logic for managing complex distributed workflows with rollback capabilities.

## Architecture

### Core Design Patterns

**Saga Pattern**: Implements distributed transaction management where a workflow consists of multiple steps that can be compensated (rolled back) if any step fails. Each saga step has an action and an optional compensation function.

**Event Sourcing**: All state changes are persisted as immutable events in the EventStore. System state can be reconstructed by replaying events from the event log.

**CQRS**: Separates write operations (commands that generate events) from read operations (projections that consume events to build read models).

**Pub/Sub Messaging**: EventBus provides asynchronous communication between components using a publish-subscribe pattern.

### Component Interactions

**WorkflowEngine** (engine.py) is the orchestration layer that:
- Registers and executes sagas
- Manages per-saga locks to prevent concurrent execution
- Sets saga context using contextvars for thread-local state
- Handles timeout and cancellation with automatic compensation
- Coordinates with StateMachine for workflow state tracking

**Saga** (saga.py) executes distributed transactions by:
- Managing a sequence of SagaStep instances (action + compensation pairs)
- Executing all steps concurrently using asyncio.gather
- Publishing step completion events to the EventBus
- Rolling back completed steps in reverse order if any step fails
- Tracking completed steps for partial compensation

**EventBus** (event_bus.py) provides pub/sub messaging:
- Maintains subscriber registry keyed by event type
- Publishes events asynchronously to all registered handlers
- Partitions events by hash (currently unused but suggests future sharding)
- Fires event handlers as background tasks (no await)

**EventStore** (event_store.py) persists events:
- Appends events with monotonically increasing sequence numbers
- Supports aggregate-based event retrieval
- Enables replay from snapshots for optimization
- Uses in-memory storage (production would use database)

**ProjectionManager** (projections.py) builds read models:
- Consumes events to update CQRS read models (projections)
- Each projection maintains event counter and last processed event ID
- No idempotency checks (events can be processed multiple times)
- Reads saga_id from contextvars to track which saga triggered updates

**StateMachine** (state_machine.py) tracks workflow states:
- Enforces valid state transitions (PENDING → RUNNING → COMPLETED/FAILED)
- Supports compensation flow (FAILED → COMPENSATING)
- Prevents invalid transitions (e.g., can't go from COMPLETED to FAILED)

**SnapshotManager** (snapshots.py) optimizes event replay:
- Creates point-in-time snapshots of aggregate state
- Enables event replay from last snapshot instead of beginning
- Reduces replay cost for aggregates with long event histories

**CompensationManager** (compensations.py) executes saga rollbacks:
- Runs compensation functions in reverse order using ThreadPoolExecutor
- Schedules compensations for batch execution
- Propagates compensation failures

**WorkflowScheduler** (scheduler.py) handles delayed execution:
- Schedules tasks with configurable delay
- Uses ThreadPoolExecutor for concurrent task execution
- Returns task IDs for tracking

## Code Modification Guidelines

When modifying this codebase:

- All public APIs are async - maintain this pattern
- Preserve the saga context pattern using contextvars
- Lock acquisitions in WorkflowEngine must remain at saga execution level
- Event handler registration should remain synchronous, only invocation is async
- Maintain backward compatibility for SagaStep dataclass (used by consumers)
- State machine transitions must follow the valid_transitions map
- All event store operations should be atomic (even if in-memory now)
