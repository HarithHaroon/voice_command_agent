"""
Toggle tool for controlling fall detection on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToggleFallDetectionTool(BaseTool):
    """Tool for toggling fall detection monitoring."""

    def __init__(self):
        super().__init__("toggle_fall_detection")

    def get_tool_methods(self) -> list:
        return ["toggle_fall_detection"]

    def get_tool_functions(self) -> list:
        return [self.toggle_fall_detection]

    @function_tool
    async def toggle_fall_detection(self) -> str:
        """
        Control fall detection monitoring.

        Args:
            action: Action to perform - "on", "off", or "toggle" (default: "toggle")
        """
        logger.info(f"Toggling fall detection")

        result = await self.send_tool_request("toggle_fall_detection", {})

        success = result.get("success", False)
        message = result.get("message", "")
        new_state = result.get("new_state", None)

        if success:
            state_text = "enabled" if new_state else "disabled"
            return f"✅ Fall detection {state_text}. {message}"
        else:
            return f"❌ Failed to toggle fall detection: {message}"
