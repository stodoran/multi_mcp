"""Intent extraction utility for parsing LLM responses."""

import re


def extract_intent(content: str, default: str | None = None) -> str | None:
    """Extract intent from model response content.

    Looks for patterns like:
    - **Intent:** `framework`
    - **Intent:** framework
    - Intent: framework

    Args:
        content: Model response text
        default: Fallback value if no intent found (typically tool name)

    Returns:
        Extracted intent string (lowercase) or default
    """
    patterns = [
        r"\*\*Intent:\*\*\s*`(\w+)`",  # **Intent:** `framework`
        r"\*\*Intent:\*\*\s*(\w+)",  # **Intent:** framework
        r"Intent:\s*`?(\w+)`?",  # Intent: framework
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).lower()

    return default
