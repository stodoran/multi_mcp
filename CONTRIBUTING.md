# Contributing to Multi-MCP

Thanks for your interest in contributing! This guide will help you get started.

## Quick Start

1. **Fork and clone** the repository
2. **Install dependencies:** `uv sync`
3. **Create a branch:** `git checkout -b feature-name`
4. **Make your changes**
5. **Run tests:** `uv run pytest tests/unit/`
6. **Submit a PR**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/multi_mcp.git
cd multi_mcp

# Install dependencies
uv sync

# Create .env file
cp .env.example .env
# Add at least one API key to .env
```

## Before Submitting a PR

Run these commands to ensure your code passes CI:

```bash
# Run unit tests (~2s)
uv run pytest tests/unit/ -v

# Type checking
uv run pyright

# Linting
uv run ruff check .

# Format code
uv run ruff format .
```

## Code Standards

- **Python 3.13+** required
- **Type hints** on all functions
- **Async-first** - use `async def` for I/O operations
- **Test coverage** - add tests for new features
- **Line length** - 120 characters max

## Project Structure

```
src/
├── server.py          # MCP server
├── cli.py             # CLI tool
├── schemas/           # Pydantic models
├── tools/             # Tool implementations
├── models/            # LLM config & client
└── utils/             # Utilities
```

## Testing

```bash
# Unit tests only (fast)
uv run pytest tests/unit/

# Integration tests (requires API keys)
RUN_E2E=1 uv run pytest tests/integration/

# All tests
RUN_E2E=1 uv run pytest
```

## Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/religa/multi_mcp/issues/new) and include:
- **Bugs:** Description, steps to reproduce, expected vs actual behavior, environment details
- **Features:** Description, use case, proposed solution

## Pull Request Process

1. **Create an issue first** (for major changes)
2. **Keep PRs focused** - one feature/fix per PR
3. **Add tests** for new functionality
4. **Update docs** if you change APIs
5. **Ensure CI passes** before requesting review

## Questions?

Open an issue with the "Question" type and we'll help you out!
