"""Debate tool schema models."""

from pydantic import Field

from src.schemas.base import ModelResponse, MultiToolRequest, MultiToolResponse


class DebateRequest(MultiToolRequest):
    """Debate request - runs models in two steps: independent answers + debate."""

    pass  # Inherits models: list[str] from MultiToolRequest


class DebateResponse(MultiToolResponse):
    """Debate response with Step 1 (results) and Step 2 (step2_results)."""

    step2_results: list[ModelResponse] = Field(..., description="Step 2 debate responses where each model critiques Step 1 answers")
