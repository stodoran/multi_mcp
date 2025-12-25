#!/usr/bin/env bash
# Code quality checks for Multi-MCP
# Enforces KISS, DRY, YAGNI principles
#
# Usage:
#   ./scripts/check.sh        Auto-fix and check (local development)
#   ./scripts/check.sh --ci   Check only, no modifications (CI/pre-commit)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

CI_MODE=false
[[ "$1" == "--ci" ]] && CI_MODE=true

echo "====================================="
if $CI_MODE; then
    echo "Multi-MCP CI Checks (no auto-fix)"
else
    echo "Multi-MCP Code Quality Checks"
fi
echo "====================================="
echo ""

# 1. Formatting
echo -e "${YELLOW}[1/5] Formatting${NC}"
if $CI_MODE; then
    uv run ruff format --check . || { echo -e "${RED}✗ Format check failed${NC}"; exit 1; }
else
    uv run ruff format .
fi
echo -e "${GREEN}✓ Format OK${NC}"
echo ""

# 2. Linting (includes KISS/DRY rules: SIM, PIE, C90)
echo -e "${YELLOW}[2/5] Linting${NC}"
if $CI_MODE; then
    uv run ruff check .
else
    uv run ruff check . --fix
fi
echo -e "${GREEN}✓ Lint OK${NC}"
echo ""

# 3. Type checking
echo -e "${YELLOW}[3/5] Type checking${NC}"
uv run pyright
echo -e "${GREEN}✓ Types OK${NC}"
echo ""

# 4. Dead code detection (YAGNI)
echo -e "${YELLOW}[4/5] Dead code detection${NC}"
uv run vulture multi_mcp/ scripts/vulture_whitelist.py --min-confidence 80 --exclude "multi_mcp/cli.py"
echo -e "${GREEN}✓ No dead code${NC}"
echo ""

# 5. Unit tests
echo -e "${YELLOW}[5/5] Unit tests${NC}"
uv run pytest tests/unit/ -v --tb=short --ignore=tests/unit/test_config.py
echo -e "${GREEN}✓ Tests passed${NC}"
echo ""

echo "====================================="
echo -e "${GREEN}All checks passed!${NC}"
echo "====================================="
