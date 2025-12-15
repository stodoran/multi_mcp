"""Path resolution and validation utilities."""

from pathlib import Path

# User data directory: ~/.multi_mcp/
USER_DATA_DIR = Path.home() / ".multi_mcp"
LOGS_DIR = USER_DATA_DIR / "logs"

# Track if logs directory has been initialized
_logs_dir_initialized = False


def ensure_logs_dir() -> Path:
    """Ensure logs directory exists (lazy initialization).

    Call this before writing to LOGS_DIR. Safe to call multiple times.

    Returns:
        Path to the logs directory
    """
    global _logs_dir_initialized
    if not _logs_dir_initialized:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        _logs_dir_initialized = True
    return LOGS_DIR


def resolve_path(file_path: str, base_path: str) -> str:
    """Resolve and validate file path within base_path.

    Security: Path.resolve() follows symlinks, then relative_to() ensures
    the final resolved path is within base_path (prevents traversal attacks).

    Args:
        file_path: File path (absolute or relative)
        base_path: Base directory path (absolute)

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If resolved path escapes base_path
    """
    base = Path(base_path).resolve()

    if Path(file_path).is_absolute():
        resolved = Path(file_path).resolve()
    else:
        resolved = (base / file_path).resolve()

    # Security: Ensure resolved path is within base_path
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Path {file_path} escapes base_path {base_path}") from None

    return str(resolved)
