# ConfigWorkflow

## Bug Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 2 |
| 🟡 Medium | 2 |
| 🟢 Low | 1 |
| **Total** | **7** |

## Description

ConfigWorkflow is a configuration-driven workflow engine that executes multi-step workflows with plugin support, state management, and persistence. The system provides a flexible workflow execution engine, configuration loading from multiple sources with precedence rules, plugin registry for extensibility, state machine with defined transitions, step execution with parallel processing support, and state serialization for workflow persistence.

The architecture enables users to define workflows as sequences of steps, configure behavior through environment variables and files, extend functionality through plugins, track workflow state transitions, execute steps in parallel for performance, persist and resume workflows across restarts, and validate workflow execution according to state machine rules.

The system is designed for batch processing pipelines, configuration-driven automation tasks, extensible workflow systems, and long-running jobs that need state persistence.

## Directory Structure

```
repo4/
  README.md
  configworkflow/
    __init__.py           # Package initialization
    engine.py             # Workflow execution engine
    config.py             # Multi-source configuration loader
    steps.py              # Workflow step definitions and factory
    plugins.py            # Plugin registry and management
    state.py              # State machine and transitions
    serializer.py         # State persistence to disk
```

## Component Overview

- **engine.py**: Orchestrates workflow execution with support for parallel step processing via multiprocessing. Manages workflow state, integrates configuration settings, handles scheduled execution times, and coordinates with the serializer for state persistence.

- **config.py**: Loads configuration from multiple sources (defaults, files, environment variables) with defined precedence rules. Manages plugin enablement and provides configuration access to other components.

- **steps.py**: Provides Step class and factory functions for creating workflow steps. Defines step execution logic and supports different operation types like processing, validation, and transformation.

- **plugins.py**: Implements singleton plugin registry for workflow extensions. Manages plugin registration and retrieval. Provides default plugins for logging, monitoring, and notifications.

- **state.py**: Defines WorkflowState dataclass and StateTransition enum. Implements state machine with validation rules for transitions between pending, running, completed, and failed states.

- **serializer.py**: Handles serialization of workflow state to JSON and pickle formats for persistence. Manages state file storage and retrieval for workflow resume capabilities.

## Known Issues

⚠️ **This repository contains intentional bugs for testing bug detection systems.**

### 🔴 Critical Issues (2 total)

1. **Circular import with side effects during module initialization**: The config module imports from plugins to register default plugins during initialization. The plugins module imports from config to check feature flags for plugin validation. This circular dependency causes initialization errors where one module tries to use the other before it's fully initialized, resulting in AttributeError for None references or partially constructed objects when registration code runs.

2. **Multiprocessing pickling failure with nested function closures**: The step factory creates workflow step functions as nested functions defined inside the factory method scope. The engine passes these steps to multiprocessing.Pool for parallel execution across processes. The serializer attempts to pickle workflow state including these step functions for persistence. Pickle cannot serialize nested functions or closures, causing PicklingError exceptions that prevent workflow state from being saved or distributed to worker processes.

### 🟠 High Issues (2 total)

3. **Configuration precedence bypass allowing inconsistent overrides**: Configuration implements a documented precedence system where environment variables override file settings which override defaults. However, the engine reads some configuration values directly from the file instead of using the configuration getter method. This bypasses the precedence system, causing environment variable overrides to work for some settings but not others, leading to configuration drift between development and production environments.

4. **Mutable default argument sharing state across workflow instances**: The WorkflowState dataclass defines a metadata field with a mutable dictionary as the default value. Python dataclasses share a single instance of mutable defaults across all object instances. When the engine creates multiple workflows, they all share the same metadata dictionary. Updates to one workflow's metadata leak into all other workflows, causing state corruption and data mixing between independent workflow executions.

### 🟡 Medium Issues (2 total)

5. **Timezone-naive datetime comparison causing runtime TypeError**: The configuration module parses scheduled execution times from ISO format strings into naive datetime objects without timezone information. The engine compares these scheduled times to the current time using datetime.now() which may return timezone-aware datetimes depending on system configuration. When comparing naive and aware datetime objects, Python raises TypeError. This causes workflow scheduling to crash unpredictably based on deployment environment timezone settings.

6. **State transition protocol violations bypassing validation logic**: The state module defines a strict state machine requiring workflows to transition through defined states (pending to running to completed). The state transition validation method enforces these rules. However, the engine directly assigns state values using attribute assignment instead of calling the validation method. When using cached results, the engine transitions directly from pending to completed, violating the state machine protocol without detection, causing invalid state graphs.

### 🟢 Low Issues (1 total)

7. **Encoding assumption mismatch between writer and reader**: The serializer writes workflow state to JSON files without explicitly specifying encoding, relying on Python's platform-default encoding. The state loading code assumes UTF-8 encoding when reading files. On Windows systems where the default encoding is cp1252 rather than UTF-8, workflow state containing unicode characters fails to load after restart, causing workflow resume failures.

## Expected Behavior

The system should load configuration from all sources with proper precedence enforcement, avoid circular import dependencies through careful module organization, serialize workflow state including all necessary components for parallel execution and persistence, maintain separate state for each workflow instance, handle timezone-aware datetimes consistently, enforce state machine transition rules, and use consistent encoding for all file operations.

## Usage Example

```python
import os
from configworkflow import WorkflowEngine, Step, create_step, WorkflowState, StateSerializer
from configworkflow.config import Config

# Set environment configuration
os.environ['WORKFLOW_MAX_WORKERS'] = '4'
os.environ['WORKFLOW_TIMEOUT'] = '60'

# Create configuration
config = Config(config_file="./workflow_config.json")

# Create workflow engine
engine = WorkflowEngine(config=config)

# Define workflow steps
steps = [
    create_step("step1", "process"),
    create_step("step2", "validate"),
    create_step("step3", "transform")
]

# Create and execute workflow
state = engine.create_workflow(
    workflow_id="batch_job_001",
    steps=steps,
    scheduled_time="2024-01-15T10:00:00"
)

print(f"Created workflow: {state.workflow_id}")
print(f"Total steps: {state.total_steps}")

# Execute workflow
success = engine.execute_workflow(
    workflow_id="batch_job_001",
    steps=steps,
    use_cache=False
)

if success:
    print("Workflow completed successfully")
    final_state = engine.get_workflow_state("batch_job_001")
    print(f"Final state: {final_state.current_state}")
else:
    print("Workflow execution failed")

# Workflow state is automatically persisted and can be loaded
# on restart using:
# loaded_state = engine.load_workflow("batch_job_001")
```
