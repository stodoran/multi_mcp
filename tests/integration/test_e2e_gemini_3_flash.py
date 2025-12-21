"""End-to-end integration tests for Gemini 3 Flash model."""

import os
import uuid

import pytest

from multi_mcp.tools.chat import chat_impl

pytestmark = pytest.mark.skipif(not os.getenv("RUN_E2E"), reason="Integration tests require RUN_E2E=1 and API keys")


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_gemini_3_flash_basic():
    """Verify Gemini 3 Flash responds correctly."""
    thread_id = str(uuid.uuid4())

    response = await chat_impl(
        name="Gemini 3 Flash test",
        content="What is 2 + 2? Answer in one word.",
        step_number=1,
        next_action="stop",
        base_path="/tmp",
        model="gemini-3-flash",
        thread_id=thread_id,
    )

    assert response["status"] in ["success", "in_progress"]
    assert response["thread_id"] == thread_id
    assert "content" in response
    assert len(response["content"]) > 0

    content = response["content"].lower()
    assert "4" in content or "four" in content, f"Expected '4' or 'four', got: {content}"

    print(f"\n✓ Gemini 3 Flash test passed: {response['content'][:100]}")
