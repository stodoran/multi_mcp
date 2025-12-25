.PHONY: help install install-hooks verify check ci test test-cov test-integration test-all server build publish publish-test clean

# Default target
.DEFAULT_GOAL := help

help:
	@echo "Multi-MCP Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make check            Run all checks with auto-fix (format, lint, types, deadcode, tests)"
	@echo "  make ci               Run all checks WITHOUT auto-fix (for CI/pre-commit)"
	@echo "  make test             Run unit tests"
	@echo "  make test-cov         Run unit tests with coverage (fails if <80%)"
	@echo "  make test-integration Run integration tests (requires API keys)"
	@echo "  make test-all         Run all tests (unit + integration)"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies and setup environment"
	@echo "  make install-hooks    Install git pre-commit hooks"
	@echo "  make verify           Verify installation is working"
	@echo "  make server           Start the MCP server"
	@echo ""
	@echo "Release:"
	@echo "  make build            Build Python package"
	@echo "  make publish          Publish to PyPI"
	@echo "  make publish-test     Publish to TestPyPI"
	@echo "  make clean            Remove build artifacts"

# =============================================================================
# Development
# =============================================================================

check:
	@./scripts/check.sh

ci:
	@./scripts/check.sh --ci

# Note: test_config.py excluded - tests depend on .env values, not portable
PYTEST_UNIT := tests/unit/ --ignore=tests/unit/test_config.py

test:
	uv run pytest $(PYTEST_UNIT) -v

test-cov:
	uv run pytest $(PYTEST_UNIT) --cov=multi_mcp --cov-report=term-missing --cov-fail-under=80

test-integration:
	@./scripts/check-api-keys.sh
	RUN_E2E=1 uv run pytest tests/integration/ -v

test-all: test test-integration

# =============================================================================
# Setup
# =============================================================================

install:
	@./scripts/install.sh

install-hooks:
	@ln -sf ../../.githooks/pre-commit .git/hooks/pre-commit
	@echo "✓ Git hooks installed"

verify:
	@./scripts/verify.sh

server:
	@./scripts/run_server.sh

# =============================================================================
# Release
# =============================================================================

build:
	uv build

publish: build
	uv run twine upload dist/*
	@echo "✓ Published to PyPI"

publish-test: build
	uv run twine upload --repository testpypi dist/*
	@echo "✓ Published to TestPyPI"

clean:
	rm -rf dist/ build/ *.egg-info/ .coverage htmlcov/ .pytest_cache/ .ruff_cache/ .pyright/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned"
