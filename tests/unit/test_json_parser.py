"""Tests for JSON parser."""

from src.utils.json_parser import parse_llm_json


def test_parse_simple_json():
    """Test parsing simple JSON."""
    result = parse_llm_json('{"status": "no_issues_found", "message": "Great"}')
    assert result == {"status": "no_issues_found", "message": "Great"}


def test_parse_with_markdown_fence():
    """Test parsing JSON in markdown fence."""
    content = """```json
{"status": "no_issues_found", "message": "Excellent code"}
```"""
    result = parse_llm_json(content)
    assert result["status"] == "no_issues_found"
    assert result["message"] == "Excellent code"


def test_parse_with_markdown_fence_no_language():
    """Test parsing JSON in markdown fence without language tag."""
    content = """```
{"status": "no_issues_found", "message": "Good"}
```"""
    result = parse_llm_json(content)
    assert result["status"] == "no_issues_found"


def test_parse_trailing_comma():
    """Test repairing trailing commas."""
    result = parse_llm_json('{"a": 1, "b": 2,}')
    assert result == {"a": 1, "b": 2}


def test_parse_trailing_comma_in_array():
    """Test repairing trailing commas in arrays."""
    result = parse_llm_json('{"arr": [1, 2, 3,]}')
    assert result == {"arr": [1, 2, 3]}


def test_parse_unquoted_keys():
    """Test repairing unquoted keys."""
    result = parse_llm_json('{foo: "bar", baz: 123}')
    assert result == {"foo": "bar", "baz": 123}


def test_parse_python_true():
    """Test converting Python True literal."""
    result = parse_llm_json('{"a": True}')
    assert result == {"a": True}


def test_parse_python_false():
    """Test converting Python False literal."""
    result = parse_llm_json('{"a": False}')
    assert result == {"a": False}


def test_parse_python_none():
    """Test converting Python None literal."""
    result = parse_llm_json('{"a": None}')
    assert result == {"a": None}


def test_parse_python_literals_combined():
    """Test converting multiple Python literals."""
    result = parse_llm_json('{"a": True, "b": False, "c": None}')
    assert result == {"a": True, "b": False, "c": None}


def test_parse_with_line_comments():
    """Test stripping line comments."""
    result = parse_llm_json("""
    {
        "status": "no_issues_found", // This is a comment
        "message": "Good"
    }
    """)
    assert result["status"] == "no_issues_found"


def test_parse_with_block_comments():
    """Test stripping block comments."""
    result = parse_llm_json("""
    {
        "status": "no_issues_found",
        /* Block comment here */
        "message": "Good"
    }
    """)
    assert result["status"] == "no_issues_found"


def test_parse_json_in_text():
    """Test extracting JSON from surrounding text."""
    result = parse_llm_json('Here is the response: {"status": "ok", "value": 123} and more text')
    assert result == {"status": "ok", "value": 123}


def test_parse_json_with_prefix_text():
    """Test extracting JSON when preceded by text."""
    content = """The analysis is complete.

{
  "status": "no_issues_found",
  "message": "Code is excellent"
}"""
    result = parse_llm_json(content)
    assert result["status"] == "no_issues_found"


def test_parse_files_required_response():
    """Test parsing files_required special case."""
    content = """{
  "status": "files_required_to_continue",
  "message": "Need auth module",
  "files_needed": ["auth.py", "models/"]
}"""
    result = parse_llm_json(content)
    assert result["status"] == "files_required_to_continue"
    assert len(result["files_needed"]) == 2
    assert "auth.py" in result["files_needed"]


def test_parse_non_json():
    """Test that non-JSON returns None."""
    result = parse_llm_json("This is just plain text with no JSON")
    assert result is None


def test_parse_empty():
    """Test that empty string returns None."""
    result = parse_llm_json("")
    assert result is None


def test_parse_whitespace_only():
    """Test that whitespace-only string returns None."""
    result = parse_llm_json("   \n\t  ")
    assert result is None


def test_parse_invalid_json():
    """Test that completely broken JSON returns None."""
    result = parse_llm_json("{this is broken json")
    assert result is None


def test_parse_none_input():
    """Test that None input returns None."""
    result = parse_llm_json(None)  # type: ignore
    assert result is None


def test_parse_smart_quotes():
    """Test handling of smart quotes around keys."""
    # Smart quotes around the key
    result = parse_llm_json('{"message": "Code is excellent"}')
    assert result is not None
    assert "message" in result


def test_parse_array():
    """Test parsing JSON array."""
    result = parse_llm_json("[1, 2, 3]")
    assert result == [1, 2, 3]


def test_parse_nested_objects():
    """Test parsing nested JSON objects."""
    result = parse_llm_json('{"outer": {"inner": "value"}}')
    assert result == {"outer": {"inner": "value"}}


def test_parse_combined_issues():
    """Test handling multiple malformations at once."""
    content = """```json
{
  status: "no_issues_found",  // Comment here
  message: "Great code",
}
```"""
    result = parse_llm_json(content)
    assert result is not None
    assert result["status"] == "no_issues_found"


def test_parse_with_analysis_block():
    """Test stripping <analysis> block before parsing JSON."""
    content = """<analysis>
1. VERIFICATION:
   - Issue "SQL injection": Confirmed. Fix required.
   - Issue "Missing import": False positive. The code handles this in line 45. Discarding.
2. DISCOVERY:
   - Found potential race condition in file.py:12.
</analysis>

```json
{
  "status": "issues_found",
  "issues_found": [
    {"severity": "high", "location": "db.py:23", "description": "SQL injection"}
  ]
}
```"""
    result = parse_llm_json(content)
    assert result is not None
    assert result["status"] == "issues_found"
    assert len(result["issues_found"]) == 1
    assert result["issues_found"][0]["severity"] == "high"


def test_parse_with_analysis_block_no_fence():
    """Test stripping <analysis> block when JSON is not in a fence."""
    content = """<analysis>
1. VERIFICATION:
   - Issue "X": Confirmed.
</analysis>

{"status": "no_issues_found", "message": "All clear"}"""
    result = parse_llm_json(content)
    assert result is not None
    assert result["status"] == "no_issues_found"


def test_parse_with_analysis_block_inline():
    """Test stripping <analysis> block that appears inline with JSON."""
    content = """<analysis>Quick check: all good</analysis>{"status": "ok"}"""
    result = parse_llm_json(content)
    assert result is not None
    assert result["status"] == "ok"
