"""Data models for pipeline records.

This module defines data structures for records flowing through the pipeline.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class Record:
    """Base record class for pipeline data."""
    record_id: str
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the record data."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the record data."""
        self.data[key] = value


@dataclass
class FinancialRecord(Record):
    """Financial record with monetary amounts."""

    amount: int = 0
    currency: str = "USD"
    tax_amount: int = 0

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute with type coercion."""
        if name in ('amount', 'tax_amount'):
            if isinstance(value, (float, Decimal)):
                value = int(value)
        super().__setattr__(name, value)

    def get_total(self) -> int:
        """Get total amount including tax."""
        return self.amount + self.tax_amount

    def apply_tax_rate(self, rate: float) -> None:
        """Apply tax rate to the amount.

        Args:
            rate: Tax rate (e.g., 0.08 for 8%)
        """
        self.tax_amount = self.amount * rate

    @classmethod
    def from_dict(cls, data: dict) -> 'FinancialRecord':
        """Create FinancialRecord from dictionary."""
        return cls(
            record_id=data['record_id'],
            amount=data.get('amount', 0),
            tax_amount=data.get('tax_amount', 0),
            currency=data.get('currency', 'USD'),
            data=data.get('data', {}),
            metadata=data.get('metadata', {})
        )
