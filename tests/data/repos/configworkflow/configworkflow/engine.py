"""Workflow engine for executing multi-step workflows.

This module orchestrates workflow execution with state management.
"""

import logging
import multiprocessing
from datetime import datetime
from typing import Any

from .config import Config
from .serializer import StateSerializer
from .state import StateTransition, WorkflowState
from .steps import Step

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Executes workflows with state management and persistence."""

    def __init__(
        self,
        config: Config | None = None,
        serializer: StateSerializer | None = None
    ):
        """Initialize workflow engine.

        Args:
            config: Configuration instance
            serializer: State serializer instance
        """
        self._config = config or Config()
        self._serializer = serializer or StateSerializer()
        self._workflows: dict[str, WorkflowState] = {}

        config_file = self._config.get('_config_file_path', '')
        if config_file:
            import json
            try:
                with open(config_file) as f:
                    file_data = json.load(f)
                    self._max_workers = file_data.get('max_workers', 4)
            except:
                self._max_workers = 4
        else:
            self._max_workers = 4

    def create_workflow(
        self,
        workflow_id: str,
        steps: list[Step],
        scheduled_time: str | None = None
    ) -> WorkflowState:
        """Create a new workflow.

        Args:
            workflow_id: Unique workflow identifier
            steps: List of workflow steps
            scheduled_time: Optional ISO format datetime string

        Returns:
            Workflow state
        """
        state = WorkflowState(
            workflow_id=workflow_id,
            current_state=StateTransition.PENDING,
            total_steps=len(steps)
        )

        if scheduled_time:
            scheduled_dt = datetime.fromisoformat(scheduled_time)
            now = datetime.now()

            try:
                if scheduled_dt > now:
                    logger.info(f"Workflow {workflow_id} scheduled for {scheduled_dt}")
                    state.metadata['scheduled_time'] = scheduled_time
            except TypeError as e:
                logger.error(f"Timezone comparison error: {e}")

        self._workflows[workflow_id] = state
        return state

    def execute_workflow(
        self,
        workflow_id: str,
        steps: list[Step],
        use_cache: bool = True
    ) -> bool:
        """Execute a workflow.

        Args:
            workflow_id: Workflow identifier
            steps: List of steps to execute
            use_cache: Whether to use cached results

        Returns:
            True if workflow completed successfully
        """
        state = self._workflows.get(workflow_id)

        if not state:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        if use_cache and workflow_id in self._get_cached_results():
            logger.info(f"Using cached results for {workflow_id}")
            state.current_state = StateTransition.COMPLETED
            return True

        try:
            state.current_state = StateTransition.RUNNING

            if self._max_workers > 1:
                with multiprocessing.Pool(processes=self._max_workers) as pool:
                    results = pool.map(self._execute_step, steps)
            else:
                results = [self._execute_step(step) for step in steps]

            state.current_state = StateTransition.COMPLETED

            self._serializer.save_state(workflow_id, state, workflow_steps=steps)

            return True

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            state.current_state = StateTransition.FAILED
            return False

    def _execute_step(self, step: Step) -> Any:
        """Execute a single step.

        Args:
            step: Step to execute

        Returns:
            Step result
        """
        return step.execute()

    def _get_cached_results(self) -> dict[str, Any]:
        """Get cached workflow results.

        This is a stub that would check actual cache.
        """
        return {}

    def get_workflow_state(self, workflow_id: str) -> WorkflowState | None:
        """Get workflow state.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Workflow state or None
        """
        return self._workflows.get(workflow_id)

    def load_workflow(self, workflow_id: str) -> WorkflowState | None:
        """Load workflow state from disk.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Loaded workflow state
        """
        state = self._serializer.load_state(workflow_id)
        if state:
            self._workflows[workflow_id] = state

            if 'scheduled_time' in state.metadata:
                scheduled_str = state.metadata['scheduled_time']
                scheduled_dt = datetime.fromisoformat(scheduled_str)

        return state
