"""
Tool for toggling WatchOS fall detection on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToggleWatchosFallDetectionTool(BaseTool):
    """Tool for toggling fall detection monitoring on Apple Watch."""

    def __init__(self):
        super().__init__("toggle_watchos_fall_detection")

    def get_tool_methods(self) -> list:
        return ["toggle_watchos_fall_detection"]

    def get_tool_functions(self) -> list:
        return [self.toggle_watchos_fall_detection]

    @function_tool
    async def toggle_watchos_fall_detection(self) -> str:
        """
        Toggle fall detection monitoring on Apple Watch.

        Turns WatchOS fall detection on if it's currently off, or off if it's currently on.
        This controls the smartwatch's ability to detect falls and alert emergency contacts.
        """
        logger.info("Toggling WatchOS fall detection")

        result = await self.send_tool_request("toggle_watchos_fall_detection", {})

        message = result.get("message", "Action completed")
        new_state = result.get("new_state", None)

        if new_state is not None:
            state_text = "started" if new_state else "stopped"
            return f"✅ WatchOS fall detection {state_text}. {message}"
        else:
            return f"✅ {message}"
