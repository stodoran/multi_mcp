"""Comparison tool schema models."""

from src.schemas.base import MultiToolRequest, MultiToolResponse


class ComparisonRequest(MultiToolRequest):
    """Chat request for side-by-side model comparison."""

    pass  # Inherits models: list[str] from MultiToolRequest


class ComparisonResponse(MultiToolResponse):
    """Response with side-by-side comparison results."""

    pass  # Inherits results: list[ModelResponse] from MultiToolResponse
