# AsyncTaskQueue

## Bug Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 3 |
| 🟡 Medium | 2 |
| 🟢 Low | 1 |
| **Total** | **8** |

## Description

AsyncTaskQueue is a lightweight asynchronous task processing system that provides a queue-based architecture for executing background jobs. The system consists of a task queue manager, worker pool for parallel execution, periodic job scheduler, configurable settings management, and persistent result storage.

## Directory Structure

```
repo1/
  README.md
  asynctaskqueue/
    __init__.py           # Package initialization
    queue.py              # Task queue manager (142 lines)
    worker.py             # Worker pool (103 lines)
    scheduler.py          # Job scheduler (162 lines)
    config.py             # Configuration (45 lines)
    storage.py            # Result storage (80 lines)
```

---

## Detailed Bug Descriptions

### 🔴 CRITICAL BUG #1: Async/Sync Deadlock
**Files:** `scheduler.py`, `queue.py`
**Lines:** scheduler.py:89-94, queue.py:47-79

**Description:**
The scheduler calls `queue.add_task()` from a synchronous threading context (scheduler.py:89), but `add_task()` is an async method that uses `asyncio.Lock()` internally (queue.py:47,68). When the scheduler thread tries to call this async function without await from a non-async context, it causes a deadlock or RuntimeError because:
1. scheduler.py:89 calls `self._queue.add_task()` directly (no await)
2. queue.py:68 has `async with self._lock` which requires async context
3. The threading.Timer callback in scheduler.py:81-99 runs in a sync thread
4. Result: Lock can never be acquired, tasks can't be enqueued

**Cross-file interaction:** scheduler.py → queue.py

**Why it requires cross-file reasoning:**
- Reading scheduler.py alone: Looks like normal method call
- Reading queue.py alone: Async method seems correct
- Together: Reveals sync caller trying to use async lock

---

### 🔴 CRITICAL BUG #2: Race Condition in Storage
**Files:** `storage.py`, `worker.py`
**Lines:** storage.py:14-16,39-51, worker.py:35-38,64,84,90

**Description:**
ResultStorage uses non-thread-safe dictionaries (storage.py:14-16) with compound read-modify-write operations (storage.py:48-51). WorkerPool spawns multiple threads via ThreadPoolExecutor (worker.py:35-38,46) that all call `storage.increment_retry_count()` and `store_result()` concurrently (worker.py:84,90). The increment operation:
1. Line 48: Reads current value: `current_count = self._retry_counts.get(task_id, 0)`
2. Line 49: Calculates new value: `new_count = current_count + 1`
3. Line 50: Writes new value: `self._retry_counts[task_id] = new_count`

Under concurrent access from multiple worker threads, two threads can read the same value (e.g., 5), both calculate 6, and both write 6, losing one increment.

**Cross-file interaction:** storage.py → worker.py

**Why it requires cross-file reasoning:**
- Reading storage.py alone: increment_retry_count() looks reasonable
- Reading worker.py alone: ThreadPoolExecutor usage seems fine
- Together: Reveals concurrent writes to unsynchronized storage

---

### 🟠 HIGH BUG #3: Resource Exhaustion from Unlimited Workers
**Files:** `config.py`, `worker.py`
**Lines:** config.py:22, worker.py:35-38,46

**Description:**
Config defaults `max_workers=0` (config.py:22) which worker.py interprets as unlimited (worker.py:35-38). When creating ThreadPoolExecutor with `max_workers=None` (worker.py:46), it spawns unbounded threads. Under high task load, this can create thousands of threads, exhausting system resources (memory, file descriptors) and causing denial of service.

**Cross-file interaction:** config.py → worker.py

**Why it requires cross-file reasoning:**
- Reading config.py alone: 0 seems like a valid default
- Reading worker.py alone: None for unlimited might seem intentional
- Together: Reveals dangerous default enabling resource exhaustion

---

### 🟠 HIGH BUG #4: Silent Task Loss
**Files:** `worker.py`, `queue.py`
**Lines:** worker.py:87-97, queue.py:96-107

**Description:**
When task execution fails, worker.py catches all exceptions (worker.py:87) and logs intent to retry (worker.py:92-93), but never actually re-enqueues the task. The worker just marks it as failed (worker.py:97) and the task is lost forever. The queue.mark_completed() method (queue.py:96-107) silently accepts the failure without verifying retry logic exists.

Sequence:
1. Task fails in worker.py:87
2. Line 90: increment_retry_count() called
3. Line 92-93: Log says "Will retry" but no code to re-enqueue
4. Line 97: Mark as failed and task is lost
5. queue.py has no retry mechanism

**Cross-file interaction:** worker.py → queue.py

