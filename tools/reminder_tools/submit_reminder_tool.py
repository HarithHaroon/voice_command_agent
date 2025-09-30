"""
Tool for submitting medication reminder on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SubmitReminderTool(BaseTool):
    """Tool for submitting and scheduling a medication reminder."""

    def __init__(self):
        super().__init__("submit_reminder")

    def get_tool_methods(self) -> list:
        return ["submit_reminder"]

    def get_tool_functions(self) -> list:
        return [self.submit_reminder]

    @function_tool
    async def submit_reminder(self) -> str:
        """
        Submit and schedule the medication reminder with all the configured settings.
        This will create the reminder notification on the device.
        """
        logger.info("Submitting reminder")

        result = await self.send_tool_request("submit_reminder", {})

        message = result.get("message", "Reminder scheduled")
        return f"✅ {message}"
