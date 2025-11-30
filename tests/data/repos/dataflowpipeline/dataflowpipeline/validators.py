"""Data validators for pipeline stages.

This module provides validation logic for data records.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class Validator(ABC):
    """Base class for data validators."""

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Validate data and return it if valid.

        Returns:
            The data dict if valid, None if invalid
        """
        pass


class TypeValidator(Validator):
    """Validates that required fields have correct types."""

    def __init__(self, required_fields: dict[str, type]):
        """Initialize with required field types.

        Args:
            required_fields: Dict mapping field names to expected types
        """
        self.required_fields = required_fields

    def validate(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Validate field types.

        Returns:
            Data if valid, None if validation fails
        """
        for field, expected_type in self.required_fields.items():
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return None

            if not isinstance(data[field], expected_type):
                logger.error(
                    f"Field {field} has type {type(data[field])}, "
                    f"expected {expected_type}"
                )
                return None

        return data


class RangeValidator(Validator):
    """Validates that numeric fields are within specified ranges."""

    def __init__(self, field: str, min_val: float, max_val: float):
        """Initialize with field and range.

        Args:
            field: Field name to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
        """
        self.field = field
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Validate field is in range.

        Returns:
            Data if valid, None if validation fails
        """
        if self.field not in data:
            logger.error(f"Field {self.field} not found")
            return None

        value = data[self.field]

        try:
            if not (self.min_val <= value <= self.max_val):
                logger.error(
                    f"Field {self.field} value {value} outside range "
                    f"[{self.min_val}, {self.max_val}]"
                )
                return None
        except TypeError as e:
            logger.error(f"Range validation failed for {self.field}: {e}")
            return None

        return data


class SchemaValidator(Validator):
    """Validates record schema version."""

    def __init__(self, required_version: int = None):
        """Initialize with optional required version."""
        self.required_version = required_version

    def validate(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Validate schema version."""
        version = data.get('_schema_version', 1)

        if self.required_version and version != self.required_version:
            logger.warning(
                f"Schema version {version}, expected {self.required_version}"
            )

        return data
