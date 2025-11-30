"""Main pipeline orchestration."""
import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

class Pipeline:
    """Data processing pipeline."""

    def __init__(self):
        self._buffer = deque()
        self._plugins: list[Any] = []
        logger.info("Initialized pipeline")

    def add_plugin(self, plugin: Any) -> None:
        """Add plugin to pipeline."""
        self._plugins.append(plugin)

    def process(self, data: Any) -> Any:
        """Process data through pipeline."""
        self._buffer.append(data)

        for plugin in self._plugins:
            data = plugin.process(data)

        return data

    def get_buffer_size(self) -> int:
        """Get buffer size."""
        return len(self._buffer)
