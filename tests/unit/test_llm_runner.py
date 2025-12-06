"""Unit tests for shared parallel executor."""

from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.base import ModelResponse, ModelResponseMetadata
from src.utils.context import set_request_context
from src.utils.llm_runner import execute_parallel, execute_single


@pytest.mark.asyncio
async def test_execute_parallel_all_success():
    """Test execute_parallel with all models succeeding."""
    # Set context for testing
    set_request_context(thread_id="test-thread")

    # Mock litellm_client.call_async
    call_count = [0]
    models_used = []

    async def mock_call_async(messages: list[dict], model: str | None = None, enable_web_search: bool = False):
        call_count[0] += 1
        models_used.append(model)
        return ModelResponse(
            content=f"Response from {model}",
            status="success",
            metadata=ModelResponseMetadata(model=model, prompt_tokens=100, completion_tokens=200, total_tokens=300, latency_ms=1000),
        )

    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Test prompt"},
    ]

    with patch("src.utils.llm_runner.litellm_client.call_async", side_effect=mock_call_async):
        results = await execute_parallel(
            models=["gpt-5-mini", "haiku"],
            messages=messages,
        )

    assert len(results) == 2
    assert all(r.status == "success" for r in results)
    assert call_count[0] == 2
    assert "gpt-5-mini" in models_used
    assert "haiku" in models_used
    assert all(r.metadata is not None for r in results)


@pytest.mark.asyncio
async def test_execute_parallel_partial_failure():
    """Test execute_parallel with some models failing."""
    set_request_context(thread_id="test-thread")

    call_count = [0]

    async def mock_call_async(messages: list[dict], model: str | None = None, enable_web_search: bool = False):
        call_count[0] += 1

        if call_count[0] == 1:
            # First model succeeds
            return ModelResponse(
                content="Success",
                status="success",
                metadata=ModelResponseMetadata(model=model, prompt_tokens=100, completion_tokens=200, total_tokens=300),
            )
        else:
            # Second model fails
            return ModelResponse(content="", status="error", error="Timeout error", metadata=ModelResponseMetadata(model=model))

    messages = [{"role": "user", "content": "Test prompt"}]

    with patch("src.utils.llm_runner.litellm_client.call_async", side_effect=mock_call_async):
        results = await execute_parallel(models=["gpt-5-mini", "haiku"], messages=messages)

    assert len(results) == 2
    assert results[0].status == "success"
    assert results[1].status == "error"
    assert results[1].error == "Timeout error"


@pytest.mark.asyncio
async def test_execute_parallel_uses_provided_messages():
    """Test execute_parallel uses exact messages provided."""
    set_request_context(thread_id="test-thread")

    received_messages = []

    async def mock_call_async(messages: list[dict], model: str | None = None, enable_web_search: bool = False):
        # Capture messages for verification
        received_messages.append(messages)
        return ModelResponse(content="Response", status="success", metadata=ModelResponseMetadata(model=model, total_tokens=100))

    messages = [{"role": "user", "content": "Test prompt"}]

    with patch("src.utils.llm_runner.litellm_client.call_async", side_effect=mock_call_async):
        results = await execute_parallel(models=["gpt-5-mini"], messages=messages)

    assert len(results) == 1
    assert results[0].status == "success"
    # Verify exact messages were passed
    assert len(received_messages) == 1
    assert received_messages[0] == messages


# ============================================================================
# Tests for execute_single()
# ============================================================================


@pytest.mark.asyncio
async def test_execute_single_success_with_artifacts():
    """Test execute_single with successful response and artifact saving."""
    messages = [{"role": "user", "content": "Test prompt"}]

    mock_response = ModelResponse(
        content="Test response",
        status="success",
        metadata=ModelResponseMetadata(
            model="gpt-5-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=100,
        ),
    )

    with patch("src.utils.llm_runner.litellm_client.call_async", new_callable=AsyncMock) as mock_call:
        with patch("src.utils.artifacts.save_tool_artifacts", new_callable=AsyncMock) as mock_save_artifacts:
            mock_call.return_value = mock_response
            mock_save_artifacts.return_value = ["/test/artifact1.md", "/test/artifact2.json"]

            result = await execute_single(
                model="gpt-5-mini",
                messages=messages,
            )

    assert result.status == "success"
    assert result.content == "Test response"
    assert result.metadata.artifacts == ["/test/artifact1.md", "/test/artifact2.json"]
    assert result.metadata.total_tokens == 15

    # Verify litellm_client.call_async was called
    mock_call.assert_called_once()
    assert mock_call.call_args.kwargs["model"] == "gpt-5-mini"
    assert mock_call.call_args.kwargs["messages"] == messages

    # Verify save_tool_artifacts was called with only response parameter
    # All other parameters (workflow, name, step_number, thread_id, base_path) are obtained from context
    mock_save_artifacts.assert_called_once_with(response=mock_response)


