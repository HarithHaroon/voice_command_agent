"""
Sensitivity adjustment tool for fall detection.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class FallDetectionSensitivityTool(BaseTool):
    """Tool for adjusting fall detection sensitivity."""

    def __init__(self):
        super().__init__("set_sensitivity")

    def get_tool_methods(self) -> list:
        return ["set_sensitivity"]

    def get_tool_functions(self) -> list:
        return [self.set_sensitivity]

    @function_tool
    async def set_sensitivity(self, level: str) -> str:
        """
        Set fall detection sensitivity level.

        Args:
            level: Sensitivity level - "gentle", "balanced", or "sensitive"
        """
        logger.info(f"Setting fall detection sensitivity to: {level}")

        result = await self.send_tool_request("set_sensitivity", {"level": level})

        # send_tool_request returns the 'result' object directly, not the full response
        message = result.get("message", "Sensitivity updated")
        return f"✅ {message}"
