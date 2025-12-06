"""Unit tests for CLI error handling (mocked).

These tests verify error scenarios using mocks, without requiring real CLIs.
They test:
- Non-zero exit codes
- Timeouts
- CLI not found
- Malformed output
- Claude CLI is_error flag
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest


class TestCLIErrorHandling:
    """Test CLI error scenarios."""

    @pytest.mark.asyncio
    async def test_cli_exit_code_1(self, mock_claude_cli):
        """Handle non-zero exit code."""
        mock_claude_cli(exit_code=1, stderr="Error: Invalid API key")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")

        assert result.status == "error"
        assert "exit code 1" in result.error.lower()
        assert "Invalid API key" in result.error

    @pytest.mark.asyncio
    async def test_cli_timeout(self, mocker):
        """Handle CLI timeout."""

        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/claude")

        # Create async mock that will be cancelled by wait_for
        async def slow_communicate(*args, **kwargs):
            await asyncio.sleep(10)  # Long enough to be cancelled
            return (b"", b"")

        mock_proc = Mock()
        mock_proc.returncode = None
        mock_proc.communicate = slow_communicate
        mock_proc.kill = Mock()

        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        # Mock asyncio.wait_for to raise TimeoutError immediately
        async def mock_wait_for(coro, timeout):
            # Close the coroutine to prevent "was never awaited" warning
            coro.close()
            # For our test, immediately raise TimeoutError instead of actually waiting
            raise TimeoutError()

        mocker.patch("src.models.litellm_client.asyncio.wait_for", side_effect=mock_wait_for)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")

        assert result.status == "error"
        assert "timed out" in result.error.lower()
        mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_cli_not_found(self, mocker):
        """Handle CLI command not found."""
        mocker.patch("shutil.which", return_value=None)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")

        assert result.status == "error"
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_claude_cli_error_flag(self, mocker):
        """Handle Claude CLI is_error=true response."""
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/claude")

        mock_proc = Mock()
        mock_proc.returncode = 0  # Success exit code
        # But is_error flag is true
        stdout = '{"result": "Permission denied", "is_error": true}'
        mock_proc.communicate = AsyncMock(return_value=(stdout.encode(), b""))
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")

        assert result.status == "error"
        assert "Permission denied" in result.error

    @pytest.mark.asyncio
    async def test_cli_malformed_json(self, mocker):
        """Handle malformed JSON output."""
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/gemini")

        mock_proc = Mock()
        mock_proc.returncode = 0
        # Malformed JSON
        stdout = '{"response": invalid json here'
        mock_proc.communicate = AsyncMock(return_value=(stdout.encode(), b""))
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="gemini-cli")

        # Should fall back to raw text
        assert result.status == "success"
        assert "response" in result.content

    @pytest.mark.asyncio
    async def test_cli_empty_output(self, mocker):
        """Handle empty CLI output."""
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/gemini")

        mock_proc = Mock()
        mock_proc.returncode = 0
        # Empty output
        stdout = ""
        mock_proc.communicate = AsyncMock(return_value=(stdout.encode(), b""))
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="gemini-cli")

        # Empty output should still be success (just empty content)
        assert result.status == "success"
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_cli_stderr_output(self, mock_claude_cli):
        """Handle CLI that writes to stderr."""
        mock_claude_cli(response_text="Success", stderr="Warning: Using deprecated API")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")

        # Should still succeed (stderr is just warnings)
        assert result.status == "success"
        assert result.content == "Success"

    @pytest.mark.asyncio
    async def test_cli_non_zero_exit_with_stdout(self, mocker):
        """Handle non-zero exit with stdout output."""
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/claude")

        mock_proc = Mock()
        mock_proc.returncode = 1
        # Has stdout but failed
        stdout = '{"result": "Partial response before error"}'
        stderr = "Fatal error occurred"
        mock_proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")

        assert result.status == "error"
        assert "exit code 1" in result.error.lower()
        # Should include stderr in error message
        assert "Fatal error" in result.error or "Partial response" in result.error

    @pytest.mark.asyncio
    async def test_codex_cli_malformed_jsonl(self, mocker):
        """Handle malformed JSONL from Codex CLI."""
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/codex")

        mock_proc = Mock()
        mock_proc.returncode = 0
        # Mix of valid and invalid JSONL
        stdout = (
            '{"type": "text", "text": "Valid line"}\n'
            "invalid json line\n"  # Should be skipped
            '{"type": "text", "text": "Another valid"}\n'
        )
        mock_proc.communicate = AsyncMock(return_value=(stdout.encode(), b""))
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="codex-cli")

        # Should succeed and skip invalid lines
        assert result.status == "success"
        assert "Valid line" in result.content
        assert "Another valid" in result.content

    @pytest.mark.asyncio
    async def test_cli_unicode_error_handling(self, mocker):
        """Handle invalid unicode in CLI output."""
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/gemini")

        mock_proc = Mock()
        mock_proc.returncode = 0
        # Invalid UTF-8 sequence
        stdout = b'{"response": "Test \xff invalid"}'  # \xff is invalid UTF-8
        mock_proc.communicate = AsyncMock(return_value=(stdout, b""))
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="gemini-cli")

        # Should handle gracefully (replace invalid chars)
        assert result.status == "success"
        assert "Test" in result.content
