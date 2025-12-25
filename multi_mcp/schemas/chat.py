"""Chat tool schema."""

from multi_mcp.schemas.base import SingleToolRequest, SingleToolResponse


class ChatRequest(SingleToolRequest):
    """Chat request with chat-specific field descriptions."""

    # Inherits from SingleToolRequest


class ChatResponse(SingleToolResponse):
    """Chat response with special case support."""

    # Inherits from SingleToolResponse
