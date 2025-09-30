"""
Tool for updating location tracking interval on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class UpdateLocationIntervalTool(BaseTool):
    """Tool for changing location update frequency."""

    ALLOWED_INTERVALS = [5, 10, 15, 30]

    def __init__(self):
        super().__init__("update_location_interval")

    def get_tool_methods(self) -> list:
        return ["update_location_interval"]

    def get_tool_functions(self) -> list:
        return [self.update_location_interval]

    @function_tool
    async def update_location_interval(self, interval: int) -> str:
        """
        Update the location tracking interval.

        Args:
            interval: Update frequency in minutes. Must be one of: 5, 10, 15, or 30 minutes.
        """
        logger.info(f"Updating location interval to {interval} minutes")

        # Validate interval
        if interval not in self.ALLOWED_INTERVALS:
            return f"Invalid interval. Please choose one of: {', '.join(map(str, self.ALLOWED_INTERVALS))} minutes."

        result = await self.send_tool_request(
            "update_location_interval", {"interval": interval}
        )

        message = result.get("message", "Interval updated")
        return f"✅ {message}"
