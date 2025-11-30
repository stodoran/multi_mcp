"""Workflow engine core implementation."""

import asyncio
import contextvars
import logging
from typing import Any

from .saga import Saga
from .state_machine import StateMachine

logger = logging.getLogger(__name__)

current_saga_id = contextvars.ContextVar('saga_id', default=None)


class WorkflowEngine:
    """Core workflow engine for executing sagas."""

    def __init__(self):
        """Initialize workflow engine."""
        self._sagas: dict[str, Saga] = {}
        self._state_machines: dict[str, StateMachine] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        logger.info("Initialized workflow engine")

    def register_saga(self, saga: Saga) -> None:
        """Register a saga with the engine."""
        self._sagas[saga.saga_id] = saga
        self._state_machines[saga.saga_id] = StateMachine(saga.saga_id)
        self._locks[saga.saga_id] = asyncio.Lock()
        logger.info(f"Registered saga {saga.saga_id}")

    async def execute_saga(self, saga_id: str, timeout: float = 60.0) -> Any:
        """Execute a saga with timeout.

        Sets context for saga execution.
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            raise ValueError(f"Saga {saga_id} not found")

        current_saga_id.set(saga_id)

        async with self._locks[saga_id]:
            try:
                result = await asyncio.wait_for(saga.execute(), timeout=timeout)
                return result
            except asyncio.CancelledError:
                logger.warning(f"Saga {saga_id} cancelled, starting compensation")
                await saga.compensate()
                raise
            except Exception as e:
                logger.error(f"Saga {saga_id} failed: {e}")
                await saga.compensate()
                raise
            finally:
                current_saga_id.set(None)

    async def cancel_saga(self, saga_id: str) -> None:
        """Cancel a running saga."""
        saga = self._sagas.get(saga_id)
        if saga:
            await saga.cancel()

    def get_saga_status(self, saga_id: str) -> dict[str, Any]:
        """Get saga execution status."""
        saga = self._sagas.get(saga_id)
        state_machine = self._state_machines.get(saga_id)

        if not saga or not state_machine:
            return {"status": "not_found"}

        return {
            "saga_id": saga_id,
            "state": state_machine.current_state.value,
            "steps_completed": saga.get_completed_steps(),
        }
