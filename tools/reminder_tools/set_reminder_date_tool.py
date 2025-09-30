"""
Tool for setting reminder date on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SetReminderDateTool(BaseTool):
    """Tool for setting the date for a medication reminder."""

    def __init__(self):
        super().__init__("set_reminder_date")

    def get_tool_methods(self) -> list:
        return ["set_reminder_date"]

    def get_tool_functions(self) -> list:
        return [self.set_reminder_date]

    @function_tool
    async def set_reminder_date(self, year: int, month: int, day: int) -> str:
        """
        Set the date for a medication reminder.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            day: Day (1-31)
        """
        logger.info(f"Setting reminder date to {year}-{month}-{day}")

        result = await self.send_tool_request(
            "set_reminder_date", {"year": year, "month": month, "day": day}
        )

        message = result.get("message", "Date set")
        return f"✅ {message}"
