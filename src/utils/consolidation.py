"""Multi-model response consolidation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def consolidate_model_results(
    raw_results: list[Any],
):
    """
    Consolidate multiple model results into a single CodeReviewModelResult.

    Args:
        raw_results: List of ModelResponse objects from parallel execution

    Returns:
        CodeReviewModelResult with:
        - model: comma-separated model names (e.g., "gpt-5-mini, claude-sonnet-4.5")
        - content: consolidated analysis summary
        - issues_found: deduplicated issues with found_by attribution
        - metadata.source_models: list of contributing model names
        - metadata.consolidation_model: model used for consolidation
        - metadata.total_tokens: sum of all tokens (cost/resource usage)
        - metadata.latency_ms: max(source_latencies) + consolidation_latency (wall-clock time)

    Note:
        Token counts use sum() (represents total cost/usage).
        Latency uses max() + consolidation (represents wall-clock time user waits).
    """
    # Extract successful results
    successful = [r for r in raw_results if r.status == "success"]

    if not successful:
        # No successful results - return error as CodeReviewModelResult
        from src.schemas.base import ModelResponseMetadata
        from src.schemas.codereview import CodeReviewModelResult

        model_names = ", ".join(r.metadata.model for r in raw_results)

        metadata = ModelResponseMetadata(
            model=model_names,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=0,
            source_models=[r.metadata.model for r in raw_results],
            consolidation_model=None,  # No consolidation performed (all failed)
        )

        return CodeReviewModelResult(
            content="All models failed to complete the review.",
            status="error",
            error="All models failed",
            issues_found=[],
            metadata=metadata,
        )

    # Filter out results with unparseable JSON
    from src.utils.json_parser import parse_llm_json

    valid_results = []
    filtered_count = 0
    for result in successful:
        parsed = parse_llm_json(result.content)
        if parsed and isinstance(parsed, dict):
            valid_results.append(result)
        else:
            filtered_count += 1
            logger.warning(
                f"[CONSOLIDATION] Filtering out {result.metadata.model} - invalid JSON response. "
                "This model's results will not be included in consolidation."
            )

    if not valid_results:
        # All results have invalid JSON - return error
        from src.schemas.base import ModelResponseMetadata
        from src.schemas.codereview import CodeReviewModelResult

        model_names = ", ".join(r.metadata.model for r in successful)

        metadata = ModelResponseMetadata(
            model=model_names,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=0,
            source_models=[r.metadata.model for r in successful],
            consolidation_model=None,
        )

        return CodeReviewModelResult(
            content=f"All {len(successful)} model(s) returned unparseable JSON responses. No results to consolidate.",
            status="error",
            error="All models returned invalid JSON",
            issues_found=[],
            metadata=metadata,
        )

    if filtered_count > 0:
        logger.info(
            f"[CONSOLIDATION] Consolidating {len(valid_results)}/{len(successful)} models ({filtered_count} filtered due to invalid JSON)"
        )

    # Build consolidation messages with only valid results
    messages = _build_consolidation_messages(valid_results)

    # Single LLM call to consolidate using default model
    from src.config import settings
    from src.utils.llm_runner import execute_single

    try:
        # Use execute_single for automatic artifact saving and logging
        response = await execute_single(
            model=settings.default_model,
            messages=messages,
        )

        # Handle error responses
        if response.status != "success":
            raise ValueError(f"Consolidation LLM call failed: {response.error}")

        # Parse response
        from src.utils.json_parser import parse_llm_json

        consolidated = parse_llm_json(response.content)

        if not isinstance(consolidated, dict):
            raise ValueError(f"Expected dict, got {type(consolidated)}")

        # Build final result as CodeReviewModelResult
        from src.schemas.base import ModelResponseMetadata
        from src.schemas.codereview import CodeReviewModelResult

        model_names = ", ".join(r.metadata.model for r in valid_results)

        # Aggregate token counts (sum = total cost/resource usage)
        # Only count tokens from valid results that were actually consolidated
        total_prompt_tokens = sum(r.metadata.prompt_tokens for r in valid_results if r.metadata.prompt_tokens)
        total_completion_tokens = sum(r.metadata.completion_tokens for r in valid_results if r.metadata.completion_tokens)
        total_tokens = sum(r.metadata.total_tokens for r in valid_results if r.metadata.total_tokens)

        # Aggregate latency (max = wall-clock time in parallel execution)
        # Users wait for the SLOWEST model, not sum of all models
        max_source_latency = max((r.metadata.latency_ms for r in valid_results if r.metadata.latency_ms), default=0)

        # Add consolidation LLM metrics to aggregates
        if response.metadata.total_tokens:
            total_tokens += response.metadata.total_tokens
        if response.metadata.prompt_tokens:
            total_prompt_tokens += response.metadata.prompt_tokens
        if response.metadata.completion_tokens:
            total_completion_tokens += response.metadata.completion_tokens

        # Latency: max(parallel sources) + sequential consolidation
        consolidation_latency = response.metadata.latency_ms or 0
        total_latency_ms = max_source_latency + consolidation_latency

        # Build metadata with consolidated fields
        metadata = ModelResponseMetadata(
            model=model_names,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            latency_ms=total_latency_ms,
            artifacts=response.metadata.artifacts if hasattr(response.metadata, "artifacts") else None,
            source_models=[r.metadata.model for r in valid_results],
            consolidation_model=settings.default_model,
        )

        # Return typed Pydantic model
        return CodeReviewModelResult(
            content=consolidated.get("message", "No summary provided."),
            status=consolidated.get("status", "success"),
            issues_found=consolidated.get("issues_found", []),
            metadata=metadata,
        )

    except Exception as e:
        logger.warning(f"[CONSOLIDATION] Failed: {e}. Falling back to first result.")
        # Fallback: return first successful result as CodeReviewModelResult
        from src.schemas.base import ModelResponseMetadata
        from src.schemas.codereview import CodeReviewModelResult

        first = successful[0]

        # Extract issues from first result
        issues = _extract_issues_from_content(first.content)

        # Build metadata from first result (may be Mock in tests, so extract attrs)
        artifacts_val = getattr(first.metadata, "artifacts", None)
        # Ensure artifacts is None or a list (not a Mock)
        if artifacts_val is not None and not isinstance(artifacts_val, list):
            artifacts_val = None

        metadata = ModelResponseMetadata(
            model=getattr(first.metadata, "model", "unknown"),
            prompt_tokens=getattr(first.metadata, "prompt_tokens", 0),
            completion_tokens=getattr(first.metadata, "completion_tokens", 0),
            total_tokens=getattr(first.metadata, "total_tokens", 0),
            latency_ms=getattr(first.metadata, "latency_ms", 0),
            artifacts=artifacts_val,
            # Note: source_models and consolidation_model remain None (fallback path)
        )

        # Return as CodeReviewModelResult
        return CodeReviewModelResult(
            content=first.content,
            status="success",
            issues_found=issues,
            metadata=metadata,
        )


def _build_consolidation_messages(successful_results: list[Any]) -> list[dict]:
    """Build messages array for LLM to consolidate multiple model responses."""
    from src.prompts import CODEREVIEW_CONSOLIDATION_PROMPT

    # Build model responses in XML format
    model_responses = []
    for result in successful_results:
        model_name = result.metadata.model
        model_content = result.content
        model_responses.append(f'<MODEL name="{model_name}">\n{model_content}\n</MODEL>')

    models_xml = "\n\n".join(model_responses)

    # Build user message with structured input
    user_message = f"""<MODEL_RESPONSES>
{models_xml}
</MODEL_RESPONSES>

Please consolidate these code review results following the instructions in the system prompt."""

    return [
        {"role": "system", "content": CODEREVIEW_CONSOLIDATION_PROMPT},
        {"role": "user", "content": user_message},
    ]


def _extract_issues_from_content(content: str) -> list[dict]:
    """Fallback: Try to extract issues from model content (JSON parsing)."""
    from src.utils.json_parser import parse_llm_json

    try:
        parsed = parse_llm_json(content)
        if isinstance(parsed, dict) and "issues_found" in parsed:
            return parsed["issues_found"]
    except Exception:
        pass
    return []
