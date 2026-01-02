"""
Conversation Tracker - Simplified to work with EmotionHandler.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from helpers.emotion_handler import EmotionHandler

logger = logging.getLogger(__name__)


class ConversationTracker:
    """
    Tracks conversation flow and routes to EmotionHandler for check-ins.
    """

    def __init__(self, emotion_handler: "EmotionHandler"):
        """
        Initialize conversation tracker.

        Args:
            emotion_handler: EmotionHandler instance for check-in tracking
        """
        self.emotion_handler = emotion_handler
        logger.info("ConversationTracker initialized")

    def track_assistant_message(self, content: str) -> None:
        """
        Track assistant's message.

        Currently just logs - emotion handler speaks check-ins directly.

        Args:
            content: The assistant's message content
        """
        logger.debug(f"Assistant message: {content[:50]}...")

    def track_user_response(self, content: str) -> None:
        """
        Track user's response, checking if it's a check-in response.

        Args:
            content: The user's message content
        """
        # Route to emotion handler to check if this is a check-in response
        self.emotion_handler.track_user_response(content)

        logger.debug(f"User message: {content[:50]}...")
