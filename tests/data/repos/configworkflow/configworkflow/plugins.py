"""Plugin registry for dynamic plugin loading.

This module manages workflow plugins and extensions.
"""

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for workflow plugins."""

    _instance = None
    _plugins: dict[str, Callable] = {}

    def __new__(cls):
        """Singleton pattern for plugin registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, name: str, plugin: Callable) -> None:
        """Register a plugin.

        Args:
            name: Plugin name
            plugin: Plugin function
        """
        if not hasattr(cls, '_plugins'):
            cls._plugins = {}

        cls._plugins[name] = plugin
        logger.info(f"Registered plugin: {name}")

    @classmethod
    def get_plugin(cls, name: str) -> Callable:
        """Get a registered plugin.

        Args:
            name: Plugin name

        Returns:
            Plugin function or None
        """
        if not hasattr(cls, '_plugins'):
            cls._plugins = {}

        plugin = cls._plugins.get(name)

        if plugin is None:
            logger.warning(f"Plugin {name} not found")

        return plugin

    @classmethod
    def list_plugins(cls) -> dict[str, Callable]:
        """List all registered plugins."""
        if not hasattr(cls, '_plugins'):
            cls._plugins = {}
        return dict(cls._plugins)


def default_logging_plugin(**kwargs) -> None:
    """Default logging plugin."""
    logger.info(f"Default logging plugin executed: {kwargs}")


def default_monitoring_plugin(**kwargs) -> None:
    """Default monitoring plugin."""
    logger.info(f"Default monitoring plugin executed: {kwargs}")


def default_notification_plugin(**kwargs) -> None:
    """Default notification plugin."""
    logger.info(f"Default notification plugin executed: {kwargs}")
