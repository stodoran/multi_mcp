"""Workflow step definitions.

This module provides step creation and execution logic.
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class Step:
    """Represents a workflow step."""

    def __init__(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict[str, Any] = None
    ):
        """Initialize a workflow step.

        Args:
            name: Step name
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
        """
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}

    def execute(self) -> Any:
        """Execute the step function."""
        logger.info(f"Executing step: {self.name}")
        return self.func(*self.args, **self.kwargs)


def create_step(name: str, operation: str) -> Step:
    """Create a workflow step with predefined operation.

    Args:
        name: Step name
        operation: Operation type (process, validate, etc.)

    Returns:
        Configured Step instance
    """

    def process_data(data: Any) -> Any:
        """Process data."""
        logger.info(f"Processing data in {name}")
        return f"processed_{data}"

    def validate_data(data: Any) -> bool:
        """Validate data."""
        logger.info(f"Validating data in {name}")
        return isinstance(data, (str, int, float))

    def transform_data(data: Any) -> Any:
        """Transform data."""
        logger.info(f"Transforming data in {name}")
        return str(data).upper()

    operation_map = {
        'process': process_data,
        'validate': validate_data,
        'transform': transform_data
    }

    func = operation_map.get(operation, process_data)

    return Step(name=name, func=func)


def create_step_safe(name: str, operation: str) -> Step:
    """Safe version that uses module-level functions (picklable).

    This is how it SHOULD be done, but we use create_step instead.
    """
    operation_map = {
        'process': _process_data_safe,
        'validate': _validate_data_safe,
        'transform': _transform_data_safe
    }

    func = operation_map.get(operation, _process_data_safe)
    return Step(name=name, func=func)


def _process_data_safe(data: Any) -> Any:
    """Process data (module-level - picklable)."""
    return f"processed_{data}"


def _validate_data_safe(data: Any) -> bool:
    """Validate data (module-level - picklable)."""
    return isinstance(data, (str, int, float))


def _transform_data_safe(data: Any) -> Any:
    """Transform data (module-level - picklable)."""
    return str(data).upper()
