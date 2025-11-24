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

    def __init__(self):
        super().__init__("add_reminder")
        self.backlog_manager = BacklogManager()
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
        scheduled_date: str,
        scheduled_time: str,
        remind_before_minutes: int = 15,
        recurrence: str = "once",
        notes: str = "",
    ) -> str:
        """
        Create a new reminder for the user. Use this when the user says things like
        'remind me to...', 'don't let me forget...', or 'I need to remember to...'.

        Args:
            title: What to remind the user about (e.g., "call my son", "water the plants")
            scheduled_date: Date for the reminder in YYYY-MM-DD format (e.g., "2025-11-24")
            scheduled_time: Time for the reminder in HH:MM 24-hour format (e.g., "14:00" for 2 PM)
            remind_before_minutes: How many minutes before to remind. Default is 15.
                                   Examples: 30 for half hour, 60 for 1 hour, 120 for 2 hours
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

            # Parse date and time
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
            if scheduled_datetime < datetime.utcnow():
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

            # Calculate remind time
            remind_datetime = scheduled_datetime
            if remind_before_minutes > 0:
                from datetime import timedelta

                remind_datetime = scheduled_datetime - timedelta(
                    minutes=remind_before_minutes
                )
            remind_time_display = remind_datetime.strftime("%I:%M %p").lstrip("0")

            # Build response
            if recurrence == "once":
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

            # Add remind-before info if not default
            if remind_before_minutes != 15:
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
                response += (
                    f" I'll remind you {early_text} before, at {remind_time_display}."
                )
            else:
                response += f" I'll remind you 15 minutes before."

            return response

        except Exception as e:
            logger.error(f"Error in add_reminder: {e}", exc_info=True)
            return f"I'm sorry, I couldn't create the reminder. Please try again."
