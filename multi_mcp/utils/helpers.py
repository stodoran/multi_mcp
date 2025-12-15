"""General helper functions for the server."""

from importlib.metadata import PackageNotFoundError, version

from pydantic import BaseModel
from pydantic.fields import FieldInfo


def get_version() -> str:
    """Read version from package metadata."""
    try:
        return version("multi-mcp")
    except PackageNotFoundError:
        return "unknown"


def get_field_description(model_class: type[BaseModel], field_name: str) -> str:
    """Extract field description from Pydantic model.

    This enables DRY principle: field descriptions are defined once in the schema
    and automatically extracted for MCP tool documentation.

    Args:
        model_class: Pydantic model class
        field_name: Name of the field to get description for

    Returns:
        Field description string, or default message if not found
    """
    field_info = model_class.model_fields.get(field_name)
    if field_info and isinstance(field_info, FieldInfo):
        return field_info.description or f"{field_name} parameter"
    return f"{field_name} parameter"
