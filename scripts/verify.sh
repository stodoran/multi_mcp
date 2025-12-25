#!/usr/bin/env bash
# Verify Multi-MCP installation

set -e

echo "Verifying Multi-MCP installation..."

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found. Run 'make install' first."
    exit 1
fi
echo "✓ Virtual environment exists"

# Check .env file
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Run 'make install' to generate it."
    exit 1
fi
echo "✓ .env file exists"

# Check server module loads
uv run python -c "from multi_mcp.server import mcp; print('✓ Server module loads correctly')" || {
    echo "ERROR: Server module failed to load"
    exit 1
}

echo ""
echo "Installation verified! Next steps:"
echo "1. Add API keys to .env file"
echo "2. Configure your MCP client (see README.md)"
echo "3. Run: make server"
