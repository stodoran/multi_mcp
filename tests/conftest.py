"""Pytest configuration for multi_mcp tests."""

import pytest


@pytest.fixture(autouse=True)
async def clear_conversation_store():
    """Clear conversation store between tests to prevent state leakage."""
    yield  # Run the test first

    # Clear the global store after each test
    from src.memory.store import _threads

    _threads.clear()
