"""
Toggle tool for controlling location tracking on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToggleLocationTrackingTool(BaseTool):
    """Tool for toggling background location tracking."""

    def __init__(self):
        super().__init__("toggle_location_tracking")

    def get_tool_methods(self) -> list:
        return ["toggle_location_tracking"]

    def get_tool_functions(self) -> list:
        return [self.toggle_location_tracking]

    @function_tool
    async def toggle_location_tracking(self) -> str:
        """
        Toggle background location tracking on or off.

        Enables or disables continuous location sharing with family members.
        Requires location permissions to be granted.
        """
        logger.info("Toggling location tracking")

        result = await self.send_tool_request("toggle_location_tracking", {})

        message = result.get("message", "Action completed")
        new_state = result.get("new_state", None)

        if new_state is not None:
            state_text = "started" if new_state else "stopped"
            return f"✅ Location tracking {state_text}. {message}"
        else:
            return f"✅ {message}"
