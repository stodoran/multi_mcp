"""Pytest configuration for multi_mcp tests."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
async def clear_conversation_store():
    """Clear conversation store between tests to prevent state leakage."""
    yield  # Run the test first

    # Clear the global store after each test
    from src.memory.store import _threads

    _threads.clear()


@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with standard structure."""
    project = tmp_path / "test_project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Test Project\n")
    return project


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Provide mock environment variables for testing."""
    test_vars = {
        "OPENAI_API_KEY": "sk-test-key-12345",
        "DEFAULT_MODEL": "gpt-5-mini",
        "LOG_LEVEL": "INFO",
    }
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    return test_vars


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (>5s)")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their location."""
    for item in items:
        # Auto-mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # Auto-mark unit tests
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
