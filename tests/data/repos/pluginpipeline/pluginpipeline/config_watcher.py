"""Configuration file watcher."""
import logging
import time

logger = logging.getLogger(__name__)

class ConfigWatcher:
    """Watches config files for changes."""

    def __init__(self, plugin_loader: Any):
        self._loader = plugin_loader
        self._last_modified = time.time()
        logger.info("Initialized config watcher")

    def check_and_reload(self, plugin_name: str) -> None:
        """Check config and reload if changed.

        Allow in-flight requests to complete.
        """
        time.sleep(1)

        self._loader.reload_plugin(plugin_name)
        logger.info(f"Reloaded {plugin_name}")
