"""
Tool for setting custom reminder days on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SetCustomDaysTool(BaseTool):
    """Tool for setting which days of the week a reminder repeats."""

    def __init__(self):
        super().__init__("set_custom_days")

    def get_tool_methods(self) -> list:
        return ["set_custom_days"]

    def get_tool_functions(self) -> list:
        return [self.set_custom_days]

    @function_tool
    async def set_custom_days(self, days: list[int]) -> str:
        """
        Set which days of the week the medication reminder repeats.

        Args:
            days: List of day numbers where 1=Monday, 2=Tuesday, ..., 7=Sunday
                  Example: [1, 3, 5] for Monday, Wednesday, Friday
        """
        logger.info(f"Setting custom days to {days}")

        # Validate days
        if not days:
            return "Please provide at least one day"

        for day in days:
            if not isinstance(day, int) or day < 1 or day > 7:
                return "Day numbers must be between 1 (Monday) and 7 (Sunday)"

        result = await self.send_tool_request("set_custom_days", {"days": days})

        message = result.get("message", "Custom days set")
        day_names = result.get("day_names", [])

        if day_names:
            return f"✅ Reminder set for: {', '.join(day_names)}"
        else:
            return f"✅ {message}"
