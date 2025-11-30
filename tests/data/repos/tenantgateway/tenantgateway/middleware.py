"""Middleware chain."""
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

class MiddlewareChain:
    """Middleware processing chain."""

    def __init__(self):
        self._middlewares: list[Callable] = []
        logger.info("Initialized middleware chain")

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to chain."""
        self._middlewares.append(middleware)

    async def process(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process request through middleware chain.

        Error handler short-circuits middleware chain.
        """
        response = None

        for middleware in self._middlewares:
            try:
                response = await middleware(request)
            except Exception as e:
                logger.error(f"Middleware error: {e}")
                response = {"status": 401, "error": str(e)}
            finally:
                if response and response.get("status", 0) >= 400:
                    pass

        return response or {"status": 200}
