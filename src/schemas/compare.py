"""Compare tool schema models."""

from src.schemas.base import MultiToolRequest, MultiToolResponse


class CompareRequest(MultiToolRequest):
    """Chat request for side-by-side model compare."""

    pass  # Inherits models: list[str] from MultiToolRequest


class CompareResponse(MultiToolResponse):
    """Response with side-by-side compare results."""

    pass  # Inherits results: list[ModelResponse] from MultiToolResponse
