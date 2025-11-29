"""Robust JSON extraction and parsing for LLM responses.

This module provides utilities to extract and parse JSON from LLM responses
that may contain markdown formatting, comments, or other non-standard JSON.
"""

import json
import re
from typing import Any

_CODE_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

_ANALYSIS_BLOCK_RE = re.compile(r"<analysis>[\s\S]*?</analysis>", re.IGNORECASE)

_COMMENT_RE = re.compile(
    r"""
    //.*?$           |   # line comments
    /\*[\s\S]*?\*/       # block comments
    """,
    re.MULTILINE | re.VERBOSE,
)

_UNQUOTED_KEY_RE = re.compile(r"(?P<prefix>[{\[,]\s*)(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)(?P<suffix>\s*:)")

_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")

_SMART_QUOTES = {
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',  # double quotes
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",  # single quotes
}


def _strip_code_fences(s: str) -> str:
    """Strip markdown code fences from string."""
    m = _CODE_FENCE_RE.search(s)
    return m.group(1) if m else s


def _strip_analysis_blocks(s: str) -> str:
    """Remove <analysis>...</analysis> blocks from string."""
    return re.sub(_ANALYSIS_BLOCK_RE, "", s)


def _strip_comments(s: str) -> str:
    """Remove line and block comments from string."""
    return re.sub(_COMMENT_RE, "", s)


def _normalize_quotes(s: str) -> str:
    """Replace smart quotes with standard quotes."""
    for k, v in _SMART_QUOTES.items():
        s = s.replace(k, v)
    return s


def _extract_first_json_block(s: str) -> str | None:
    """Extract first JSON object or array from string.

    Handles nested braces/brackets and string escaping.
    """
    starts = [(s.find("{"), "{"), (s.find("["), "[")]
    starts = [(i, ch) for i, ch in starts if i != -1]
    if not starts:
        return None

    start, opener = min(starts, key=lambda x: x[0])
    closer = "}" if opener == "{" else "]"

    depth = 0
    in_str = False
    esc = False
    quote_char = ""

    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote_char:
                in_str = False
        else:
            if c in ('"', "'"):
                in_str = True
                quote_char = c
            elif c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
    return None


def _repair_json(s: str) -> str:
    """Repair common JSON formatting issues.

    Handles:
    - Comments
    - Smart quotes
    - Python/JavaScript literals
    - Unquoted keys
    - Trailing commas
    """
    s = s.strip()
    s = s.lstrip("\ufeff")
    s = _strip_comments(s)
    s = _normalize_quotes(s)

    # Convert Python/JS literals to JSON
    s = re.sub(r"\bNone\b", "null", s)
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bundefined\b", "null", s)
    s = re.sub(r"\bNaN\b", "null", s)
    s = re.sub(r"\bInfinity\b", "1e9999", s)
    s = re.sub(r"\b-Infinity\b", "-1e9999", s)

    # Fix unquoted keys and trailing commas
    s = re.sub(_UNQUOTED_KEY_RE, r'\g<prefix>"\g<key>"\g<suffix>', s)
    s = re.sub(_TRAILING_COMMA_RE, r"\1", s)

    return s


def parse_llm_json(text: str) -> Any | None:
    """Parse JSON from LLM response with robust error handling.

    Tries to extract and parse JSON from text that may contain:
    - Markdown code fences
    - Surrounding text
    - Comments
    - Non-standard JSON formatting

    Args:
        text: Raw text from LLM response

    Returns:
        Parsed JSON object/array, or None if parsing fails
    """
    if not isinstance(text, str) or not text.strip():
        return None

    raw = _strip_analysis_blocks(text)
    raw = _strip_code_fences(raw)
    candidate = raw.strip()

    if not (candidate.startswith("{") or candidate.startswith("[")):
        block = _extract_first_json_block(candidate)
        if block is None:
            return None
        candidate = block

    try:
        return json.loads(candidate)
    except Exception:
        pass

    repaired = _repair_json(candidate)
    try:
        return json.loads(repaired)
    except Exception:
        return None
