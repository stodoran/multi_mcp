"""Workflow state serialization and persistence.

This module handles saving and loading workflow state to/from disk.
"""

import json
import logging
import pickle
from pathlib import Path

from .state import WorkflowState

logger = logging.getLogger(__name__)


class StateSerializer:
    """Serializes and deserializes workflow state."""

    def __init__(self, state_dir: str = "./workflow_states"):
        """Initialize serializer.

        Args:
            state_dir: Directory for state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, workflow_id: str, state: WorkflowState, workflow_steps: list = None) -> bool:
        """Save workflow state to disk.

        Args:
            workflow_id: Workflow identifier
            state: Workflow state to save
            workflow_steps: Optional list of Step objects

        Returns:
            True if save succeeded, False otherwise
        """
        state_file = self.state_dir / f"{workflow_id}.json"
        pickle_file = self.state_dir / f"{workflow_id}.pkl"

        try:
            state_dict = {
                'workflow_id': state.workflow_id,
                'current_state': state.current_state.value,
                'current_step': state.current_step,
                'total_steps': state.total_steps,
                'metadata': state.metadata
            }

            with open(state_file, 'w') as f:
                json.dump(state_dict, f, indent=2)

            if workflow_steps:
                with open(pickle_file, 'wb') as f:
                    pickle.dump({
                        'state': state,
                        'steps': workflow_steps
                    }, f)

            logger.info(f"Saved state for workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save state for {workflow_id}: {e}")
            return False

    def load_state(self, workflow_id: str) -> WorkflowState | None:
        """Load workflow state from disk.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Loaded WorkflowState or None if not found
        """
        state_file = self.state_dir / f"{workflow_id}.json"

        if not state_file.exists():
            logger.warning(f"State file not found for {workflow_id}")
            return None

        try:
            with open(state_file) as f:
                data = json.load(f)

            from .state import StateTransition
            state = WorkflowState(
                workflow_id=data['workflow_id'],
                current_step=data['current_step'],
                total_steps=data['total_steps']
            )
            state.current_state = StateTransition(data['current_state'])
            state.metadata = data['metadata']

            logger.info(f"Loaded state for workflow {workflow_id}")
            return state

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error loading state for {workflow_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load state for {workflow_id}: {e}")
            return None

    def delete_state(self, workflow_id: str) -> bool:
        """Delete workflow state files.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if deletion succeeded
        """
        state_file = self.state_dir / f"{workflow_id}.json"
        pickle_file = self.state_dir / f"{workflow_id}.pkl"

        success = True
        for file in [state_file, pickle_file]:
            if file.exists():
                try:
                    file.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete {file}: {e}")
                    success = False

        return success
