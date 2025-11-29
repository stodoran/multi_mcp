"""CodeReview schema models."""

from pydantic import Field

from src.schemas.base import SingleToolRequest, SingleToolResponse


class CodeReviewRequest(SingleToolRequest):
    """Code review request."""

    content: str = Field(
        ...,
        description=(
            "Your code review request for the expert reviewer. "
            "Step 1: Describe the project and define review objectives and focus areas. "
            "Step 2+: Report findings organized by quality, security, performance, architecture. "
            "Include: what to review, focus areas (security/concurrency/logic), specific concerns, confidence level. "
            "Exclude: code snippets (use `relevant_files`), issue lists (use `issues_found`)."
        ),
    )
    issues_found: list[dict] | None = Field(
        default=None,
        description=(
            "REQUIRED: List of issues identified with severity levels, locations, and detailed descriptions. "
            "IMPORTANT: This list is CUMULATIVE across steps. Include ALL issues found in previous steps PLUS new ones. "
            "Each dict must contain these keys: "
            "'severity' (required, one of: 'critical', 'high', 'medium', 'low'), "
            "'location' (required, format: 'filename:line_number' or 'filename' if line unknown), "
            "'description' (required, detailed explanation of the issue). "
            "Example: [{'severity': 'high', 'location': 'auth.py:45', "
            "'description': 'SQL injection vulnerability in login query - user input not sanitized'}]. "
            "Empty list is acceptable if no issues found yet."
        ),
    )


class CodeReviewResponse(SingleToolResponse):
    """Code review response."""

    content: str = Field(
        ...,
        description=(
            "Step 1: Returns checklist for code review workflow. "
            "Step 2+: Expert analysis covering security, performance, architecture, and code quality. "
            "May request more files or suggest narrowing scope if needed."
        ),
    )
    issues_found: list[dict] | None = Field(
        default=None,
        description=(
            "Structured list of confirmed issues. "
            "Each dict contains: "
            "'severity' ('critical'/'high'/'medium'/'low'), "
            "'location' ('filename:line_number'), "
            "'description' (what's wrong and why it matters). "
            "Empty list means no issues found. None means issues are in content only."
        ),
    )
