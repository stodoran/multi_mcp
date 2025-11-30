# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ConfigWorkflow is a configuration-driven workflow engine with a plugin system. It orchestrates multi-step workflows with state management, persistence, and parallel execution support.

## Architecture

### Core Components

**`engine.py`**: WorkflowEngine - Orchestrates workflow execution
- Creates and manages workflows with unique IDs
- Supports parallel execution via `multiprocessing.Pool`
- Handles caching and state persistence
- Integrates with Config and StateSerializer

**`state.py`**: Workflow state management
- `StateTransition` enum: PENDING → RUNNING → COMPLETED/FAILED
- `WorkflowState` dataclass: Tracks workflow progress and metadata
- State validation with defined transition rules

**`steps.py`**: Step definitions and execution
- `Step` class: Wraps functions with name and arguments
- `create_step()`: Factory for common operations (process, validate, transform)
- `create_step_safe()`: Picklable alternative using module-level functions

**`config.py`**: Multi-source configuration management
- Precedence: Environment variables > config file > defaults
- Supports JSON config files
- Environment variables use `WORKFLOW_` prefix
- Plugin registration on initialization

**`plugins.py`**: Plugin registry with singleton pattern
- `PluginRegistry`: Manages workflow plugins
- Default plugins: logging, monitoring, notification
- Thread-safe plugin registration and retrieval

**`serializer.py`**: State persistence
- JSON serialization for WorkflowState
- Pickle support for full workflow snapshots (state + steps)
- File-based storage in configurable directory

## Development Workflow

This is a library module without executable entry points or test files in the current directory. It would typically be:
- Imported by other Python projects
- Tested via pytest in a parent directory
- Configured via JSON files or environment variables

### Configuration Example

```json
{
  "max_workers": 4,
  "timeout": 30,
  "retry_attempts": 3,
  "enable_logging": true,
  "enable_monitoring": false,
  "log_level": "INFO"
}
```

### Environment Variables

```bash
WORKFLOW_MAX_WORKERS=8
WORKFLOW_TIMEOUT=60
WORKFLOW_ENABLE_LOGGING=true
```

