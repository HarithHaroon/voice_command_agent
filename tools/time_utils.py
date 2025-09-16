"""
Time utilities tool for client-side execution via Flutter app.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class TimeTool(BaseTool):
    """Tool for getting current time information from Flutter client."""

    def __init__(self):
        super().__init__("time")

    def get_tool_methods(self) -> list:
        """Return list of tool methods this class provides."""
        return ["get_current_time"]

    def get_tool_functions(self) -> list:
        """Return list of function_tool decorated methods."""
        return [self.get_current_time]

    @function_tool
    async def get_current_time(self, timezone: str = "local") -> str:
        """Get current time from Flutter client."""
        logger.info(f"Getting time for timezone: {timezone}")

        # Use timezone as ID suffix to match original format
        result = await self.send_tool_request(
            "get_current_time", {"timezone": timezone}, timezone
        )

        # Extract time from result
        time_info = result.get("time", "Unknown time")
        logger.info(f"Time retrieved: {time_info}")

        return f"The current time is {time_info}"