@pytest.mark.asyncio
async def test_execute_single_with_messages():
    """Test execute_single with pre-built messages."""
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "User message"},
    ]

    mock_response = ModelResponse(
        content="Test response",
        status="success",
        metadata=ModelResponseMetadata(
            model="gpt-5-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=100,
        ),
    )

    with patch("src.utils.llm_runner.litellm_client.call_async", new_callable=AsyncMock) as mock_call:
        with patch("src.utils.artifacts.save_tool_artifacts", new_callable=AsyncMock) as mock_save_artifacts:
            mock_call.return_value = mock_response
            mock_save_artifacts.return_value = ["/test/artifact.md"]

            result = await execute_single(
                model="gpt-5-mini",
                messages=messages,
            )

    assert result.status == "success"
    mock_call.assert_called_once()
    assert mock_call.call_args.kwargs["messages"] == messages


@pytest.mark.asyncio
async def test_execute_single_error_no_artifacts():
    """Test that artifacts are not saved when LLM call fails."""
    messages = [{"role": "user", "content": "Test prompt"}]

    error_response = ModelResponse(
        content="",
        status="error",
        error="Test error",
        metadata=ModelResponseMetadata(model="gpt-5-mini"),
    )

    with patch("src.utils.llm_runner.litellm_client.call_async", new_callable=AsyncMock) as mock_call:
        with patch("src.utils.artifacts.save_tool_artifacts", new_callable=AsyncMock) as mock_save_artifacts:
            mock_call.return_value = error_response

            result = await execute_single(
                model="gpt-5-mini",
                messages=messages,
            )

    assert result.status == "error"
    assert result.error == "Test error"

    # Artifacts should not be saved for error responses
    mock_save_artifacts.assert_not_called()


@pytest.mark.asyncio
async def test_execute_single_no_artifacts_returned():
    """Test execute_single when save_tool_artifacts returns None."""
    messages = [{"role": "user", "content": "Test prompt"}]

    mock_response = ModelResponse(
        content="Test response",
        status="success",
        metadata=ModelResponseMetadata(
            model="gpt-5-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=100,
        ),
    )

    with patch("src.utils.llm_runner.litellm_client.call_async", new_callable=AsyncMock) as mock_call:
        with patch("src.utils.artifacts.save_tool_artifacts", new_callable=AsyncMock) as mock_save_artifacts:
            mock_call.return_value = mock_response
            mock_save_artifacts.return_value = None

            result = await execute_single(
                model="gpt-5-mini",
                messages=messages,
            )

    assert result.status == "success"
    assert result.content == "Test response"
    # Metadata should not have artifacts field when None returned
    assert not hasattr(result.metadata, "artifacts") or result.metadata.artifacts is None


@pytest.mark.asyncio
async def test_execute_single_preserves_issues_in_content():
    """Test that issues embedded in JSON response content are saved in artifacts."""
    messages = [{"role": "user", "content": "Review the code"}]

    response_with_issues = ModelResponse(
        content='{"status": "review_complete", "issues_found": [{"severity": "high", "description": "SQL injection"}]}',
        status="success",
        metadata=ModelResponseMetadata(
            model="gpt-5-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=100,
        ),
    )

    with patch("src.utils.llm_runner.litellm_client.call_async", new_callable=AsyncMock) as mock_call:
        with patch("src.utils.artifacts.save_tool_artifacts", new_callable=AsyncMock) as mock_save_artifacts:
            mock_call.return_value = response_with_issues
            mock_save_artifacts.return_value = ["/test/review.json"]

            result = await execute_single(
                model="gpt-5-mini",
                messages=messages,
            )

    assert result.status == "success"
    assert "issues_found" in result.content
    assert "SQL injection" in result.content

    # Verify the full content (including issues) was passed to save_tool_artifacts
    save_call_args = mock_save_artifacts.call_args
    saved_response = save_call_args.kwargs["response"]
    assert "issues_found" in saved_response.content
