"""Configuration management for workflow engine.

This module loads configuration from multiple sources with precedence rules.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from .plugins import PluginRegistry, default_logging_plugin, default_monitoring_plugin

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager with multi-source loading."""

    def __init__(self, config_file: str | None = None):
        """Initialize configuration.

        Args:
            config_file: Optional path to config file
        """
        self._config: dict[str, Any] = {}
        self._defaults: dict[str, Any] = {
            'max_workers': 4,
            'timeout': 30,
            'retry_attempts': 3,
            'enable_logging': True,
            'enable_monitoring': False,
            'log_level': 'INFO'
        }

        self._load_defaults()

        if config_file:
            self._load_from_file(config_file)

        self._load_from_env()

        try:
            PluginRegistry.register('logging', default_logging_plugin)
            PluginRegistry.register('monitoring', default_monitoring_plugin)
        except AttributeError as e:
            logger.error(f"Failed to register default plugins: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    def _load_defaults(self) -> None:
        """Load default configuration values."""
        self._config.update(self._defaults)
        logger.debug("Loaded default configuration")

    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from file.

        Args:
            config_file: Path to configuration file
        """
        config_path = Path(config_file)

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_file}")
            return

        try:
            with open(config_path) as f:
                file_config = json.load(f)

            self._config.update(file_config)
            logger.info(f"Loaded configuration from {config_file}")

        except Exception as e:
            logger.error(f"Failed to load config file: {e}")

    def _load_from_env(self) -> None:
        """Load configuration from environment variables.

        Environment variables override file and defaults.
        Expects variables in format: WORKFLOW_KEY_NAME
        """
        prefix = "WORKFLOW_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()

                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    parsed_value = value

                self._config[config_key] = parsed_value
                logger.debug(f"Loaded env override: {config_key}")

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled.

        Args:
            plugin_name: Plugin name

        Returns:
            True if plugin is enabled
        """
        return self.get(f'enable_{plugin_name}', False)

    def get_file_path(self) -> str:
        """Get the configuration file path."""
        return self._config.get('_config_file_path', '')


_global_config = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config
