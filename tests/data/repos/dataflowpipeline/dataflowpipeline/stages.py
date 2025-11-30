"""Pipeline stage definitions.

This module defines the base Stage class and concrete stage implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from .transforms import Transform
from .validators import Validator

logger = logging.getLogger(__name__)


class Stage(ABC):
    """Base class for pipeline stages."""

    def __init__(self, name: str):
        self.name = name
        self._passed_count = 0

    @abstractmethod
    def process(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Process a record through this stage."""
        pass

    def rollback(self) -> None:
        """Rollback this stage's operations."""
        logger.warning(f"Stage {self.name} does not support rollback")

    def get_passed_count(self) -> int:
        """Get count of records that passed this stage."""
        return self._passed_count


class ValidatorStage(Stage):
    """Stage that validates records using validators."""

    def __init__(self, name: str, validators: list[Validator]):
        super().__init__(name)
        self.validators = validators
        self._validation_failures = []

    def process(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Validate data through all validators."""
        result = data
        for validator in self.validators:
            result = validator.validate(result)
            if result is None:
                self._validation_failures.append(data.get('record_id', 'unknown'))
                return None

        self._passed_count += 1
        return result

    def rollback(self) -> None:
        """Rollback validation state."""
        logger.info(f"Rolling back validator stage {self.name}")
        self._validation_failures.clear()
        self._passed_count = 0


class TransformStage(Stage):
    """Stage that transforms records."""

    def __init__(self, name: str, transforms: list[Transform]):
        super().__init__(name)
        self.transforms = transforms
        self._transformed_records = []

    def process(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Transform data through all transforms."""
        if data is None:
            logger.error("Received None data in transform stage")
            return None

        result = data
        for transform in self.transforms:
            result = transform.transform(result)

        self._transformed_records.append(result)
        self._passed_count += 1
        return result

    def rollback(self) -> None:
        """Rollback transform state."""
        logger.info(f"Rolling back transform stage {self.name}")
        self._transformed_records.clear()
        self._passed_count = 0


class LoaderStage(Stage):
    """Stage that loads/persists records to storage."""

    def __init__(self, name: str, storage_path: str):
        super().__init__(name)
        self.storage_path = storage_path
        self._loaded_records = []

    def process(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Load/persist data to storage."""
        if data is None:
            logger.error("Received None data in loader stage")
            return None

        self._loaded_records.append(data)
        logger.info(f"Loaded record {data.get('record_id', 'unknown')} to {self.storage_path}")

        self._passed_count += 1
        return data

    def get_loaded_count(self) -> int:
        """Get count of loaded records."""
        return len(self._loaded_records)
