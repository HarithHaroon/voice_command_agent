"""
Assistant Data Handler - Handles incoming data messages.
Refactored to work with SharedState and EmotionHandler.
"""

import json
import logging
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.shared_state import SharedState
    from helpers.emotion_handler import EmotionHandler

logger = logging.getLogger(__name__)


class AssistantDataHandler:
    """Handles data channel messages for the multi-agent system."""

    def __init__(self, shared_state: "SharedState", emotion_handler: "EmotionHandler"):
        """
        Initialize data handler.

        Args:
            shared_state: SharedState instance
            emotion_handler: EmotionHandler instance
        """
        self.shared_state = shared_state

        self.emotion_handler = emotion_handler

        logger.info("AssistantDataHandler initialized")

    def handle_data(self, data, participant=None):
        """
        Handle incoming data and route to appropriate handlers.

        Args:
            data: Raw data packet from LiveKit
            participant: Optional participant info
        """
        logger.info("Data received!")

        try:
            # Extract message bytes
            if hasattr(data, "data"):
                message_bytes = data.data

            else:
                message_bytes = data

            # Parse message
            message = json.loads(message_bytes.decode("utf-8"))

            # logger.info(f"Parsed message: {message}")

            # Route based on message type
            message_type = message.get("type")

            if message_type == "session_init":
                asyncio.create_task(self._handle_session_init(message))

            elif message_type == "tool_result":
                self._handle_tool_result(message)

            elif message_type == "emotion_detected":
                asyncio.create_task(self._handle_emotion_event(message))

            else:
                logger.info(f"Non-tool message type: {message_type}")

        except Exception as e:
            logger.error(f"Data handling error: {e}")

    async def _handle_session_init(self, message: dict):
        """Handle session initialization message."""
        try:
            # Store navigation context
            navigation_data = message.get("navigation", {})

            self.shared_state.navigation_state.initialize_from_session(navigation_data)

            # Initialize time tracker
            client_time = message.get("current_time")

            timezone_offset = message.get("timezone_offset_minutes", 0)

            if client_time:
                self.shared_state.time_tracker.initialize(client_time, timezone_offset)

                logger.info(f"🕐 Client time received: {client_time}")

                logger.info(f"🕐 Timezone offset: {timezone_offset} minutes")

                logger.info(
                    f"🕐 Formatted time: {self.shared_state.time_tracker.get_formatted_datetime()}"
                )

        except Exception as e:
            logger.error(f"Error handling session_init: {e}", exc_info=True)

    def _handle_tool_result(self, message: dict):
        """Handle tool result message."""
        try:
            # Route through tool manager
            success = self.shared_state.tool_manager.route_tool_response(message)

            if not success:
                logger.error("Failed to route tool response")

            # Update navigation state if this was a successful navigation
            if (
                message.get("tool") == "navigate_to_screen"
                and message.get("success")
                and "result" in message
            ):
                result = message.get("result", {})

                if "navigation_stack" in result and "current_screen" in result:
                    self.shared_state.navigation_state.update_from_navigation_success(
                        result["navigation_stack"], result["current_screen"]
                    )

        except Exception as e:
            logger.error(f"Error handling tool_result: {e}", exc_info=True)

    async def _handle_emotion_event(self, event: dict):
        """
        Handle emotion/voice quality detection event from Flutter.
        Routes to EmotionHandler.

        Args:
            event: Emotion event data
        """
        try:
            # Route to emotion handler
            await self.emotion_handler.handle_emotion_event(event)

        except Exception as e:
            logger.error(f"❌ Error routing emotion event: {e}", exc_info=True)
