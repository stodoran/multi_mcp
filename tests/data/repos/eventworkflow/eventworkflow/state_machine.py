"""State machine for workflow state management."""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"


class StateMachine:
    """State machine for workflow execution."""

    def __init__(self, workflow_id: str):
        """Initialize state machine."""
        self.workflow_id = workflow_id
        self.current_state = WorkflowState.PENDING
        logger.info(f"Initialized state machine for {workflow_id}")

    def transition(self, new_state: WorkflowState) -> bool:
        """Transition to a new state."""
        if self._is_valid_transition(new_state):
            old_state = self.current_state
            self.current_state = new_state
            logger.info(f"State transition: {old_state.value} -> {new_state.value}")
            return True

        logger.error(f"Invalid transition: {self.current_state.value} -> {new_state.value}")
        return False

    def _is_valid_transition(self, new_state: WorkflowState) -> bool:
        """Check if transition is valid."""
        valid_transitions = {
            WorkflowState.PENDING: {WorkflowState.RUNNING},
            WorkflowState.RUNNING: {WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.COMPENSATING},
            WorkflowState.FAILED: {WorkflowState.COMPENSATING, WorkflowState.RUNNING},
            WorkflowState.COMPENSATING: {WorkflowState.FAILED, WorkflowState.COMPLETED},
            WorkflowState.COMPLETED: {WorkflowState.RUNNING},
        }

        return new_state in valid_transitions.get(self.current_state, set())
