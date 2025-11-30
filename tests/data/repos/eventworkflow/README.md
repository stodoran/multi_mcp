# EventWorkflowEngine

## Bug Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 2 |
| 🟡 Medium | 1 |
| **Total** | **5** |

## Description

EventWorkflowEngine is an event-driven workflow orchestration engine with saga pattern, compensation logic, event sourcing, and CQRS. It handles long-running workflows with retries, timeouts, and distributed transaction management.

## Directory Structure

```
repo6/
  README.md
  eventworkflow/
    __init__.py           # Package initialization
    engine.py             # Workflow engine core (98 lines)
    saga.py               # Saga implementation (113 lines)
    event_bus.py          # Event pub/sub (48 lines)
    event_store.py        # Event sourcing (61 lines)
    projections.py        # CQRS projections (62 lines)
    compensations.py      # Compensation manager (34 lines)
    state_machine.py      # State management (54 lines)
    scheduler.py          # Task scheduler (30 lines)
    snapshots.py          # Snapshot optimization (32 lines)
```

---

## Detailed Bug Descriptions

### 🔴 CRITICAL BUG #1: Event Ordering Violation Causing State Corruption
**Files:** `event_bus.py`, `event_store.py`, `projections.py`, `state_machine.py`, `saga.py`
**Lines:** event_bus.py:36-41, event_store.py:45-58, projections.py:36-48, state_machine.py:23-36, saga.py:66-75

**Description:**
Events are published to EventBus with sequence numbers (event_store.py:45-51). Multiple projections subscribe via ProjectionManager. Due to async processing and event partitioning (event_bus.py:36: `partition = hash(event_type) % 4`), different projections receive events out-of-order across partitions.

The EventBus publishes to different partitions based on event type hash (line 36), but projections subscribe to multiple event types that span partitions. Projection A might receive events [1, 3, 2] while Projection B receives [1, 2, 3]. The projections (projections.py:42) process events in **arrival order, not sequence order**: `self._update_counter(event)` increments without checking sequence.

The state_machine.py allows illegal transitions (line 36: `COMPLETED → RUNNING` is allowed during replay). When saga.py queries projections for decision-making (line 70), it sees inconsistent states, making wrong compensation decisions.

**Decoy code:**
- Comment at event_bus.py:35: "# Events are delivered in-order within a partition" (but projections span partitions)
- Sequence number field exists but only for debugging, not ordering
- Buffering logic appears to sort at projections.py:47, but actually: `# sort by timestamp` (not sequence)

**Cross-file interaction:** event_bus.py → event_store.py → projections.py → state_machine.py → saga.py

**Why it requires cross-file reasoning:**
- Reading event_bus.py alone: Partitioning seems normal for scalability
- Reading event_store.py alone: Sequence numbers suggest ordering is handled
- Reading projections.py alone: Processing events as they arrive seems reasonable
- Together: Reveals partitioning breaks ordering across event types, projections don't sort by sequence

---

### 🔴 CRITICAL BUG #2: Compensation Cascade Deadlock
**Files:** `saga.py`, `compensations.py`, `engine.py`, `scheduler.py`
**Lines:** saga.py:98-110, compensations.py:22-30, engine.py:31-59, scheduler.py:19-27

**Description:**
Saga step fails, triggering compensation (saga.py:98). CompensationManager executes compensating transactions (compensations.py:22) using ThreadPoolExecutor with `max_workers=10` (line 14). Each compensation can itself fail and schedule a retry via scheduler.

The scheduler also uses ThreadPoolExecutor (scheduler.py:14) with shared worker pool. Under compensation storm (all workers busy), a compensation tries to acquire the saga's `_state_lock` (saga.py:47: `async with self._state_lock`). The engine holds this lock while waiting for compensation to complete (engine.py:36).

**Deadlock sequence:**
1. Engine acquires saga lock (engine.py:36)
2. Saga fails, calls compensate() (engine.py:45)
3. CompensationManager submits to executor (compensations.py:25)
4. All 10 workers busy with compensations
5. Compensation needs to read saga state (requires lock from line 1)
6. Worker waits for lock, engine waits for worker → deadlock

