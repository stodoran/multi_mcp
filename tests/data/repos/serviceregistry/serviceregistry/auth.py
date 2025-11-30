"""Authentication token management.

This module manages authentication tokens for service requests.
"""

import logging
import time

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages authentication tokens with refresh logic."""

    def __init__(self, token_ttl: int = 3600):
        """Initialize token manager.

        Args:
            token_ttl: Token time-to-live in seconds (default 1 hour)
        """
        self._tokens: dict[str, str] = {}
        self._expiry: dict[str, float] = {}
        self._token_ttl = token_ttl

    def get_token(self, service_id: str) -> str | None:
        """Get valid token for a service.

        Args:
            service_id: Service identifier

        Returns:
            Valid token or None if not found/expired
        """
        if service_id not in self._tokens:
            return None

        if time.time() > self._expiry.get(service_id, 0):
            logger.info(f"Token for {service_id} expired, refreshing")
            self._refresh_token(service_id)

        return self._tokens.get(service_id)

    def set_token(self, service_id: str, token: str) -> None:
        """Set token for a service.

        Args:
            service_id: Service identifier
            token: Authentication token
        """
        self._tokens[service_id] = token
        self._expiry[service_id] = time.time() + self._token_ttl
        logger.info(f"Set token for {service_id}")

    def _refresh_token(self, service_id: str) -> None:
        """Refresh token for a service."""
        new_token = f"token_{service_id}_{int(time.time())}"
        self._tokens[service_id] = new_token
        self._expiry[service_id] = time.time() + self._token_ttl

        logger.info(f"Refreshed token for {service_id}")

    def revoke_token(self, service_id: str) -> None:
        """Revoke token for a service.

        Args:
            service_id: Service identifier
        """
        self._tokens.pop(service_id, None)
        self._expiry.pop(service_id, None)
        logger.info(f"Revoked token for {service_id}")

    def is_valid(self, service_id: str, token: str) -> bool:
        """Check if a token is valid.

        Args:
            service_id: Service identifier
            token: Token to validate

        Returns:
            True if token is valid and not expired
        """
        current_token = self.get_token(service_id)
        return current_token == token
