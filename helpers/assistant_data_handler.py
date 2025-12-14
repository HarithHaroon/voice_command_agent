"""
Assistant Data Handler - Handles incoming data messages and emotion events.
"""

import json
import logging
import asyncio
from typing import TYPE_CHECKING
from livekit.agents import get_job_context

if TYPE_CHECKING:
    from assistant import Assistant

logger = logging.getLogger(__name__)


class AssistantDataHandler:
    """Handles data channel messages and emotion events for the assistant."""

    def __init__(self, assistant: "Assistant"):
        """
        Initialize data handler.

        Args:
            assistant: Assistant instance to handle data for
        """
        self.assistant = assistant

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

            logger.info(f"Parsed message: {message}")

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

            self.assistant.navigation_state.initialize_from_session(navigation_data)

            # Initialize time tracker
            client_time = message.get("current_time")

            timezone_offset = message.get("timezone_offset_minutes", 0)

            if client_time:
                self.assistant.time_tracker.initialize(client_time, timezone_offset)
                logger.info(f"🕐 Client time received: {client_time}")
                logger.info(f"🕐 Timezone offset: {timezone_offset} minutes")
                logger.info(
                    f"🕐 Formatted time: {self.assistant.time_tracker.get_formatted_datetime()}"
                )

                # Rebuild instructions with accurate client time
                updated_instructions = self.assistant.module_manager.assemble_instructions(
                    modules=self.assistant.current_modules,
                    current_time=self.assistant.time_tracker.get_formatted_datetime(),
                )

                # Update agent instructions
                await self.assistant.update_instructions(updated_instructions)
                logger.info(
                    f"Updated instructions with client time: {self.assistant.time_tracker.get_formatted_datetime()}"
                )

        except Exception as e:
            logger.error(f"Error handling session_init: {e}", exc_info=True)

    def _handle_tool_result(self, message: dict):
        """Handle tool result message."""
        try:
            # Route through tool manager
            success = self.assistant.tool_manager.route_tool_response(message)

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
                    self.assistant.navigation_state.update_from_navigation_success(
                        result["navigation_stack"], result["current_screen"]
                    )

        except Exception as e:
            logger.error(f"Error handling tool_result: {e}", exc_info=True)

    async def _handle_emotion_event(self, event: dict):
        """Handle emotion/voice quality detection event from Flutter."""
        try:
            emotion_type = event.get("emotion_type")

            severity = event.get("severity")

            check_in_message = event.get("check_in_message")

            timestamp = event.get("timestamp")

            logger.info(f"🎭 Emotion event received: {emotion_type} ({severity})")

            # If already waiting for response, ignore new events
            if self.assistant.waiting_for_check_in_response:
                logger.info(
                    f"⏭️ Skipping - already waiting for response to previous check-in"
                )
                return

            # Store event for tracking Q&A
            self.assistant.pending_check_in = {
                "type": emotion_type,
                "severity": severity,
                "message": check_in_message,
                "timestamp": timestamp,
            }

            # Ask check-in question via TTS
            await self._ask_check_in_question(check_in_message)

        except Exception as e:
            logger.error(f"❌ Error handling emotion event: {e}", exc_info=True)

    async def _ask_check_in_question(self, check_in_message: str):
        """Speak check-in question directly via TTS."""
        try:
            session = getattr(self.assistant.tool_manager, "agent_session", None)

            if not session:
                logger.error("Session not available for check-in")
                return

            logger.info(f"🎤 Speaking check-in: {check_in_message}")

            await session.say(
                text=check_in_message,
                allow_interruptions=True,
                add_to_chat_ctx=True,  # Add to history to track Q&A
            )

            logger.info("✅ Check-in question spoken")

        except Exception as e:
            logger.error(f"❌ Error speaking check-in: {e}", exc_info=True)

    async def update_emotion_event_with_interaction(
        self, timestamp: str, agent_question: str, user_response: str
    ):
        """Update emotion event in DynamoDB with agent question and user response."""
        try:
            logger.info(f"📝 Updating emotion event: {timestamp[:19]}")

            # Get job context to access room for sending update back to Flutter
            ctx = get_job_context()

            # Send update message to Flutter to trigger DynamoDB update
            if ctx and ctx.room:
                message = {
                    "type": "update_emotion_event",
                    "timestamp": timestamp,
                    "agent_question": agent_question,
                    "user_response": user_response,
                }

                message_bytes = json.dumps(message).encode("utf-8")

                await ctx.room.local_participant.publish_data(message_bytes)

                logger.info(f"✅ Sent update request to Flutter")
            else:
                logger.error("No room context available to send update")

        except Exception as e:
            logger.error(f"❌ Error updating emotion event: {e}", exc_info=True)
