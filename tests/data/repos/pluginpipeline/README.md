# PluginDataPipeline

## Bug Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 2 |
| 🟡 Medium | 1 |
| **Total** | **5** |

## Description

PluginDataPipeline is an extensible data processing pipeline with plugin system, resource pooling, backpressure handling, and stream processing. Supports hot-reload of plugins without downtime for dynamic pipeline reconfiguration.

## Directory Structure

```
repo7/
  README.md
  pluginpipeline/
    __init__.py           # Package initialization
    pipeline.py           # Pipeline orchestration (33 lines)
    plugin_loader.py      # Plugin loading/hot-reload (51 lines)
    executor.py           # Task executor (41 lines)
    resource_pool.py      # Resource pooling (40 lines)
    backpressure.py       # Backpressure management (20 lines)
    stream.py             # Stream processing (29 lines)
    metrics.py            # Metrics collection (23 lines)
    config_watcher.py     # Config file watcher (25 lines)
    isolation.py          # Plugin isolation (30 lines)
```

---

## Detailed Bug Descriptions

### 🔴 CRITICAL BUG #1: Plugin Hot-Reload Race Causing Data Corruption
**Files:** `config_watcher.py`, `plugin_loader.py`, `pipeline.py`, `executor.py`, `stream.py`
**Lines:** config_watcher.py:20-25, plugin_loader.py:36-48, pipeline.py:23-27, executor.py:17-27, stream.py:21-27

**Description:**
Config file changes trigger hot-reload via ConfigWatcher (config_watcher.py:20). It calls `PluginLoader.reload_plugin()` (plugin_loader.py:36) which deletes the plugin module from `sys.modules` (line 43: `del sys.modules[module_name]`) and reimports.

Meanwhile, Executor is actively using the old plugin to process streams (executor.py:20). The plugin_loader deletes the old plugin class, loads new version. In-flight processing in stream.py now has **half-old, half-new state**: old method references but new class attributes.

**Sequence:**
1. ConfigWatcher detects change, calls reload (config_watcher.py:24)
2. PluginLoader deletes sys.modules entry (plugin_loader.py:43)
3. Executor still has reference to old plugin class (executor.py:20)
4. Stream processing accesses renamed attributes → AttributeError
5. Pipeline receives corrupted data (pipeline.py:25)

**Decoy code:**
- Grace period at config_watcher.py:21: `time.sleep(1)  # Allow in-flight requests to complete`
- Comment at plugin_loader.py:37: "# Each plugin has isolated module namespace"
- Comment at plugin_loader.py:41: "# Hot-reload is safe because Python module import is atomic"

**Cross-file interaction:** config_watcher.py → plugin_loader.py → pipeline.py → executor.py → stream.py

**Why it requires cross-file reasoning:**
- Reading config_watcher.py alone: Grace period suggests safety
- Reading plugin_loader.py alone: Delete and reimport seems atomic
- Reading executor.py alone: Using plugin reference seems normal
- Together: Reveals grace period is arbitrary (too short under load), module deletion doesn't wait for active references

---

### 🔴 CRITICAL BUG #2: Resource Pool Deadlock via Nested Acquisition
**Files:** `resource_pool.py`, `executor.py`, `pipeline.py`, `plugin_loader.py`
**Lines:** resource_pool.py:14-41, executor.py:17-38, pipeline.py:18-27, plugin_loader.py:17-28

**Description:**
ResourcePool has fixed size `max_size=10` (resource_pool.py:18). Executor acquires connection for main task (executor.py:20: `conn = await self._pool.acquire()`). Plugin then calls `run_subtask()` (executor.py:31) which tries to acquire **another connection** (nested acquisition).

Under load, all 10 connections held by first-level tasks, each waiting for second connection:
1. Task 1-10 each hold 1 connection
2. Each tries to acquire 2nd connection via subtask
3. Pool exhausted, all tasks block on `_semaphore.acquire()` (resource_pool.py:26)
4. Timeout exists (60s) but longer than health check (30s)

