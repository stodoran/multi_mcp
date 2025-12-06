"""Shared parallel model execution utility."""

import asyncio
import logging

from src.models.litellm_client import litellm_client
from src.schemas.base import ModelResponse

logger = logging.getLogger(__name__)


async def execute_single(
    model: str,
    messages: list[dict],
    enable_web_search: bool = False,
) -> ModelResponse:
    """Execute single-model LLM call with automatic artifact saving.
    Args:
        model: Model name to use
        messages: Pre-built messages array
        enable_web_search: Enable provider-native web search if supported

    Returns:
        ModelResponse with artifacts in metadata if saving succeeded
    """
    from src.utils.artifacts import save_tool_artifacts

    response = await litellm_client.call_async(
        messages=messages,
        model=model,
        enable_web_search=enable_web_search,
    )

    if response.status == "success":
        artifact_paths = await save_tool_artifacts(response=response)

        if artifact_paths:
            response.metadata.artifacts = artifact_paths

    return response


async def execute_parallel(
    models: list[str],
    messages: list[dict],
    max_concurrency: int = 5,
    enable_web_search: bool = False,
) -> list[ModelResponse]:
    """
    Execute messages against multiple models in parallel.

    Args:
        models: List of model names
        messages: Pre-built messages array (same for all models)
        max_concurrency: Max concurrent calls (default: 5)
        enable_web_search: Enable provider-native web search if supported

    Note:
        All artifact metadata (workflow, name, step_number, thread_id, base_path)
        is automatically retrieved from request context.

    Returns:
        list[ModelResponse]: One response per model (includes errors/timeouts)
    """
    # Use Semaphore for concurrency control (throttles instead of rejecting)
    sem = asyncio.Semaphore(max_concurrency)

    logger.info(f"[LLM_RUNNER] Executing {len(models)} models in parallel (max_concurrency: {max_concurrency})")

    async def _bounded_call(model_name: str) -> ModelResponse:
        async with sem:
            response = await litellm_client.call_async(
                messages=messages,
                model=model_name,
                enable_web_search=enable_web_search,
            )

            if response.status == "success":
                from src.utils.artifacts import save_tool_artifacts

                artifact_paths = await save_tool_artifacts(response=response)

                if artifact_paths:
                    response.metadata.artifacts = artifact_paths

            return response

    # Run all models in parallel (throttled by semaphore)
    tasks = [_bounded_call(model) for model in models]

    results: list[ModelResponse] = await asyncio.gather(*tasks)

    successes = sum(1 for r in results if r.status == "success")
    logger.info(f"[LLM_RUNNER] Complete: {successes}/{len(results)} models succeeded")

    return results
