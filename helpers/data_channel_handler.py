"""
Data Channel Handler - Manages communication with Flutter client.
"""

import logging
import json
from livekit import rtc

logger = logging.getLogger(__name__)


class DataChannelHandler:
    """Handles data channel communication with Flutter client."""

    def __init__(self, room: rtc.Room):
        """
        Initialize data channel handler.

        Args:
            room: LiveKit room instance
        """
        self.room = room
        logger.info("DataChannelHandler initialized")

    async def send_conversation_message(self, role: str, content: str) -> None:
        """
        Send conversation message to Flutter client.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content
        """
        try:
            message = {
                "type": "conversation_message",
                "role": role,
                "content": content,
            }

            message_bytes = json.dumps(message).encode("utf-8")

            await self.room.local_participant.publish_data(message_bytes)

            logger.info(f"📤 Sent {role} message to client")

        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