**Decoy code:**
- Timeout at resource_pool.py:26: `timeout=60.0` (doesn't prevent deadlock)
- Comment at resource_pool.py:17: "# Pool size tuned for concurrent tasks"
- Semaphore usage suggests thread-safety is handled

**Cross-file interaction:** resource_pool.py ↔ executor.py ↔ pipeline.py ↔ plugin_loader.py

**Why it requires cross-file reasoning:**
- Reading resource_pool.py alone: Fixed pool with semaphore seems correct
- Reading executor.py alone: Acquiring resources for tasks seems normal
- Together: Reveals nested acquisition pattern exhausts pool, causing deadlock

---

### 🟠 HIGH BUG #3: Backpressure Signal Inversion Causing OOM
**Files:** `backpressure.py`, `stream.py`, `executor.py`, `pipeline.py`
**Lines:** backpressure.py:13-21, stream.py:17-27, executor.py:14-16, pipeline.py:13-16

**Description:**
When downstream is slow, BackpressureManager signals upstream via `_should_throttle` flag (backpressure.py:15). StreamProcessor checks before emitting (stream.py:20). However, Executor uses bounded queue (`maxsize=1000`, executor.py:15) while Pipeline uses **unbounded buffer** (pipeline.py:14: `self._buffer = deque()`).

The **signal inversion bug**: BackpressureManager.should_throttle() returns `not self._should_throttle` (backpressure.py:21), inverting the signal. When queue is full, `_should_throttle=True` is set, but `should_throttle()` returns False, telling stream to continue.

Meanwhile, Pipeline doesn't check backpressure at all (pipeline.py:24) and keeps buffering, eventually OOMing.

**Decoy code:**
- Comment at backpressure.py:20: "# Throttle when backpressure signal is active"
- Method name suggests correct behavior: `should_throttle()`
- Code structure looks like defensive check: `return not self._should_throttle`

**Cross-file interaction:** backpressure.py → stream.py → executor.py → pipeline.py

**Why it requires cross-file reasoning:**
- Reading backpressure.py alone: Double negative looks like defensive programming
- Reading stream.py alone: Checking backpressure seems correct
- Reading pipeline.py alone: Unbounded buffer isn't obviously wrong
- Together: Reveals signal inversion (`not self._should_throttle`) + missing pipeline check causes OOM

---

### 🟠 HIGH BUG #4: Logging Handler State Leakage Across Plugins
**Files:** `isolation.py`, `plugin_loader.py`, `executor.py`, `metrics.py`
**Lines:** isolation.py:16-34, plugin_loader.py:36-48, executor.py:17-27, metrics.py:11-23

**Description:**
Plugins run in "isolated" namespaces (isolation.py:20). However, Python's `logging` module is a **global singleton**. Plugin A configures logging: `logging.basicConfig(level=DEBUG, handlers=[...])`, mutating the global root logger.

Plugin B loads in separate namespace (plugin_loader.py:45) but still uses the same global `logging` module (singletons aren't isolated). Plugin B inherits Plugin A's DEBUG level and handlers, flooding disk.

When Plugin A unloads, `isolation.py` calls cleanup (line 29: `del sys.modules[plugin_name]`) which closes file handlers. But Plugin B still references closed handlers in global logger, causing `ValueError: I/O operation on closed file`.

**Decoy code:**
- Comment at isolation.py:24: "# Created namespace for {plugin_name}" (suggests isolation is complete)
- Comment at plugin_loader.py:37: "# Each plugin has isolated module namespace"
- Module deletion at isolation.py:32 suggests cleanup is thorough

**Cross-file interaction:** isolation.py → plugin_loader.py → executor.py → metrics.py

**Why it requires cross-file reasoning:**
- Reading isolation.py alone: Namespace creation and cleanup seem complete
- Reading plugin_loader.py alone: Reload logic seems safe
- Reading metrics.py alone: Singleton pattern seems normal
- Together: Reveals logging is global singleton that escapes namespace isolation

---

### 🟡 MEDIUM BUG #5: Stream Window Semantic Mismatch (Inclusive/Exclusive)
**Files:** `stream.py`, `executor.py`, `pipeline.py`, `metrics.py`
**Lines:** stream.py:24-27, executor.py:17-27, pipeline.py:23-27, metrics.py:18-23

**Description:**
Tumbling windows of 10 seconds. Event at timestamp 10.0 belongs to [0, 10) or [10, 20)? **Different modules use different semantics:**

- stream.py:27: Uses **inclusive upper**: `if start <= ts <= end`
- executor.py:23: Would use **exclusive upper** (if it had windowing): `if start <= ts < end`
- pipeline.py:25: Implicitly assumes **inclusive both bounds**
- metrics.py:20: Aggregates assuming **exclusive upper**

When events arrive exactly on boundaries (10.0, 20.0):
- Stream adds to [0, 10] (inclusive)
- Metrics expects [0, 10) (exclusive)
- Event at 10.0 appears in both windows OR neither

**Decoy code:**
- Comment at stream.py:23: "# Window: [start, end)" (but code uses `<=` for both)
- Type hints suggest clarity but callers ignore semantics
- Unit test passes: `assert 10.0 in window` (doesn't test cross-module behavior)

**Cross-file interaction:** stream.py → executor.py → pipeline.py → metrics.py

**Why it requires cross-file reasoning:**
- Reading stream.py alone: Comment says exclusive but code is inclusive (discrepancy)
- Reading metrics.py alone: Exclusive upper bound seems standard
- Together: Reveals semantic mismatch across module boundaries, not just simple off-by-one

---

## Expected Behavior

The system should provide reliable data processing with:
- Safe plugin hot-reload that waits for active processing to complete
- Resource pool that detects and prevents nested acquisition deadlocks
- Correct backpressure propagation (not inverted) to all pipeline stages
- Proper plugin isolation including global singletons like logging
- Consistent window semantics across all modules (inclusive or exclusive, documented and enforced)
- Grace periods that are actually long enough under load

## Usage Example

```python
import asyncio
from pluginpipeline import (
    Pipeline, PluginLoader, Executor,
    ResourcePool, BackpressureManager,
    StreamProcessor, ConfigWatcher
)

async def main():
    pool = ResourcePool(max_size=10)
    backpressure = BackpressureManager()
    stream = StreamProcessor(backpressure)
    loader = PluginLoader()
    executor = Executor(pool)
    pipeline = Pipeline()

    plugin = loader.load_plugin("transform", "plugins.transform")
    pipeline.add_plugin(plugin)

    data = {"value": 100}
    result = pipeline.process(data)
    print(f"Result: {result}")

    watcher = ConfigWatcher(loader)
    watcher.check_and_reload("transform")

if __name__ == "__main__":
    asyncio.run(main())
```
