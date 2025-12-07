"""
CompleteReminderTool - Mark reminders as complete.
For recurring reminders, automatically creates the next occurrence.
"""

import logging
from datetime import datetime
from typing import List

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from backlog.backlog_manager import BacklogManager

logger = logging.getLogger(__name__)


class CompleteReminderTool(ServerSideTool):
    """Tool for marking reminders as complete."""

    def __init__(self, backlog_manager: BacklogManager):
        super().__init__("complete_reminder")
        self.backlog_manager = backlog_manager
        logger.info("CompleteReminderTool initialized")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["complete_reminder"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.complete_reminder]

    @function_tool
    async def complete_reminder(self, title_search: str) -> str:
        """
        Mark a reminder as complete. Use this when the user says things like
        'I just did that', 'I already called my son', 'mark that as done',
        or 'I finished watering the plants'.

        For recurring reminders (daily, weekly, monthly), this will automatically
        schedule the next occurrence.

        Args:
            title_search: Part of the reminder title to find and complete.
                          For example, if the reminder is "call my son",
                          the user might say "call" or "son" or "call my son".

        Returns:
            Confirmation message for the user
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for complete_reminder tool")
                return "I'm sorry, I couldn't complete the reminder. Please try again."

            # Find the item by title
            item = self.backlog_manager.find_item_by_title(self._user_id, title_search)

            if not item:
                return (
                    f"I couldn't find a reminder matching '{title_search}'. "
                    "Would you like me to show you your current reminders?"
                )

            # Complete the item
            result = self.backlog_manager.complete_item(self._user_id, item["item_id"])

            completed_item = result["completed_item"]
            next_item = result["next_item"]

            logger.info(
                f"Completed reminder '{completed_item['title']}' for user {self._user_id}"
            )

            # Format response
            response = f"Great! I've marked '{completed_item['title']}' as done."

            # If recurring, mention the next occurrence
            if next_item:
                next_scheduled = datetime.fromisoformat(next_item["scheduled_time"])
                date_display = next_scheduled.strftime("%A, %B %d")
                time_display = next_scheduled.strftime("%I:%M %p").lstrip("0")

                recurrence = completed_item.get("recurrence", "")
                recurrence_text = {
                    "daily": "daily",
                    "weekly": "weekly",
                    "monthly": "monthly",
                }

                response += (
                    f" Since this is a {recurrence_text.get(recurrence, 'recurring')} reminder, "
                    f"I've scheduled the next one for {date_display} at {time_display}."
                )

            return response

        except Exception as e:
            logger.error(f"Error in complete_reminder: {e}", exc_info=True)
            return "I'm sorry, I couldn't complete the reminder. Please try again."
