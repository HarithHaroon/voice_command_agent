"""
Data channel sender - Send events to mobile app via LiveKit data channel.
"""

import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DataChannelSender:
    """Sends structured events to mobile app via LiveKit data channel"""

    @staticmethod
    async def send_medication_event(
        session,
        action: str,
        medication_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Send medication event to mobile app.

        Args:
            session: LiveKit session (not used, kept for compatibility)
            action: Event action (medication_added, medication_updated, medication_deleted, dose_confirmed, dose_skipped)
            medication_data: Medication details (name, dosage, times, etc.)
        """
        try:
            from livekit.agents import get_job_context

            ctx = get_job_context()

            if not ctx or not ctx.room:
                logger.error("No room context available to send medication event")
                return

            event = {
                "type": "medication_event",
                "action": action,
                "data": medication_data or {},
            }

            message = json.dumps(event)

            message_bytes = message.encode("utf-8")

            await ctx.room.local_participant.publish_data(message_bytes)

            logger.info(f"📤 Sent medication event to mobile: {action}")
        except Exception as e:
            logger.error(f"Failed to send medication event: {e}")
            # Don't rethrow - medication was still added successfully

    @staticmethod
    async def send_ui_notification(
        title: str,
        message: str,
        notification_type: str = "info",
    ):
        """
        Send UI notification to mobile app.

        Args:
            session: LiveKit session (not used, kept for compatibility)
            title: Notification title
            message: Notification message
            notification_type: Type (success, error, info, warning)
        """
        try:
            from livekit.agents import get_job_context

            ctx = get_job_context()

            if not ctx or not ctx.room:
                logger.error("No room context available to send notification")
                return

            event = {
                "type": "ui_notification",
                "data": {
                    "title": title,
                    "message": message,
                    "notification_type": notification_type,
                },
            }

            message_str = json.dumps(event)

            message_bytes = message_str.encode("utf-8")

            await ctx.room.local_participant.publish_data(message_bytes)

            logger.info(f"📤 Sent UI notification: {title}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
