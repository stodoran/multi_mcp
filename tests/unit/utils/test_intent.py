"""Tests for intent extraction utility."""

from multi_mcp.utils.intent import extract_intent


class TestExtractIntent:
    """Tests for extract_intent function."""

    def test_extract_intent_with_backticks(self):
        """Test extraction with **Intent:** `framework` format."""
        content = "**Intent:** `framework`\n\n## Redux vs Zustand..."
        assert extract_intent(content) == "framework"

    def test_extract_intent_without_backticks(self):
        """Test extraction with **Intent:** framework format."""
        content = "**Intent:** infrastructure\n\n## Postgres vs DynamoDB..."
        assert extract_intent(content) == "infrastructure"

    def test_extract_intent_simple_format(self):
        """Test extraction with Intent: format."""
        content = "Intent: debugging\n\nLet me investigate..."
        assert extract_intent(content) == "debugging"

    def test_extract_intent_case_insensitive(self):
        """Test that extraction is case insensitive."""
        content = "**INTENT:** `Architecture`\n\n..."
        assert extract_intent(content) == "architecture"

    def test_extract_intent_with_extra_whitespace(self):
        """Test extraction handles extra whitespace."""
        content = "**Intent:**   `security`\n\n..."
        assert extract_intent(content) == "security"

    def test_extract_intent_not_found_returns_none(self):
        """Test returns None when no intent found."""
        content = "Here is my analysis of the code..."
        assert extract_intent(content) is None

    def test_extract_intent_not_found_returns_default(self):
        """Test returns default when no intent found."""
        content = "Here is my analysis of the code..."
        assert extract_intent(content, default="compare") == "compare"

    def test_extract_intent_in_middle_of_content(self):
        """Test extraction works when intent is in middle of content."""
        content = "Some preamble text\n\n**Intent:** `api_design`\n\nMore content..."
        assert extract_intent(content) == "api_design"

    def test_extract_intent_all_valid_archetypes(self):
        """Test extraction of all valid archetype values."""
        archetypes = [
            "infrastructure",
            "framework",
            "architecture",
            "devops",
            "api_design",
            "data_storage",
            "testing",
            "security",
            "deployment",
            "caching",
            "cicd_pipeline",
            "code_review",
            "debugging",
            "refactoring",
            "system_design",
            "ai_ml_selection",
            "build_vs_buy",
            "team_process",
            "factual",
            "data_analysis",
            "creative",
            "general",
        ]
        for archetype in archetypes:
            content = f"**Intent:** `{archetype}`\n\nContent..."
            assert extract_intent(content) == archetype

    def test_extract_intent_returns_lowercase(self):
        """Test that extracted intent is always lowercase."""
        content = "**Intent:** `FRAMEWORK`\n\n..."
        assert extract_intent(content) == "framework"

    def test_extract_intent_empty_content(self):
        """Test extraction with empty content."""
        assert extract_intent("") is None
        assert extract_intent("", default="chat") == "chat"

    def test_extract_intent_priority_backticks_first(self):
        """Test that backtick format is found first."""
        # Both formats present, backtick should be matched first
        content = "Intent: wrong\n**Intent:** `correct`\nMore content"
        # The function tries patterns in order, so backtick format wins
        assert extract_intent(content) == "correct"
