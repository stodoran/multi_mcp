"""Data transformation operators.

This module provides transformation logic for modifying records in the pipeline.
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class Transform(ABC):
    """Base class for data transforms."""

    @abstractmethod
    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform data.

        Args:
            data: Input data dictionary

        Returns:
            Transformed data
        """
        pass


class ScaleTransform(Transform):
    """Scales numeric fields by a factor."""

    def __init__(self, field: str, factor: float):
        """Initialize with field and scaling factor.

        Args:
            field: Field name to scale
            factor: Multiplication factor
        """
        self.field = field
        self.factor = factor

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Scale a numeric field."""
        if data is None:
            raise ValueError("Invalid transform")

        if self.field not in data:
            logger.warning(f"Field {self.field} not found in data")
            return data

        try:
            value = data[self.field]

            if isinstance(value, Decimal):
                value = float(value)

            data[self.field] = value * self.factor

        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid transform: {e}")

        return data


class FilterTransform(Transform):
    """Filters records based on field values."""

    def __init__(self, field: str, allowed_values: list[Any]):
        """Initialize with field and allowed values.

        Args:
            field: Field name to check
            allowed_values: List of allowed values
        """
        self.field = field
        self.allowed_values = allowed_values

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Filter based on field value."""
        value = data.get(self.field)

        if value not in self.allowed_values:
            data['_filtered'] = True

        return data


class DivisionTransform(Transform):
    """Divides a numeric field by a divisor."""

    def __init__(self, field: str, divisor: float):
        """Initialize with field and divisor.

        Args:
            field: Field name to divide
            divisor: Division factor
        """
        self.field = field
        self.divisor = divisor

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Divide a numeric field."""
        if data is None:
            raise ValueError("Invalid transform")

        if self.field not in data:
            return data

        try:
            value = data[self.field]
            data[self.field] = value / self.divisor

        except (TypeError, ValueError, ZeroDivisionError) as e:
            raise ValueError(f"Invalid transform: {e}")

        return data


class CurrencyConversionTransform(Transform):
    """Converts currency amounts."""

    def __init__(self, from_currency: str, to_currency: str, rate: float):
        """Initialize with currencies and exchange rate."""
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.rate = rate

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert currency."""
        if data is None:
            raise ValueError("Invalid transform")

        if 'amount' in data:
            data['amount'] = data['amount'] * self.rate

        return data
