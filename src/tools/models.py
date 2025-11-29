"""Models tool implementation using config."""

import logging

from src.models.resolver import ModelResolver

logger = logging.getLogger(__name__)


async def models_impl() -> dict:
    """Return models from configuration with LiteLLM metadata enrichment."""
    resolver = ModelResolver()
    models = resolver.list_models(include_disabled=False)

    logger.info(f"[MODELS] Returning {len(models)} available models")

    return {
        "models": models,
        "default_model": resolver.config.default_model,
        "count": len(models),
    }
