"""
Emotion Handler - Manages emotion detection check-ins independently of agent routing.
"""

import json
import logging
import asyncio
from typing import Optional
from livekit.agents import get_job_context
from livekit.agents import AgentSession
from models.shared_state import SharedState

logger = logging.getLogger(__name__)


class EmotionHandler:
    """
    Handles emotion detection events and check-in Q&A tracking.

    This operates at the session level, independent of which agent is active.
    When Flutter detects concerning emotions (agitation, distress), this handler
    asks check-in questions and tracks the user's responses.
    """

    def __init__(self, session: AgentSession, user_id: str, shared_state: SharedState):
        """
        Initialize emotion handler.

        Args:
            session: AgentSession instance for speaking
            user_id: User identifier for DynamoDB updates
        """
        self.session = session

        self.user_id = user_id

        # Check-in tracking state
        self.pending_check_in: Optional[dict] = None

        self.waiting_for_response: bool = False

        self.check_in_question: Optional[str] = None

        self.session = session

        self.shared_state = shared_state

        self.waiting_for_response = False

        self.check_in_question = None

        self.last_check_in_time = None

        self.check_in_cooldown = 300  # 5 minutes between check-ins

        logger.info("EmotionHandler initialized")

    async def handle_emotion_event(self, event: dict) -> None:
        """
        Handle emotion detection event from Flutter.

        Args:
            event: Emotion event with type, severity, message, timestamp
        """
        try:
            emotion_type = event.get("emotion_type")

            severity = event.get("severity")

            check_in_message = event.get("check_in_message")

            timestamp = event.get("timestamp")

            logger.info(f"🎭 Emotion event: {emotion_type} ({severity})")

            # If already waiting for response, ignore new events
            if self.waiting_for_response:
                logger.info("⏭️ Skipping - already waiting for check-in response")

                return

            # Store event for Q&A tracking
            self.pending_check_in = {
                "type": emotion_type,
                "severity": severity,
                "message": check_in_message,
                "timestamp": timestamp,
            }

            # Ask check-in question
            await self._ask_check_in_question(check_in_message)

        except Exception as e:
            logger.error(f"❌ Error handling emotion event: {e}", exc_info=True)

    async def _ask_check_in_question(self, check_in_message: str):
        """Ask an emotion check-in question."""
        try:
            # Check if transitioning between agents
            if self.shared_state.is_transitioning:
                logger.info(f"⏸️ Skipping check-in during agent transition")
                return

            # Check if session is still active
            if not self.session:
                logger.info(f"⏸️ Skipping check-in - no session")
                return

            # NEW: Check if speech scheduling is available
            if hasattr(self.session, "_speech_state"):
                speech_state = getattr(self.session, "_speech_state", None)

                if speech_state and speech_state in ["draining", "paused", "pausing"]:
                    logger.info(f"⏸️ Skipping check-in - speech is {speech_state}")

                    return

            logger.info(f"🎤 Speaking check-in: {check_in_message}")

            # Store the question we asked
            self.check_in_question = check_in_message

            # Mark that we're waiting for response
            self.waiting_for_response = True

            await self.session.say(
                check_in_message,
                add_to_chat_ctx=True,
            )

        except RuntimeError as e:
            if "isn't running" in str(e) or "speech scheduling" in str(e):
                logger.info(f"⏸️ Session not ready, skipping check-in")
            else:
                logger.error(f"❌ Error speaking check-in: {e}")

            # Reset waiting state on error
            self.waiting_for_response = False

            self.check_in_question = None

        except Exception as e:
            if "speech scheduling" in str(e):
                logger.info(f"⏸️ Speech paused, skipping check-in")
            else:
                logger.error(f"❌ Error speaking check-in: {e}")

            # Reset waiting state on error
            self.waiting_for_response = False

            self.check_in_question = None

    def track_user_response(self, user_message: str) -> None:
        """
        Track user's response to check-in question.

        Args:
            user_message: User's response message
        """
        if not self.waiting_for_response:
            return

        logger.info(f"✅ User responded to check-in: {user_message[:50]}...")

        # Update DynamoDB with Q&A
        if self.pending_check_in and self.check_in_question:
            asyncio.create_task(
                self._update_emotion_event_with_interaction(
                    timestamp=self.pending_check_in["timestamp"],
                    agent_question=self.check_in_question,
                    user_response=user_message,
                )
            )

        # Clear tracking state
        self.waiting_for_response = False

        self.pending_check_in = None

        self.check_in_question = None

    async def _update_emotion_event_with_interaction(
        self, timestamp: str, agent_question: str, user_response: str
    ) -> None:
        """
        Update emotion event in DynamoDB with Q&A interaction.

        Args:
            timestamp: Event timestamp
            agent_question: Question asked by agent
            user_response: User's response
        """
        try:
            logger.info(f"📝 Updating emotion event: {timestamp[:19]}")

            # Get job context to send update to Flutter
            ctx = get_job_context()

            if ctx and ctx.room:
                message = {
                    "type": "update_emotion_event",
                    "timestamp": timestamp,
                    "agent_question": agent_question,
                    "user_response": user_response,
                }

                message_bytes = json.dumps(message).encode("utf-8")

                await ctx.room.local_participant.publish_data(message_bytes)

                logger.info("✅ Sent emotion event update to Flutter")
            else:
                logger.error("No room context available to send update")

        except Exception as e:
            logger.error(f"❌ Error updating emotion event: {e}", exc_info=True)
