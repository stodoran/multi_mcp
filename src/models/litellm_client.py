"""LiteLLM client wrapper with config-based model resolution."""

import asyncio
import logging
import time
from typing import Any

import litellm

from src.config import settings
from src.models.resolver import ModelResolver
from src.schemas.base import ModelResponse, ModelResponseMetadata
from src.utils.request_logger import log_llm_interaction

logger = logging.getLogger(__name__)

litellm.drop_params = True


class LiteLLMClient:
    """Wrapper for LiteLLM model calls with config-based resolution."""

    def __init__(self, resolver: ModelResolver | None = None):
        """Initialize LiteLLM client.

        Args:
            resolver: Optional ModelResolver instance. Creates one if not provided.
        """
        self._resolver: ModelResolver | None = resolver

    @property
    def resolver(self) -> ModelResolver:
        """Lazy-load resolver to avoid import-time config loading."""
        if self._resolver is None:
            self._resolver = ModelResolver()
        return self._resolver

    async def call_async(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> ModelResponse:
        """Call LiteLLM with config-based model resolution and return ModelResponse.

        Args:
            messages: List of message dicts with role and content
            model: Model name or alias (uses default if not specified)

        Returns:
            ModelResponse with status, content, metadata, error
        """
        # Resolve model: explicit > primary default
        model = model or self.resolver.get_default()
        timeout = settings.model_timeout_seconds

        try:
            canonical_name, model_config = self.resolver.resolve(model)
            litellm_model = model_config.litellm_model

            # Apply temperature (config constraint > default)
            temp = settings.default_temperature
            if model_config.constraints and model_config.constraints.temperature is not None:
                temp = model_config.constraints.temperature

            logger.info(f"[MODEL_CALL] input={model} canonical={canonical_name} litellm={litellm_model} temp={temp}")

            # Build kwargs starting with generic params from config
            kwargs: dict[str, Any] = {
                **model_config.params,
                "model": litellm_model,
                "messages": messages,
                "temperature": temp,
                "num_retries": settings.max_retries,
                "timeout": timeout,
            }

            logger.debug(f"[MODEL_REQUEST] litellm_model={litellm_model} num_messages={len(messages)}")

            # Call LiteLLM with timeout protection
            start_time = time.perf_counter()
            response = await asyncio.wait_for(
                litellm.acompletion(**kwargs),
                timeout=timeout,
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            content = response.choices[0].message.content or ""  # type: ignore[attr-defined]

            metadata = ModelResponseMetadata(
                model=canonical_name,
                prompt_tokens=response.usage.prompt_tokens,  # type: ignore[attr-defined]
                completion_tokens=response.usage.completion_tokens,  # type: ignore[attr-defined]
                total_tokens=response.usage.total_tokens,  # type: ignore[attr-defined]
                latency_ms=latency_ms,
            )
            response = ModelResponse(
                content=content,
                status="success",
                metadata=metadata,
            )

            log_llm_interaction(
                request_data={**kwargs},
                response_data=response.model_dump(),
            )
            return response

        except TimeoutError:
            logger.error(f"[MODEL_CALL] Model {model} timed out after {timeout}s")
            return ModelResponse.error_response(
                error=f"Request timed out after {timeout}s",
                model=model,
            )
        except Exception as e:
            logger.error(f"[MODEL_CALL] Model {model} failed: {e}")
            return ModelResponse.error_response(
                error=str(e),
                model=model,
            )


litellm_client = LiteLLMClient()
