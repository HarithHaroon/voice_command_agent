"""
DeleteReminderTool - Permanently delete reminders.
"""

import logging
from typing import List

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from backlog.backlog_manager import BacklogManager

logger = logging.getLogger(__name__)


class DeleteReminderTool(ServerSideTool):
    """Tool for deleting reminders."""

    def __init__(self):
        super().__init__("delete_reminder")
        self.backlog_manager = BacklogManager()
        logger.info("DeleteReminderTool initialized")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["delete_reminder"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.delete_reminder]

    @function_tool
    async def delete_reminder(self, title_search: str) -> str:
        """
        Permanently delete a reminder. Use this when the user says things like
        'cancel that reminder', 'delete the reminder about...',
        'I don't need that reminder anymore', or 'remove the reminder'.

        This permanently removes the reminder and cannot be undone.

        Args:
            title_search: Part of the reminder title to find and delete.
                          For example, if the reminder is "call my son",
                          the user might say "call" or "son" or "call my son".

        Returns:
            Confirmation message for the user
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for delete_reminder tool")
                return "I'm sorry, I couldn't delete the reminder. Please try again."

            # Find the item by title
            item = self.backlog_manager.find_item_by_title(self._user_id, title_search)

            if not item:
                return (
                    f"I couldn't find a reminder matching '{title_search}'. "
                    "Would you like me to show you your current reminders?"
                )

            # Store title before deletion
            title = item["title"]

            # Delete the item
            self.backlog_manager.delete_item(self._user_id, item["item_id"])

            logger.info(f"Deleted reminder '{title}' for user {self._user_id}")

            return f"I've deleted the reminder to '{title}'."

        except Exception as e:
            logger.error(f"Error in delete_reminder: {e}", exc_info=True)
            return "I'm sorry, I couldn't delete the reminder. Please try again."
