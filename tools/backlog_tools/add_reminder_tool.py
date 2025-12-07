"""
AddReminderTool - Create new reminders for the user.
"""

import logging
from datetime import datetime
from typing import List

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from backlog.backlog_manager import BacklogManager

logger = logging.getLogger(__name__)


class AddReminderTool(ServerSideTool):
    """Tool for creating new reminders."""

    def __init__(self, backlog_manager: BacklogManager):
        super().__init__("add_reminder")
        self.backlog_manager = backlog_manager
        logger.info("AddReminderTool initialized")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["add_reminder"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.add_reminder]

    @function_tool
    async def add_reminder(
        self,
        title: str,
        scheduled_date: str = "",
        scheduled_time: str = "",
        minutes_from_now: int = 0,
        remind_before_minutes: int = 0,
        recurrence: str = "once",
        notes: str = "",
    ) -> str:
        """
        Create a new reminder for the user. Use this when the user says things like
        'remind me to...', 'don't let me forget...', or 'I need to remember to...'.

        Args:
            title: What to remind the user about (e.g., "call my son", "water the plants")
            scheduled_date: Date for the reminder in YYYY-MM-DD format (e.g., "2025-11-24").
                            Leave empty if using minutes_from_now.
            scheduled_time: Time for the reminder in HH:MM 24-hour format (e.g., "14:00" for 2 PM).
                            Leave empty if using minutes_from_now.
            minutes_from_now: Set reminder X minutes from now. Use this for relative times like
                              "in 5 minutes" (5), "in 1 hour" (60), "in 2 hours" (120).
                              If set, scheduled_date and scheduled_time are ignored.
            remind_before_minutes: How many minutes before to remind. Default is 0 (remind at exact time).
                                   Examples: 30 for half hour, 60 for 1 hour, 120 for 2 hours.
                                   For short reminders (under 30 min), use 0.
            recurrence: How often this repeats. Options: "once", "daily", "weekly", "monthly"
            notes: Optional additional context or details

        Returns:
            Confirmation message for the user
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for add_reminder tool")
                return "I'm sorry, I couldn't create the reminder. Please try again."

            # Validate recurrence
            valid_recurrence = ["once", "daily", "weekly", "monthly"]
            if recurrence not in valid_recurrence:
                return f"Invalid recurrence '{recurrence}'. Please use: once, daily, weekly, or monthly."

            # Get current client time
            if self._time_tracker and self._time_tracker.is_initialized():
                current_time = self._time_tracker.get_current_client_time()
            else:
                current_time = datetime.utcnow()
                logger.warning("Time tracker not initialized, using UTC time")

            # Calculate scheduled_datetime
            from datetime import timedelta

            if minutes_from_now > 0:
                # Relative time: "in X minutes"
                scheduled_datetime = current_time + timedelta(minutes=minutes_from_now)
                logger.info(
                    f"Relative reminder: {minutes_from_now} min from {current_time} = {scheduled_datetime}"
                )
            else:
                # Absolute time: specific date and time
                if not scheduled_date or not scheduled_time:
                    return "Please specify when you'd like to be reminded (date and time, or how many minutes from now)."

                try:
                    scheduled_datetime = datetime.strptime(
                        f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M"
                    )
                except ValueError as e:
                    logger.error(f"Date/time parsing error: {e}")
                    return (
                        "I couldn't understand the date or time. "
                        "Please use format like '2025-11-24' for date and '14:00' for time."
                    )

                # Check if date is in the past
                if scheduled_datetime < current_time:
                    return "That time has already passed. Please choose a future date and time."

            # Create the reminder
            item = self.backlog_manager.add_item(
                user_id=self._user_id,
                title=title,
                scheduled_datetime=scheduled_datetime,
                remind_before_minutes=remind_before_minutes,
                recurrence=recurrence,
                notes=notes,
            )

            logger.info(f"Created reminder '{title}' for user {self._user_id}")

            # Format response
            time_display = scheduled_datetime.strftime("%I:%M %p").lstrip("0")
            date_display = scheduled_datetime.strftime("%A, %B %d")

            # Build response based on how reminder was set
            if minutes_from_now > 0:
                # Relative time response
                if minutes_from_now < 60:
                    time_desc = f"{minutes_from_now} minute{'s' if minutes_from_now != 1 else ''}"
                else:
                    hours = minutes_from_now // 60
                    mins = minutes_from_now % 60
                    if mins > 0:
                        time_desc = f"{hours} hour{'s' if hours != 1 else ''} and {mins} minute{'s' if mins != 1 else ''}"
                    else:
                        time_desc = f"{hours} hour{'s' if hours != 1 else ''}"
                response = (
                    f"I'll remind you to {title} in {time_desc} (at {time_display})."
                )
            elif recurrence == "once":
                response = f"I've set a reminder to {title} on {date_display} at {time_display}."
            else:
                recurrence_text = {
                    "daily": "every day",
                    "weekly": "every week",
                    "monthly": "every month",
                }
                response = (
                    f"I've set a recurring reminder to {title} {recurrence_text[recurrence]}, "
                    f"starting {date_display} at {time_display}."
                )

            # Add remind-before info if set
            if remind_before_minutes > 0:
                remind_datetime = scheduled_datetime - timedelta(
                    minutes=remind_before_minutes
                )
                remind_time_display = remind_datetime.strftime("%I:%M %p").lstrip("0")

                if remind_before_minutes >= 60:
                    hours = remind_before_minutes // 60
                    mins = remind_before_minutes % 60
                    if mins > 0:
                        early_text = (
                            f"{hours} hour{'s' if hours > 1 else ''} and {mins} minutes"
                        )
                    else:
                        early_text = f"{hours} hour{'s' if hours > 1 else ''}"
                else:
                    early_text = f"{remind_before_minutes} minutes"
                response += f" I'll give you a heads up {early_text} before, at {remind_time_display}."

            return response

        except Exception as e:
            logger.error(f"Error in add_reminder: {e}", exc_info=True)
            return f"I'm sorry, I couldn't create the reminder. Please try again."
