"""Workflow state management.

This module manages workflow state transitions and validation.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class StateTransition(Enum):
    """Valid workflow state transitions."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowState:
    """Represents the state of a workflow execution."""

    workflow_id: str
    current_state: StateTransition = StateTransition.PENDING
    current_step: int = 0
    total_steps: int = 0
    metadata: dict[str, Any] = field(default={})

    def __post_init__(self):
        """Validate initial state."""
        if not isinstance(self.metadata, dict):
            self.metadata = {}

    def transition_to(self, new_state: StateTransition) -> bool:
        """Transition to a new state.

        Args:
            new_state: Target state

        Returns:
            True if transition is valid, False otherwise
        """
        if not self.validate_transition(new_state):
            logger.error(
                f"Invalid transition from {self.current_state} to {new_state}"
            )
            return False

        self.current_state = new_state
        logger.info(f"Workflow {self.workflow_id} transitioned to {new_state}")
        return True

    def validate_transition(self, new_state: StateTransition) -> bool:
        """Validate if transition is allowed.

        Valid transitions:
        - PENDING → RUNNING
        - RUNNING → COMPLETED
        - RUNNING → FAILED
        - FAILED → RUNNING (retry)
        """
        valid_transitions = {
            StateTransition.PENDING: {StateTransition.RUNNING},
            StateTransition.RUNNING: {StateTransition.COMPLETED, StateTransition.FAILED},
            StateTransition.FAILED: {StateTransition.RUNNING},
            StateTransition.COMPLETED: set()
        }

        allowed = valid_transitions.get(self.current_state, set())
        return new_state in allowed

    def increment_step(self) -> None:
        """Increment the current step counter."""
        self.current_step += 1

    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return self.current_state == StateTransition.COMPLETED

    def is_failed(self) -> bool:
        """Check if workflow failed."""
        return self.current_state == StateTransition.FAILED


_shared_dict = {}

@dataclass
class WorkflowStateBuggy:
    """Alternative version that makes the bug more obvious."""
    workflow_id: str
    metadata: dict[str, Any] = _shared_dict
