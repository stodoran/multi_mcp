"""Plugin loading and hot-reload."""
import importlib
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

class PluginLoader:
    """Loads and manages plugins."""

    def __init__(self):
        self._plugins: dict[str, Any] = {}
        logger.info("Initialized plugin loader")

    def load_plugin(self, name: str, module_path: str) -> Any:
        """Load a plugin module."""
        try:
            module = importlib.import_module(module_path)
            self._plugins[name] = module
            logger.info(f"Loaded plugin {name}")
            return module
        except Exception as e:
            logger.error(f"Failed to load {name}: {e}")
            return None

    def reload_plugin(self, name: str) -> None:
        """Hot-reload a plugin.

        Deletes from sys.modules and reimports.
        Each plugin has isolated module namespace.
        """
        if name in self._plugins:
            module = self._plugins[name]
            module_name = module.__name__

            if module_name in sys.modules:
                del sys.modules[module_name]

            self._plugins[name] = importlib.import_module(module_name)
            logger.info(f"Reloaded plugin {name}")

    def get_plugin(self, name: str) -> Any:
        """Get loaded plugin."""
        return self._plugins.get(name)