**Why it requires cross-file reasoning:**
- Reading worker.py alone: Logging suggests retry happens
- Reading queue.py alone: Unclear if retries are external
- Together: Reveals missing retry implementation

---

### 🟠 HIGH BUG #5: Cancellation Propagation Failure
**Files:** `scheduler.py`, `queue.py`
**Lines:** scheduler.py:101-120, queue.py:140-142

**Description:**
When cancel_job() is called (scheduler.py:101-120), it cancels the timer (line 118) and pauses the job (line 115), but never notifies queue.py about tasks that should be aborted. The queue continues to track these tasks as RUNNING forever (queue.py:140-142). This causes stuck metrics and prevents cleanup.

**Cross-file interaction:** scheduler.py → queue.py

**Why it requires cross-file reasoning:**
- Reading scheduler.py alone: cancel_job seems complete
- Reading queue.py alone: No way to know about scheduler cancellations
- Together: Reveals missing state synchronization

---

### 🟡 MEDIUM BUG #6: Inconsistent Error Handling
**Files:** `queue.py`, `worker.py`
**Lines:** queue.py:31-38, worker.py:87

**Description:**
TaskQueue raises custom exceptions `QueueFullError` and `TaskNotFoundError` (queue.py:31-38), but worker.py catches generic `Exception` (worker.py:87). This means:
- QueueFullError gets caught and logged like any error
- TaskNotFoundError gets caught and logged like any error
- No special handling for queue-specific errors
- Callers can't rely on consistent error propagation

**Cross-file interaction:** queue.py → worker.py

**Why it requires cross-file reasoning:**
- Reading queue.py alone: Custom exceptions seem purposeful
- Reading worker.py alone: Catching Exception seems safe
- Together: Reveals exception hierarchy is ignored

---

### 🟡 MEDIUM BUG #7: Timeout Unit Mismatch
**Files:** `config.py`, `worker.py`
**Lines:** config.py:17,23, worker.py:73,78-79

**Description:**
Config defines `task_timeout` with documentation saying "seconds" (config.py:17) and defaults to 30.0 (config.py:23). However, worker.py uses this value directly as milliseconds (worker.py:73,78-79):
- Line 73: `timeout_ms = self._config.task_timeout` (no conversion!)
- Line 78: `elapsed_ms = (time.time() - start_time) * 1000` (milliseconds)
- Line 79: `if elapsed_ms > timeout_ms` (comparing ms to seconds!)

Result: 30 second timeout becomes 30 milliseconds, causing premature timeouts.

**Cross-file interaction:** config.py → worker.py

**Why it requires cross-file reasoning:**
- Reading config.py alone: Seconds seems clear from docs
- Reading worker.py alone: Variable named timeout_ms suggests milliseconds
- Together: Reveals unit conversion is missing

---

### 🟢 LOW BUG #8: Confusing API Naming
**Files:** `scheduler.py`, `queue.py`
**Lines:** scheduler.py:101-120, queue.py:109-122

**Description:**
Inconsistent naming across modules causes confusion:
- scheduler.py:101 `cancel_job()` actually pauses (sets paused=True at line 115)
- queue.py:109 `remove_task()` actually cancels (deletes task at line 122)

Users expect "cancel" to mean permanent cancellation, but scheduler's cancel just pauses while queue's remove truly cancels. The API violates principle of least surprise.

**Cross-file interaction:** scheduler.py ↔ queue.py

**Why it requires cross-file reasoning:**
- Reading scheduler.py alone: cancel_job name seems appropriate
- Reading queue.py alone: remove_task name seems appropriate
- Together: Reveals semantic inconsistency

---

## Expected Behavior

The system should provide reliable asynchronous task execution with proper error handling, timeout enforcement, and state management. Worker pool size should be configurable with reasonable defaults. Failed tasks should be retried according to configuration. Scheduled jobs should integrate cleanly with the async queue. All state transitions and cancellations should be properly tracked and propagated across modules.

## Usage Example

```python
import asyncio
from asynctaskqueue import TaskQueue, WorkerPool, Scheduler, Config, ResultStorage

async def main():
    config = Config(max_workers=4, task_timeout=30.0)
    queue = TaskQueue(max_size=1000)
    storage = ResultStorage()
    worker_pool = WorkerPool(queue, storage, config)
    scheduler = Scheduler(queue)

    worker_pool.start()

    def my_task(x, y):
        return x + y

    await queue.add_task("task1", my_task, args=(5, 3))

    job_id = scheduler.schedule_periodic(lambda: print("Running"), interval=60.0)

    await asyncio.sleep(1)
    result = storage.get_result("task1")
    print(f"Result: {result}")

    scheduler.cancel_job(job_id)
    worker_pool.stop()

if __name__ == "__main__":
    asyncio.run(main())
```
