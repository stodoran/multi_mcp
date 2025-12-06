"""Unit tests for CLI output parsing (mocked, no real CLIs needed).

These tests verify CLI output parsing logic using mocks.
They run in <1 second and don't require any CLIs installed.

All tests use mock fixtures from tests/fixtures/cli_mocks.py.
"""

import pytest


class TestCLIJSONParsing:
    """Test JSON parsing from CLI output."""

    @pytest.mark.asyncio
    async def test_claude_cli_json_response(self, mock_claude_cli):
        """Parse Claude CLI JSON response correctly."""
        mock_claude_cli(response_text="The answer is 4")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "What is 2+2?"}], model="claude-cli")

        assert result.status == "success"
        assert "4" in result.content
        assert result.metadata.model == "claude-cli"
        assert result.metadata.latency_ms >= 0  # Mock might execute instantly

    @pytest.mark.asyncio
    async def test_gemini_cli_json_response(self, mock_gemini_cli):
        """Parse Gemini CLI JSON response correctly."""
        mock_gemini_cli(response_text="4")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "What is 2+2?"}], model="gemini-cli")

        assert result.status == "success"
        assert result.content == "4"
        assert result.metadata.model == "gemini-cli"

    @pytest.mark.asyncio
    async def test_codex_cli_jsonl_parsing(self, mock_codex_cli):
        """Parse Codex CLI JSONL output correctly."""
        mock_codex_cli(response_text="The answer is 4")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "What is 2+2?"}], model="codex-cli")

        assert result.status == "success"
        assert "The answer is 4" in result.content
        assert result.metadata.model == "codex-cli"

    @pytest.mark.asyncio
    async def test_claude_cli_multiline_response(self, mock_claude_cli):
        """Parse Claude CLI response with multiple lines."""
        mock_claude_cli(response_text="Line 1\\nLine 2\\nLine 3")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "Give me 3 lines"}], model="claude-cli")

        assert result.status == "success"
        assert "Line 1" in result.content
        assert "Line 2" in result.content
        assert "Line 3" in result.content

    @pytest.mark.asyncio
    async def test_gemini_cli_unicode_response(self, mock_gemini_cli):
        """Parse Gemini CLI response with unicode characters."""
        mock_gemini_cli(response_text="Hello 世界 🌍")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "Say hello in different languages"}], model="gemini-cli")

        assert result.status == "success"
        assert "世界" in result.content
        assert "🌍" in result.content

    @pytest.mark.asyncio
    async def test_codex_cli_empty_text_fields_filtered(self, mocker):
        """Codex CLI filters out empty text fields."""
        # Custom mock for this specific test
        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/codex")

        from unittest.mock import AsyncMock, Mock

        mock_proc = Mock()
        mock_proc.returncode = 0
        # JSONL with empty text fields (should be filtered)
        stdout = (
            '{"type": "text", "text": ""}\n'  # Empty, should be skipped
            '{"type": "text", "text": "Hello"}\n'
            '{"type": "text", "text": ""}\n'  # Empty, should be skipped
            '{"type": "text", "text": "World"}\n'
        )
        mock_proc.communicate = AsyncMock(return_value=(stdout.encode(), b""))
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="codex-cli")

        assert result.status == "success"
        # Only non-empty text should be included
        assert result.content == "Hello\nWorld"

    @pytest.mark.asyncio
    async def test_claude_cli_special_characters_in_response(self, mock_claude_cli):
        """Parse Claude CLI response with special JSON characters."""
        # Test with quotes, backslashes, etc.
        mock_claude_cli(response_text='She said \\"Hello\\" to me')

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")

        assert result.status == "success"
        assert "Hello" in result.content

    @pytest.mark.asyncio
    async def test_gemini_cli_long_response(self, mock_gemini_cli):
        """Parse Gemini CLI long response correctly."""
        long_text = "A" * 10000
        mock_gemini_cli(response_text=long_text)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "Give me a long text"}], model="gemini-cli")

        assert result.status == "success"
        assert len(result.content) == 10000
        assert result.content == long_text


class TestCLIAliasResolution:
    """Test CLI model alias resolution."""

    @pytest.mark.asyncio
    async def test_claude_cli_alias_resolves(self, mock_claude_cli):
        """Claude CLI alias resolves to canonical name."""
        mock_claude_cli(response_text="test")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(
            messages=[{"role": "user", "content": "test"}],
            model="cl-cli",  # Using alias
        )

        assert result.status == "success"
        assert result.metadata.model == "claude-cli"  # Should resolve to canonical name

    @pytest.mark.asyncio
    async def test_gemini_cli_alias_resolves(self, mock_gemini_cli):
        """Gemini CLI alias resolves to canonical name."""
        mock_gemini_cli(response_text="test")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(
            messages=[{"role": "user", "content": "test"}],
            model="gem-cli",  # Using alias
        )

        assert result.status == "success"
        assert result.metadata.model == "gemini-cli"

    @pytest.mark.asyncio
    async def test_codex_cli_alias_resolves(self, mock_codex_cli):
        """Codex CLI alias resolves to canonical name."""
        mock_codex_cli(response_text="test")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(
            messages=[{"role": "user", "content": "test"}],
            model="cx-cli",  # Using alias
        )

        assert result.status == "success"
        assert result.metadata.model == "codex-cli"


class TestCLIMetadata:
    """Test CLI metadata extraction."""

    @pytest.mark.asyncio
    async def test_cli_latency_tracking(self, mock_claude_cli, mocker):
        """Track CLI execution latency."""
        import asyncio
        import time

        # Make the mock take some time
        async def slow_communicate(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return (b'{"result": "ok", "is_error": false}', b"")

        mocker.patch("src.models.litellm_client.shutil.which", return_value="/usr/bin/claude")
        mock_proc = mocker.Mock()
        mock_proc.returncode = 0
        mock_proc.communicate = slow_communicate
        mocker.patch("src.models.litellm_client.asyncio.create_subprocess_exec", return_value=mock_proc)

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()

        start = time.time()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")
        duration_ms = (time.time() - start) * 1000

        assert result.status == "success"
        assert result.metadata.latency_ms > 0
        # Latency should be approximately equal to actual duration (within 20ms tolerance)
        assert abs(result.metadata.latency_ms - duration_ms) < 20

    @pytest.mark.asyncio
    async def test_cli_token_counts_are_zero(self, mock_claude_cli):
        """CLI models don't report token counts (set to 0)."""
        mock_claude_cli(response_text="test")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="claude-cli")

        assert result.status == "success"
        assert result.metadata.prompt_tokens == 0
        assert result.metadata.completion_tokens == 0
        assert result.metadata.total_tokens == 0

    @pytest.mark.asyncio
    async def test_cli_model_name_in_metadata(self, mock_gemini_cli):
        """CLI model name is correctly set in metadata."""
        mock_gemini_cli(response_text="test")

        from src.models.litellm_client import LiteLLMClient

        client = LiteLLMClient()
        result = await client.call_async(messages=[{"role": "user", "content": "test"}], model="gemini-cli")

        assert result.status == "success"
        assert result.metadata.model == "gemini-cli"
