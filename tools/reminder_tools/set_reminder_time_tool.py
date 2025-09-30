"""
Tool for setting reminder time on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SetReminderTimeTool(BaseTool):
    """Tool for setting the time for a medication reminder."""

    def __init__(self):
        super().__init__("set_reminder_time")

    def get_tool_methods(self) -> list:
        return ["set_reminder_time"]

    def get_tool_functions(self) -> list:
        return [self.set_reminder_time]

    @function_tool
    async def set_reminder_time(self, hour: int, minute: int) -> str:
        """
        Set the time for a medication reminder.

        Args:
            hour: Hour in 24-hour format (0-23)
            minute: Minute (0-59)
        """
        logger.info(f"Setting reminder time to {hour}:{minute}")

        result = await self.send_tool_request(
            "set_reminder_time", {"hour": hour, "minute": minute}
        )

        message = result.get("message", "Time set")
        return f"✅ {message}"