**Decoy code:**
- Timeout on lock at engine.py:35: `timeout=60.0` (but longer than health check interval)
- Comment at compensations.py:13: "# Worker pool sized for expected load" (doesn't account for storms)
- Retry backoff makes it worse by holding locks longer

**Cross-file interaction:** saga.py ↔ compensations.py ↔ engine.py ↔ scheduler.py

**Why it requires cross-file reasoning:**
- Reading saga.py alone: Lock usage seems normal
- Reading compensations.py alone: ThreadPoolExecutor seems fine
- Reading engine.py alone: Calling compensate() while holding lock seems safe
- Together: Reveals resource exhaustion (thread pool) + lock holding causes deadlock

---

### 🟠 HIGH BUG #3: Event Store Replay Race Causing Duplicate Events
**Files:** `event_store.py`, `snapshots.py`, `projections.py`, `state_machine.py`
**Lines:** event_store.py:51-58, snapshots.py:18-28, projections.py:42-48, state_machine.py:35-36

**Description:**
System crashes and restarts. EventStore replays events from last snapshot (event_store.py:51). The `replay_from_snapshot()` method re-emits events without tracking which were already processed (line 56: "# Re-emits events without tracking"). At-least-once delivery means some events were processed before crash.

Projections handle events without idempotency (projections.py:46): `self.count += 1` without checking `event.id` for duplicates. The projection has `last_event_id` field (line 24) that's written but never read for deduplication.

StateMachine allows illegal transitions during replay (state_machine.py:35): `COMPLETED → RUNNING` is allowed (line 36), causing corrupted state. Snapshots save this corrupted state (snapshots.py:26), poisoning future replays.

**Decoy code:**
- Event ID field exists (projections.py:47) but only for logging
- "Idempotency key" in schema (`last_event_id`) but never checked
- Comment at event_store.py:52: "# Replay from last snapshot for crash recovery" (seems complete)

**Cross-file interaction:** event_store.py ↔ snapshots.py ↔ projections.py ↔ state_machine.py

**Why it requires cross-file reasoning:**
- Reading event_store.py alone: Replay logic seems straightforward
- Reading snapshots.py alone: Snapshot creation seems complete
- Reading projections.py alone: `last_event_id` field suggests dedup is handled
- Together: Reveals replay doesn't track processed events, projections aren't idempotent, snapshots save corrupted state

---

### 🟠 HIGH BUG #4: Contextvars Leakage Across Saga Instances
**Files:** `engine.py`, `saga.py`, `event_bus.py`, `projections.py`
**Lines:** engine.py:12-13,41-59, saga.py:13-14,66-75, event_bus.py:10-11,39-41, projections.py:10-11,36-42

**Description:**
The engine uses `contextvars.ContextVar('saga_id')` (engine.py:12) to track current saga for logging and tracing. When executing a saga, it sets the context (line 41: `current_saga_id.set(saga_id)`).

When saga publishes events (saga.py:74), EventBus spawns async handlers (event_bus.py:41: `asyncio.create_task(handler(event_data))`). Contextvars are **automatically copied to child tasks**, so handlers inherit saga context from whatever saga was active when task was created.

Under concurrent load:
1. Saga A publishes Event X, spawns handler H1 (with saga_id=A in context)
2. Before H1 runs, Saga B becomes active, sets saga_id=B
3. Saga B publishes Event Y, spawns handler H2
4. Handler H1 finally runs but sees `current_saga_id.get() = B` (not A!)

Projections use `current_saga_id.get()` (projections.py:37) to update saga-specific state, causing Saga A's events to update Saga B's projection.

**Decoy code:**
- Comment at engine.py:11: "# Contextvars provide automatic context propagation in async code"
- Initialization appears safe: `current_saga_id.set(saga_id)` at saga start
- Cleanup in finally: `current_saga_id.set(None)` (but async tasks already copied old context)

**Cross-file interaction:** engine.py → saga.py → event_bus.py → projections.py

**Why it requires cross-file reasoning:**
- Reading engine.py alone: Setting contextvar seems correct
- Reading event_bus.py alone: `create_task()` seems normal
- Reading projections.py alone: Reading contextvar seems safe
- Together: Reveals contextvar copying in `create_task()` causes state bleeding across concurrent sagas

---

### 🟡 MEDIUM BUG #5: Asyncio Cancellation Not Propagating to Nested Tasks
**Files:** `scheduler.py`, `engine.py`, `saga.py`, `compensations.py`
**Lines:** scheduler.py:24-27, engine.py:35-48, saga.py:44-58, compensations.py:22-30

**Description:**
When saga times out, engine cancels the task (engine.py:35: `asyncio.wait_for(..., timeout=60.0)`). The engine catches `CancelledError` (line 44) and initiates compensation. However, saga has spawned nested tasks for parallel step execution (saga.py:49: `asyncio.create_task()`).

The saga uses `asyncio.gather(*step_tasks, return_exceptions=True)` (line 54). The **bug**: `return_exceptions=True` suppresses `CancelledError`, converting it to a returned exception instead of propagating. Nested tasks don't know they're cancelled and continue running.

Compensations start executing (engine.py:45) while original saga steps are still running, causing race conditions (e.g., compensating a transfer before transfer completes).

**Decoy code:**
- Comment at saga.py:54: "# Use return_exceptions=True to handle partial failures gracefully"
- Cancellation check that appears thorough: `if asyncio.current_task().cancelled(): return`
- Timeout wrapper (engine.py:35) suggests cancellation is handled

**Cross-file interaction:** scheduler.py → engine.py → saga.py → compensations.py

**Why it requires cross-file reasoning:**
- Reading engine.py alone: Timeout and CancelledError handling seem complete
- Reading saga.py alone: `return_exceptions=True` seems like good error handling
- Reading compensations.py alone: Compensation execution seems straightforward
- Together: Reveals `return_exceptions=True` breaks cancellation propagation, causing compensation to run concurrently with still-running steps

---

## Expected Behavior

The system should provide reliable workflow orchestration with:
- Events processed in sequence order across all projections
- Saga compensation without deadlocks, even under high failure rates
- Idempotent event replay after crashes
- Proper context isolation across concurrent saga executions
- Complete cancellation propagation to all nested tasks
- State machine transitions validated during replay
- Thread pool sizing that accounts for compensation cascades

## Usage Example

```python
import asyncio
from eventworkflow import (
    WorkflowEngine, Saga, SagaStep,
    EventBus, EventStore, ProjectionManager,
    CompensationManager, SnapshotManager
)

async def main():
    event_bus = EventBus()
    event_store = EventStore()
    projection_mgr = ProjectionManager()
    snapshot_mgr = SnapshotManager()
    engine = WorkflowEngine()

    saga = Saga("order-saga-1", event_bus)

    async def process_payment(amount):
        print(f"Processing payment: ${amount}")
        return {"status": "success"}

    async def compensate_payment(amount):
        print(f"Refunding payment: ${amount}")

    step = SagaStep(
        name="payment",
        action=process_payment,
        compensation=compensate_payment,
        args=(100,)
    )

    saga.add_step(step)
    engine.register_saga(saga)

    result = await engine.execute_saga("order-saga-1")
    print(f"Saga result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```
