"""Communication protocol for inter-node messaging."""

import logging
from typing import Any

from .node import CacheNode
from .storage import CacheEntry

logger = logging.getLogger(__name__)


class CacheProtocol:
    """Protocol for cache node communication.

    Handles serialization and transmission of cache operations
    between nodes.
    """

    def __init__(self, local_node: CacheNode):
        """Initialize protocol.

        Args:
            local_node: Local cache node
        """
        self.local_node = local_node
        self._message_handlers: dict[str, Any] = {}
        logger.info(f"Initialized protocol for node {local_node.node_id}")

    def send_replicate(
        self,
        target: CacheNode,
        key: str,
        value: Any,
        expiry_time: float,
        metadata: dict | None = None
    ) -> bool:
        """Send replication command to target node.

        Command format doesn't include hash value for verification.

        Args:
            target: Target node
            key: Cache key
            value: Value to replicate
            expiry_time: Expiry timestamp
            metadata: Optional metadata

        Returns:
            True if sent successfully
        """
        message = {
            "type": "replicate",
            "from": self.local_node.node_id,
            "key": key,
            "value": value,
            "expiry_time": expiry_time,
            "metadata": metadata or {}
        }

        try:
            logger.debug(f"Sending replicate for {key} to {target.node_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send replicate to {target.node_id}: {e}")
            return False

    def send_delete(self, target: CacheNode, key: str) -> bool:
        """Send delete command to target node.

        Args:
            target: Target node
            key: Key to delete

        Returns:
            True if sent successfully
        """
        message = {
            "type": "delete",
            "from": self.local_node.node_id,
            "key": key
        }

        try:
            logger.debug(f"Sending delete for {key} to {target.node_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send delete to {target.node_id}: {e}")
            return False

    def send_invalidate(self, target: CacheNode, key: str) -> bool:
        """Send invalidation command to target node.

        Args:
            target: Target node
            key: Key to invalidate

        Returns:
            True if sent successfully
        """
        message = {
            "type": "invalidate",
            "from": self.local_node.node_id,
            "key": key
        }

        try:
            logger.debug(f"Sending invalidate for {key} to {target.node_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send invalidate to {target.node_id}: {e}")
            return False

    def request_key(self, target: CacheNode, key: str) -> CacheEntry | None:
        """Request a key from target node.

        Args:
            target: Target node
            key: Key to request

        Returns:
            Cache entry or None
        """
        message = {
            "type": "request",
            "from": self.local_node.node_id,
            "key": key
        }

        try:
            logger.debug(f"Requesting key {key} from {target.node_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to request key from {target.node_id}: {e}")
            return None

    def send_heartbeat(self, target: CacheNode) -> bool:
        """Send heartbeat to target node.

        Args:
            target: Target node

        Returns:
            True if sent successfully
        """
        message = {
            "type": "heartbeat",
            "from": self.local_node.node_id,
            "timestamp": self.local_node._get_current_time()
        }

        try:
            return True
        except Exception as e:
            logger.error(f"Failed to send heartbeat to {target.node_id}: {e}")
            return False

    def register_handler(self, message_type: str, handler: Any) -> None:
        """Register a message handler.

        Args:
            message_type: Type of message
            handler: Handler function
        """
        self._message_handlers[message_type] = handler
        logger.debug(f"Registered handler for {message_type}")

    def handle_message(self, message: dict[str, Any]) -> Any:
        """Handle incoming message.

        Args:
            message: Message dictionary

        Returns:
            Handler result
        """
        msg_type = message.get("type")
        handler = self._message_handlers.get(msg_type)

        if handler:
            return handler(message)
        else:
            logger.warning(f"No handler for message type {msg_type}")
            return None
