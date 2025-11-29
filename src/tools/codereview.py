"""Code review tool implementation."""

import logging
from typing import Literal

from src.prompts import CODEREVIEW_PROMPT
from src.schemas.base import ModelResponseMetadata, NextAction
from src.schemas.codereview import CodeReviewResponse
from src.utils.json_parser import parse_llm_json
from src.utils.message_builder import MessageBuilder
from src.utils.prompts import build_expert_context

logger = logging.getLogger(__name__)


async def codereview_impl(
    name: str,
    content: str,
    step_number: int,
    next_action: Literal["continue", "stop"],
    base_path: str,
    model: str,
    thread_id: str,
    relevant_files: list[str] | None = None,
    issues_found: list[dict] | None = None,
) -> dict:
    """Code review implementation with conversation history support."""
    logger.info(f"[CODEREVIEW] {name} - step {step_number}, action={next_action}, files={len(relevant_files or [])}")

    # Step 1: Return checklist
    if step_number == 1:
        logger.info(f"[CODEREVIEW] Starting new review {thread_id} - providing checklist")
        checklist_content = """# Code Review Checklist - Step 1

Complete this checklist, then call step 2 with your findings and relevant_files.

## Checklist:
- Read and understand the code base
- Read and understand the relevant files specified
- Map out main modules, classes and functions
- Verify intended behavior and business logic
- Check architecture, structure and design patterns
- Look for bugs, security risks and performance issues
- Identify code smells and maintainability problems
- Add files to `relevant_files` list

**Next**: Set `next_action='continue'` and `step_number=2` with findings in `content` and files in `relevant_files`."""

        result = CodeReviewResponse(
            status="in_progress",
            thread_id=thread_id,
            content=checklist_content,
            next_action=NextAction(action="continue", reason="Complete checklist, then proceed to step 2"),
            metadata=ModelResponseMetadata.error_metadata(),
        )
        return result.model_dump(exclude_none=True)

    # Validate files
    if not relevant_files:
        logger.info(f"[CODEREVIEW] No relevant files provided at step {step_number}")
        result = CodeReviewResponse(
            status="in_progress",
            thread_id=thread_id,
            content=(
                "⚠️ **No relevant files provided**\n\n"
                "To continue the code review, you must:\n"
                "1. Identify the files you want reviewed\n"
                "2. Add their absolute paths to the `relevant_files` parameter\n"
                "3. Include project documentation (README.md, CLAUDE.md) for context\n\n"
                "Example:\n"
                "```\nrelevant_files=[\n"
                "  '/path/to/project/README.md',\n"
                "  '/path/to/project/src/main.py',\n"
                "  '/path/to/project/tests/test_main.py'\n"
                "]\n```"
            ),
            next_action=NextAction(
                action="continue",
                reason="Add file paths to `relevant_files` parameter and retry with the same step_number",
            ),
            metadata=ModelResponseMetadata.error_metadata(),
        )
        return result.model_dump(exclude_none=True)

    logger.info("[CODEREVIEW] Final step - calling expert analysis")

    # Build expert context
    expert_context = build_expert_context(content=content, issues_found=issues_found)

    # Build messages with conversation history
    messages = await (
        MessageBuilder(
            system_prompt=CODEREVIEW_PROMPT,
            base_path=base_path,
            thread_id=thread_id,
            include_history=True,
        )
        .add_conversation_history()  # Check for existing history
        .add_repository_context()  # Skip if continuation
        .add_files(relevant_files)  # Skip if continuation
        .add_user_message(expert_context, escape_html=False)  # Already formatted XML
        .build()
    )

    # Call LLM
    from src.utils.llm_runner import execute_single

    model_response = await execute_single(
        model=model,
        messages=messages,
    )

    # Handle response
    if model_response.status == "error":
        logger.error(f"[CODEREVIEW] {model_response.error}")
        return CodeReviewResponse.error_response(
            thread_id=thread_id,
            error=model_response.error,
            metadata=model_response.metadata,
        ).model_dump(exclude_none=True)

    # Success case
    logger.info(
        f"[CODEREVIEW] Expert analysis complete - "
        f"tokens={model_response.metadata.total_tokens} "
        f"latency={model_response.metadata.latency_ms}ms"
    )
    from src.memory.store import store_conversation_turn

    await store_conversation_turn(thread_id, messages, model_response.content)

    # Parse response
    metadata = model_response.metadata
    parsed_json = parse_llm_json(model_response.content)
    status = None if parsed_json is None or not isinstance(parsed_json, dict) or "status" not in parsed_json else parsed_json.get("status")

    ALLOWED_STATUSES = [
        "files_required_to_continue",
        "focused_review_required",
        "unreviewable_content",
        "no_issues_found",
        "review_complete",
    ]

    if parsed_json is None or status is None or status not in ALLOWED_STATUSES:
        logger.info("[CODEREVIEW] LLM response is not valid JSON or missing 'status' field")
        result = CodeReviewResponse(
            status="success",
            thread_id=thread_id,
            content=model_response.content,
            metadata=metadata,
        )
        return result.model_dump(exclude_none=True)

    if status == "files_required_to_continue":
        logger.info("[CODEREVIEW] Expert needs more files")
        files_needed = parsed_json.get("files_needed", [])
        message_text = parsed_json.get("message", "Need additional files")
        files_list = "\n".join(f"- {f}" for f in files_needed)
        result = CodeReviewResponse(
            status="in_progress",
            thread_id=thread_id,
            content=f"{message_text}\n\nFiles needed:\n{files_list}",
            next_action=NextAction(action="continue", reason=f"Expert needs {len(files_needed)} additional files"),
            metadata=metadata,
        )
    elif status == "focused_review_required":
        logger.info("[CODEREVIEW] Expert suggests narrowing scope")
        message_text = parsed_json.get("message", "Scope too large")
        suggestion = parsed_json.get("suggestion", "")
        result = CodeReviewResponse(
            status="in_progress",
            thread_id=thread_id,
            content=f"{message_text}\n\nSuggestion: {suggestion}",
            next_action=NextAction(action="continue", reason="Scope too large for effective review"),
            metadata=metadata,
        )
    elif status == "unreviewable_content":
        logger.warning("[CODEREVIEW] Expert cannot review content")
        message_text = parsed_json.get("message", "Content is unreviewable")
        result = CodeReviewResponse(
            status="success",
            thread_id=thread_id,
            content=f"Content is unreviewable: {message_text}",
            metadata=metadata,
        )
    elif status == "no_issues_found":
        logger.info("[CODEREVIEW] Expert found no issues")
        message_text = parsed_json.get("message", "No issues detected")
        result = CodeReviewResponse(
            status="success",
            thread_id=thread_id,
            content=message_text,
            issues_found=[],
            metadata=metadata,
        )
    elif status == "review_complete" and "issues_found" in parsed_json:
        logger.info("[CODEREVIEW] Expert completed review with issues found")
        message_text = parsed_json.get("message", "Review complete with issues found")
        issues_found_result = parsed_json.get("issues_found", [])
        result = CodeReviewResponse(
            status="success",
            thread_id=thread_id,
            content=message_text,
            issues_found=issues_found_result,
            metadata=metadata,
        )
    else:
        logger.info(f"[CODEREVIEW] Unknown status '{status}', treating as normal review")
        result = CodeReviewResponse(
            status="success",
            thread_id=thread_id,
            content=model_response.content,
            metadata=metadata,
        )

    return result.model_dump(exclude_none=True)
