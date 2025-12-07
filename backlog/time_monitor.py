"""
Time Monitor - Background task that checks for due reminders and announces them.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from backlog.backlog_manager import BacklogManager

logger = logging.getLogger(__name__)


class TimeMonitor:
    """Monitors time and triggers reminders when they're due."""

    def __init__(
        self,
        user_id: str,
        time_tracker,
        backlog_manager: BacklogManager,
    ):
        """
        Initialize TimeMonitor.

        Args:
            user_id: User identifier
            time_tracker: ClientTimeTracker instance for accurate client time
            backlog_manager: Optional BacklogManager instance
        """
        self.user_id = user_id
        self.time_tracker = time_tracker
        self.backlog_manager = backlog_manager
        self._running = False
        self._task = None
        self._session = None

        logger.info(f"TimeMonitor initialized for user: {user_id}")

    def set_session(self, session):
        """Set the LiveKit session for speaking reminders."""
        self._session = session
        logger.info("Session set for TimeMonitor")

    async def start(self):
        """Start the time monitor background task."""
        if self._running:
            logger.warning("TimeMonitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("🕐 TimeMonitor started")

    async def stop(self):
        """Stop the time monitor background task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("🕐 TimeMonitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop - checks for due reminders every 30 seconds."""
        check_interval = 30  # seconds

        logger.info(f"🕐 Monitor loop started (checking every {check_interval}s)")

        while self._running:
            try:
                await self._check_and_announce_reminders()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)

            # Wait before next check
            await asyncio.sleep(check_interval)

    async def _check_and_announce_reminders(self):
        """Check for due reminders and announce them."""
        try:
            # Get current client time
            if self.time_tracker and self.time_tracker.is_initialized():
                current_time = self.time_tracker.get_current_client_time()
            else:
                current_time = datetime.utcnow()
                logger.warning("Time tracker not initialized, using UTC")

            # Get due reminders
            due_items = self.backlog_manager.get_due_reminders(
                self.user_id, current_time
            )

            if not due_items:
                return  # Nothing due

            logger.info(f"⏰ Found {len(due_items)} due reminder(s)")

            # Announce each reminder
            for item in due_items:
                await self._announce_reminder(item)

        except Exception as e:
            logger.error(f"Error checking reminders: {e}", exc_info=True)

    async def _announce_reminder(self, item: dict):
        """
        Announce a reminder to the user.

        Args:
            item: Reminder item dictionary from DynamoDB
        """
        try:
            title = item.get("title", "something")
            scheduled_time = datetime.fromisoformat(item["scheduled_time"])
            time_display = scheduled_time.strftime("%I:%M %p").lstrip("0")

            # Build announcement message
            announcement = f"Reminder: {title}"

            # Check if it's the exact time or early warning
            remind_before = int(item.get("remind_before_minutes", 0))
            if remind_before > 0:
                if self.time_tracker and self.time_tracker.is_initialized():
                    current_time = self.time_tracker.get_current_client_time()
                else:
                    current_time = datetime.utcnow()

                time_until = scheduled_time - current_time
                minutes_until = int(time_until.total_seconds() / 60)

                if minutes_until > 5:
                    # Early warning
                    if minutes_until >= 60:
                        hours = minutes_until // 60
                        mins = minutes_until % 60
                        if mins > 0:
                            time_desc = f"{hours} hour{'s' if hours > 1 else ''} and {mins} minutes"
                        else:
                            time_desc = f"{hours} hour{'s' if hours > 1 else ''}"
                    else:
                        time_desc = f"{minutes_until} minutes"
                    announcement = (
                        f"Reminder: {title} in {time_desc} (at {time_display})"
                    )
                else:
                    # Close to time or past
                    announcement = f"Reminder: It's time to {title}"
            else:
                # No early warning, announce at exact time
                announcement = f"Reminder: It's time to {title}"

            logger.info(f"🔔 Announcing: {announcement}")

            # Speak the reminder
            if self._session:
                await self._session.say(
                    text=announcement,
                    allow_interruptions=True,
                    add_to_chat_ctx=True,  # Add reminders to chat history
                )
            else:
                logger.error("Session not available, cannot announce reminder")

            # Update last_reminded_at timestamp
            self.backlog_manager.update_reminded_timestamp(
                self.user_id, item["item_id"]
            )

            logger.info(
                f"✅ Reminder announced and timestamp updated: {item['item_id']}"
            )

        except Exception as e:
            logger.error(f"Error announcing reminder: {e}", exc_info=True)
