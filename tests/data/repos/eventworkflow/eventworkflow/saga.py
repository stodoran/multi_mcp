"""Saga implementation for distributed transactions."""

import asyncio
import contextvars
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .event_bus import EventBus

logger = logging.getLogger(__name__)

current_saga_id = contextvars.ContextVar('saga_id', default=None)


@dataclass
class SagaStep:
    """Represents a single step in a saga."""
    name: str
    action: Callable
    compensation: Callable | None = None
    args: tuple = ()
    kwargs: dict[str, Any] = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class Saga:
    """Saga for managing distributed transactions."""

    def __init__(self, saga_id: str, event_bus: EventBus):
        """Initialize saga."""
        self.saga_id = saga_id
        self.event_bus = event_bus
        self._steps: list[SagaStep] = []
        self._completed_steps: list[int] = []
        self._state_lock = asyncio.Lock()
        self._cancelled = False
        logger.info(f"Created saga {saga_id}")

    def add_step(self, step: SagaStep) -> None:
        """Add a step to the saga."""
        self._steps.append(step)

    async def execute(self) -> Any:
        """Execute all saga steps."""
        async with self._state_lock:
            step_tasks = []
            for i, step in enumerate(self._steps):
                task = asyncio.create_task(self._execute_step(i, step))
                step_tasks.append(task)

            results = await asyncio.gather(*step_tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Step {i} failed: {result}")
                    raise result
                self._completed_steps.append(i)

            return results

    async def _execute_step(self, index: int, step: SagaStep) -> Any:
        """Execute a single step."""
        logger.info(f"Executing step {step.name}")
        result = await step.action(*step.args, **step.kwargs)

        event_data = {"saga_id": self.saga_id, "step": step.name, "result": result}
        await self.event_bus.publish(f"step_completed:{step.name}", event_data)

        return result

    async def compensate(self) -> None:
        """Execute compensation for completed steps."""
        logger.info(f"Starting compensation for saga {self.saga_id}")

        for step_index in reversed(self._completed_steps):
            step = self._steps[step_index]
            if step.compensation:
                try:
                    await step.compensation(*step.args, **step.kwargs)
                    logger.info(f"Compensated step {step.name}")
                except Exception as e:
                    logger.error(f"Compensation failed for {step.name}: {e}")

    async def cancel(self) -> None:
        """Cancel the saga execution."""
        self._cancelled = True
        logger.info(f"Saga {self.saga_id} cancelled")

    def get_completed_steps(self) -> list[int]:
        """Get list of completed step indices."""
        return self._completed_steps.copy()
