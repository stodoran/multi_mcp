"""EventWorkflowEngine - Event-driven workflow orchestration with saga pattern.

This package implements an event-driven workflow orchestration engine with:
- Saga pattern for distributed transactions
- Event sourcing and CQRS
- Compensation logic for rollbacks
- State machine for workflow execution
- Periodic scheduler for long-running workflows
"""

from .engine import WorkflowEngine
from .saga import Saga, SagaStep
from .event_store import EventStore, Event
from .projections import ProjectionManager, Projection
from .compensations import CompensationManager
from .state_machine import StateMachine, WorkflowState
from .scheduler import WorkflowScheduler
from .event_bus import EventBus
from .snapshots import SnapshotManager

__version__ = "1.0.0"
__all__ = [
    "WorkflowEngine",
    "Saga",
    "SagaStep",
    "EventStore",
    "Event",
    "ProjectionManager",
    "Projection",
    "CompensationManager",
    "StateMachine",
    "WorkflowState",
    "WorkflowScheduler",
    "EventBus",
    "SnapshotManager",
]
