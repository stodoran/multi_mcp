"""Multi-MCP: Multi-model AI orchestration MCP server for code review."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("multi-mcp")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["__version__"]
