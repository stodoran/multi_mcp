"""Main API gateway."""
import logging
from typing import Any

logger = logging.getLogger(__name__)

class APIGateway:
    """Main API gateway."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._middleware: Any = None
        self._router: Any = None
        logger.info("Initialized API gateway")

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming request."""
        try:
            response = await self._middleware.process(request)
            return response
        except Exception as e:
            return self._error_handler(e)

    def _error_handler(self, error: Exception) -> dict[str, Any]:
        """Handle errors."""
        logger.error(f"Request error: {error}")
        return {"status": 401, "error": str(error)}

    def set_middleware(self, middleware: Any) -> None:
        """Set middleware chain."""
        self._middleware = middleware

    def set_router(self, router: Any) -> None:
        """Set request router."""
        self._router = router
