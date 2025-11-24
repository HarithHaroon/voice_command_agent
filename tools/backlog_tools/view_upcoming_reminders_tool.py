"""
ViewUpcomingRemindersTool - Show upcoming reminders by timeframe.
"""

import logging
from datetime import datetime, timedelta
from typing import List

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from backlog.backlog_manager import BacklogManager

logger = logging.getLogger(__name__)


class ViewUpcomingRemindersTool(ServerSideTool):
    """Tool for viewing upcoming reminders."""

    def __init__(self):
        super().__init__("view_upcoming_reminders")
        self.backlog_manager = BacklogManager()
        logger.info("ViewUpcomingRemindersTool initialized")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["view_upcoming_reminders"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.view_upcoming_reminders]

    @function_tool
    async def view_upcoming_reminders(self, timeframe: str = "today") -> str:
        """
        Show the user their upcoming reminders. Use this when the user asks things like
        'what do I have today?', 'what's coming up?', 'any reminders for tomorrow?',
        or 'what's on my schedule this week?'.

        Args:
            timeframe: The time period to show. Options:
                       - "today": Reminders for today
                       - "tomorrow": Reminders for tomorrow
                       - "week": Reminders for the next 7 days
                       - "all": All active reminders

        Returns:
            List of upcoming reminders formatted for the user
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for view_upcoming_reminders tool")
                return "I'm sorry, I couldn't check your reminders. Please try again."

            # Validate timeframe
            valid_timeframes = ["today", "tomorrow", "week", "all"]
            if timeframe not in valid_timeframes:
                return (
                    f"I can show you reminders for: today, tomorrow, this week, or all."
                )

            # Get items by timeframe
            items = self.backlog_manager.get_items_by_timeframe(
                self._user_id, timeframe
            )

            logger.info(f"Found {len(items)} reminders for {timeframe}")

            if not items:
                timeframe_text = {
                    "today": "today",
                    "tomorrow": "tomorrow",
                    "week": "this week",
                    "all": "set up",
                }
                return f"You don't have any reminders {timeframe_text[timeframe]}."

            # Format response
            timeframe_headers = {
                "today": "Here's what you have today:",
                "tomorrow": "Here's what you have tomorrow:",
                "week": "Here's what you have this week:",
                "all": "Here are all your reminders:",
            }

            response_lines = [timeframe_headers[timeframe]]

            for i, item in enumerate(items, 1):
                scheduled = datetime.fromisoformat(item["scheduled_time"])
                time_display = scheduled.strftime("%I:%M %p").lstrip("0")

                # Add date for week/all views
                if timeframe in ["week", "all"]:
                    date_display = scheduled.strftime("%A, %B %d")
                    line = f"{i}. {item['title']} - {date_display} at {time_display}"
                else:
                    line = f"{i}. {item['title']} at {time_display}"

                # Add recurrence info
                if item.get("recurrence") and item["recurrence"] != "once":
                    recurrence_text = {
                        "daily": "(repeats daily)",
                        "weekly": "(repeats weekly)",
                        "monthly": "(repeats monthly)",
                    }
                    line += f" {recurrence_text.get(item['recurrence'], '')}"

                # Add remind-before info
                remind_before = item.get("remind_before_minutes", 15)
                if remind_before != 15:
                    remind_time = scheduled - timedelta(minutes=remind_before)
                    remind_display = remind_time.strftime("%I:%M %p").lstrip("0")
                    line += f" - I'll remind you at {remind_display}"

                response_lines.append(line)

            return "\n".join(response_lines)

        except Exception as e:
            logger.error(f"Error in view_upcoming_reminders: {e}", exc_info=True)
            return "I'm sorry, I couldn't retrieve your reminders. Please try again."
