"""Comparison tool implementation - side-by-side multi-model execution."""

import logging
from typing import Literal

from src.prompts import COMPARISON_PROMPT
from src.schemas.base import ModelResponse
from src.schemas.comparison import ComparisonResponse
from src.utils.llm_runner import execute_parallel
from src.utils.message_builder import MessageBuilder

logger = logging.getLogger(__name__)


async def comparison_impl(
    name: str,
    content: str,
    step_number: int,
    next_action: Literal["continue", "stop"],
    base_path: str,
    models: list[str],
    thread_id: str,
    relevant_files: list[str] | None = None,
) -> dict:
    """Comparison implementation - fully stateless."""
    logger.info(f"[COMPARISON] Starting with {len(models)} models, {len(relevant_files or [])} files")

    messages = await (
        MessageBuilder(system_prompt=COMPARISON_PROMPT, base_path=base_path)
        .add_repository_context()
        .add_files(relevant_files)
        .add_user_message(content)
        .build()
    )

    results: list[ModelResponse] = await execute_parallel(
        models=models,
        messages=messages,
    )

    # Build response
    successes = sum(1 for r in results if r.status == "success")
    if successes == len(results):
        status = "success"
        summary = f"Comparison complete: all {len(results)} models succeeded"
    elif successes > 0:
        status = "partial"
        failed = [r.metadata.model for r in results if r.status == "error"]
        summary = f"Comparison: {successes}/{len(results)} succeeded. Failed: {', '.join(failed)}"
    else:
        status = "error"
        summary = f"Comparison failed: all {len(results)} models failed"

    logger.info(f"[COMPARISON] Complete: {successes}/{len(results)} models succeeded")

    return ComparisonResponse(
        thread_id=thread_id,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        results=results,
    ).model_dump(exclude_none=True)
