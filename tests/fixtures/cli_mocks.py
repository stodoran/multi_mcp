"""Reusable CLI mock fixtures for testing.

These fixtures allow testing CLI integration logic without actually
executing CLI subprocesses. This makes tests:
- Fast (no subprocess overhead)
- Reliable (no external dependencies)
- Deterministic (no API calls)

Usage:
    @pytest.mark.asyncio
    async def test_something(mock_claude_cli):
        mock_claude_cli(response_text="Hello world")
        # Your test code...
"""

from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_claude_cli(mocker):
    """Mock Claude CLI subprocess execution.

    Args:
        response_text: Text content to return as CLI response
        exit_code: Exit code (0 = success, non-zero = error)
        stderr: Optional stderr output
        is_error: If True, sets is_error flag in JSON response

    Returns:
        Mock process object

    Example:
        def test_claude_success(mock_claude_cli):
            mock_claude_cli(response_text="The answer is 42")
            result = await client.call_async(model="claude-cli", ...)
            assert result.status == "success"
    """

    def _mock(response_text="Success", exit_code=0, stderr="", is_error=False):
        # Mock which() to indicate CLI is installed
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/claude")

        # Create mock process
        mock_proc = Mock()
        mock_proc.returncode = exit_code

        # Build response JSON based on Claude CLI format
        # Format: {"result": "content", "is_error": bool}
        if exit_code == 0 and not is_error:
            stdout = f'{{"result": "{response_text}", "is_error": false}}'
        else:
            stdout = f'{{"result": "{response_text}", "is_error": true}}'

        mock_proc.communicate = AsyncMock(return_value=(stdout.encode("utf-8"), stderr.encode("utf-8")))

        # Patch subprocess creation
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        return mock_proc

    return _mock


@pytest.fixture
def mock_gemini_cli(mocker):
    """Mock Gemini CLI subprocess execution.

    Args:
        response_text: Text content to return as CLI response
        exit_code: Exit code (0 = success, non-zero = error)
        stderr: Optional stderr output

    Returns:
        Mock process object

    Example:
        def test_gemini_success(mock_gemini_cli):
            mock_gemini_cli(response_text="The answer is 42")
            result = await client.call_async(model="gemini-cli", ...)
            assert result.status == "success"
    """

    def _mock(response_text="Success", exit_code=0, stderr=""):
        # Mock which() to indicate CLI is installed
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/gemini")

        # Create mock process
        mock_proc = Mock()
        mock_proc.returncode = exit_code

        # Build response JSON based on Gemini CLI format
        # Format: {"response": "content"}
        if exit_code == 0:
            stdout = f'{{"response": "{response_text}"}}'
        else:
            stdout = ""

        mock_proc.communicate = AsyncMock(return_value=(stdout.encode("utf-8"), stderr.encode("utf-8")))

        # Patch subprocess creation
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        return mock_proc

    return _mock


@pytest.fixture
def mock_codex_cli(mocker):
    """Mock Codex CLI subprocess execution.

    Args:
        response_text: Text content to return as CLI response
        exit_code: Exit code (0 = success, non-zero = error)
        stderr: Optional stderr output

    Returns:
        Mock process object

    Example:
        def test_codex_success(mock_codex_cli):
            mock_codex_cli(response_text="The answer is 42")
            result = await client.call_async(model="codex-cli", ...)
            assert result.status == "success"
    """

    def _mock(response_text="Success", exit_code=0, stderr=""):
        # Mock which() to indicate CLI is installed
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/codex")

        # Create mock process
        mock_proc = Mock()
        mock_proc.returncode = exit_code

        # Build response JSONL based on Codex CLI format
        # Format: Multiple JSON objects, one per line
        # {"type": "text", "text": "content"}
        # {"type": "item.completed", "item": {"type": "agent_message", "text": "content"}}
        if exit_code == 0:
            stdout = (
                f'{{"type": "text", "text": "{response_text}"}}\n'
                f'{{"type": "item.completed", "item": {{"type": "agent_message", "text": "Done"}}}}'
            )
        else:
            stdout = ""

        mock_proc.communicate = AsyncMock(return_value=(stdout.encode("utf-8"), stderr.encode("utf-8")))

        # Patch subprocess creation
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        return mock_proc

    return _mock


@pytest.fixture
def mock_any_cli(mock_claude_cli, mock_gemini_cli, mock_codex_cli):
    """Auto-mock any CLI based on model name.

    Convenience fixture that automatically selects the right CLI mock
    based on the model name.

    Args:
        cli_model: Model name (e.g., "claude-cli", "gemini-cli", "codex-cli")
        **kwargs: Arguments to pass to the specific CLI mock

    Returns:
        Mock process object

    Example:
        def test_any_cli(mock_any_cli):
            mock_any_cli("claude-cli", response_text="Hello")
            # Test code...
    """

    def _mock(cli_model, **kwargs):
        if "claude" in cli_model:
            return mock_claude_cli(**kwargs)
        elif "gemini" in cli_model:
            return mock_gemini_cli(**kwargs)
        elif "codex" in cli_model:
            return mock_codex_cli(**kwargs)
        else:
            raise ValueError(f"Unknown CLI model: {cli_model}. Expected 'claude-cli', 'gemini-cli', or 'codex-cli'")

    return _mock
