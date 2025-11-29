"""Unit tests for models tool."""

from unittest.mock import patch

import pytest

from src.models.config import ModelConfig, ModelsConfiguration
from src.tools.models import models_impl


class TestModelsImpl:
    """Tests for models_impl function."""

    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing."""
        return ModelsConfiguration(
            version="1.0",
            default_model="gpt-5-mini",
            models={
                "gpt-5-mini": ModelConfig(
                    litellm_model="openai/gpt-5-mini",
                    aliases=["mini"],
                    context_window=128000,
                ),
                "haiku": ModelConfig(
                    litellm_model="anthropic/claude-sonnet-4-5-20250929",
                    aliases=["sonnet"],
                ),
                "disabled-model": ModelConfig(
                    litellm_model="openai/disabled",
                    disabled=True,
                ),
            },
        )

    @pytest.mark.asyncio
    async def test_models_impl_returns_model_list(self, sample_config):
        """Test that models_impl returns list of models."""
        with patch("src.tools.models.ModelResolver") as mock_resolver_class:
            mock_resolver = mock_resolver_class.return_value
            mock_resolver.config = sample_config
            mock_resolver.list_models.return_value = [
                {
                    "name": "gpt-5-mini",
                    "aliases": ["mini"],
                    "provider": "openai",
                    "context_window": 128000,
                    "max_tokens": None,
                    "disabled": False,
                    "notes": "",
                },
                {
                    "name": "haiku",
                    "aliases": ["sonnet"],
                    "provider": "anthropic",
                    "context_window": None,
                    "max_tokens": None,
                    "disabled": False,
                    "notes": "",
                },
            ]

            result = await models_impl()

            assert "models" in result
            assert "default_model" in result
            assert "count" in result

            assert len(result["models"]) == 2
            assert result["count"] == 2
            assert result["default_model"] == "gpt-5-mini"

            # Verify list_models was called with include_disabled=False
            mock_resolver.list_models.assert_called_once_with(include_disabled=False)

    @pytest.mark.asyncio
    async def test_models_impl_includes_aliases_and_metadata(self, sample_config):
        """Test that returned models include all metadata fields."""
        with patch("src.tools.models.ModelResolver") as mock_resolver_class:
            mock_resolver = mock_resolver_class.return_value
            mock_resolver.config = sample_config
            mock_resolver.list_models.return_value = [
                {
                    "name": "gpt-5-mini",
                    "aliases": ["mini", "gpt5-mini"],
                    "provider": "openai",
                    "context_window": 128000,
                    "max_tokens": 16000,
                    "disabled": False,
                    "notes": "Fast and cost-effective",
                },
            ]

            result = await models_impl()

            model = result["models"][0]
            assert model["name"] == "gpt-5-mini"
            assert "mini" in model["aliases"]
            assert "gpt5-mini" in model["aliases"]
            assert model["provider"] == "openai"
            assert model["context_window"] == 128000
            assert model["max_tokens"] == 16000
            assert model["disabled"] is False
            assert model["notes"] == "Fast and cost-effective"

    @pytest.mark.asyncio
    async def test_models_impl_excludes_disabled_models(self, sample_config):
        """Test that disabled models are excluded from the list."""
        with patch("src.tools.models.ModelResolver") as mock_resolver_class:
            mock_resolver = mock_resolver_class.return_value
            mock_resolver.config = sample_config
            # list_models should return only enabled models
            mock_resolver.list_models.return_value = [
                {
                    "name": "gpt-5-mini",
                    "aliases": ["mini"],
                    "provider": "openai",
                    "context_window": None,
                    "max_tokens": None,
                    "disabled": False,
                    "notes": "",
                },
                {
                    "name": "haiku",
                    "aliases": ["sonnet"],
                    "provider": "anthropic",
                    "context_window": None,
                    "max_tokens": None,
                    "disabled": False,
                    "notes": "",
                },
            ]

            result = await models_impl()

            # Should have 2 models (disabled-model excluded)
            assert result["count"] == 2
            model_names = [m["name"] for m in result["models"]]
            assert "disabled-model" not in model_names
            assert "gpt-5-mini" in model_names
            assert "haiku" in model_names
