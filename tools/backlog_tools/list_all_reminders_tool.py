"""
ListAllRemindersTool - Show all active reminders regardless of date.
"""

import logging
from datetime import datetime, timedelta
from typing import List

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from backlog.backlog_manager import BacklogManager

logger = logging.getLogger(__name__)


class ListAllRemindersTool(ServerSideTool):
    """Tool for listing all active reminders."""

    def __init__(self, backlog_manager: BacklogManager):
        super().__init__("list_all_reminders")
        self.backlog_manager = backlog_manager
        logger.info("ListAllRemindersTool initialized")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["list_all_reminders"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.list_all_reminders]

    @function_tool
    async def list_all_reminders(self) -> str:
        """
        Show all active reminders regardless of when they are scheduled.
        Use this when the user asks things like 'show me all my reminders',
        'what reminders do I have?', 'list everything', or 'what have I set up?'.

        Returns:
            List of all active reminders formatted for the user
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for list_all_reminders tool")
                return (
                    "I'm sorry, I couldn't retrieve your reminders. Please try again."
                )

            # Get all active items
            items = self.backlog_manager.list_all_active(self._user_id)

            logger.info(f"Found {len(items)} total reminders for user {self._user_id}")

            if not items:
                return "You don't have any reminders set up. Would you like me to create one?"

            # Get current time from tracker or fallback to UTC
            if self._time_tracker and self._time_tracker.is_initialized():
                now = self._time_tracker.get_current_client_time()
            else:
                now = datetime.utcnow()

            # Group by date for better readability
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            next_week = today + timedelta(days=7)

            today_items = []
            tomorrow_items = []
            this_week_items = []
            later_items = []

            for item in items:
                scheduled = datetime.fromisoformat(item["scheduled_time"])
                scheduled_date = scheduled.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

                if scheduled_date == today:
                    today_items.append(item)
                elif scheduled_date == tomorrow:
                    tomorrow_items.append(item)
                elif scheduled_date < next_week:
                    this_week_items.append(item)
                else:
                    later_items.append(item)

            # Build response
            response_lines = [
                f"You have {len(items)} reminder{'s' if len(items) != 1 else ''}:"
            ]

            def format_item(item, include_date=False):
                """Format a single item for display."""
                scheduled = datetime.fromisoformat(item["scheduled_time"])
                time_display = scheduled.strftime("%I:%M %p").lstrip("0")

                if include_date:
                    date_display = scheduled.strftime("%A, %B %d")
                    line = f"  • {item['title']} - {date_display} at {time_display}"
                else:
                    line = f"  • {item['title']} at {time_display}"

                # Add recurrence badge
                recurrence = item.get("recurrence", "once")
                if recurrence != "once":
                    recurrence_badge = {
                        "daily": "🔄 daily",
                        "weekly": "🔄 weekly",
                        "monthly": "🔄 monthly",
                    }
                    line += f" ({recurrence_badge.get(recurrence, '')})"

                return line

            if today_items:
                response_lines.append("\nToday:")
                for item in today_items:
                    response_lines.append(format_item(item, include_date=False))

            if tomorrow_items:
                response_lines.append("\nTomorrow:")
                for item in tomorrow_items:
                    response_lines.append(format_item(item, include_date=False))

            if this_week_items:
                response_lines.append("\nThis week:")
                for item in this_week_items:
                    response_lines.append(format_item(item, include_date=True))

            if later_items:
                response_lines.append("\nLater:")
                for item in later_items:
                    response_lines.append(format_item(item, include_date=True))

            return "\n".join(response_lines)

        except Exception as e:
            logger.error(f"Error in list_all_reminders: {e}", exc_info=True)
            return "I'm sorry, I couldn't retrieve your reminders. Please try again."
