"""Plugin isolation mechanisms."""
import logging
import sys

logger = logging.getLogger(__name__)

class PluginIsolation:
    """Provides isolation for plugins."""

    def __init__(self):
        self._namespaces = {}
        logger.info("Initialized plugin isolation")

    def create_namespace(self, plugin_name: str) -> dict:
        """Create isolated namespace for plugin."""
        namespace = {}
        self._namespaces[plugin_name] = namespace
        logger.info(f"Created namespace for {plugin_name}")
        return namespace

    def cleanup_namespace(self, plugin_name: str) -> None:
        """Cleanup plugin namespace."""
        if plugin_name in self._namespaces:
            del self._namespaces[plugin_name]

        if plugin_name in sys.modules:
            del sys.modules[plugin_name]

        logger.info(f"Cleaned up {plugin_name}")
