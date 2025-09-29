"""
Emergency delay adjustment tool for fall detection.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class EmergencyDelayTool(BaseTool):
    """Tool for adjusting fall detection emergency call delay."""

    def __init__(self):
        super().__init__("set_emergency_delay")

    def get_tool_methods(self) -> list:
        return ["set_emergency_delay"]

    def get_tool_functions(self) -> list:
        return [self.set_emergency_delay]

    @function_tool
    async def set_emergency_delay(self, seconds: int) -> str:
        """
        Set emergency call delay duration.

        Args:
            seconds: Delay in seconds - must be 15, 30, or 60
        """
        logger.info(f"Setting emergency delay to: {seconds} seconds")

        result = await self.send_tool_request(
            "set_emergency_delay", {"seconds": seconds}
        )

        message = result.get("message", "Emergency delay updated")
        return f"✅ {message}"
