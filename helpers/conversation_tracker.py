"""
Conversation Tracker - Handles emotion check-in Q&A tracking.
"""

import logging
import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from assistant import Assistant

logger = logging.getLogger(__name__)


class ConversationTracker:
    """Tracks conversation flow, especially emotion check-ins."""

    def __init__(self, assistant: "Assistant"):
        """
        Initialize conversation tracker.

        Args:
            assistant: Assistant instance to track
        """
        self.assistant = assistant
        logger.info("ConversationTracker initialized")

    def track_assistant_message(self, content: str) -> None:
        """
        Track assistant's message, especially check-in questions.

        Args:
            content: The assistant's message content
        """
        # Track check-in question asked by assistant
        if self.assistant.pending_check_in:
            # Agent just asked the check-in question
            self.assistant.waiting_for_check_in_response = True

            self.assistant.check_in_question = content

            logger.info(f"✅ Check-in question tracked: {content[:50]}...")

    def track_user_response(self, content: str) -> None:
        """
        Track user's response, especially to check-in questions.

        Args:
            content: The user's message content
        """
        # Track user response to check-in
        if self.assistant.waiting_for_check_in_response:
            logger.info(f"✅ User responded to check-in: {content[:50]}...")

            # Update DynamoDB with Q&A
            asyncio.create_task(
                self.assistant.update_emotion_event_with_interaction(
                    timestamp=self.assistant.pending_check_in["timestamp"],
                    agent_question=self.assistant.check_in_question,
                    user_response=content,
                )
            )

            # Clear tracking state
            self.assistant.waiting_for_check_in_response = False

            self.assistant.pending_check_in = None
