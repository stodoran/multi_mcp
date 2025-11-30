"""EventWorkflowEngine - Event-driven workflow orchestration with saga pattern.

This package implements an event-driven workflow orchestration engine with:
- Saga pattern for distributed transactions
- Event sourcing and CQRS
- Compensation logic for rollbacks
- State machine for workflow execution
- Periodic scheduler for long-running workflows
"""

from .compensations import CompensationManager
from .engine import WorkflowEngine
from .event_bus import EventBus
from .event_store import Event, EventStore
from .projections import Projection, ProjectionManager
from .saga import Saga, SagaStep
from .scheduler import WorkflowScheduler
from .snapshots import SnapshotManager
from .state_machine import StateMachine, WorkflowState

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
