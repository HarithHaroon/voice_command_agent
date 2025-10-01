"""
Tool for setting WatchOS fall detection sensitivity on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SetWatchosSensitivityTool(BaseTool):
    """Tool for adjusting fall detection sensitivity on Apple Watch."""

    VALID_LEVELS = ["low", "medium", "high"]

    def __init__(self):
        super().__init__("set_watchos_sensitivity")

    def get_tool_methods(self) -> list:
        return ["set_watchos_sensitivity"]

    def get_tool_functions(self) -> list:
        return [self.set_watchos_sensitivity]

    @function_tool
    async def set_watchos_sensitivity(self, level: str) -> str:
        """
        Set the fall detection sensitivity level on Apple Watch.

        Args:
            level: Sensitivity level - "low", "medium", or "high"
                  - low: Only detects major falls, fewer false alerts
                  - medium: Balanced detection, recommended for most users
                  - high: Detects smaller movements, may have more alerts
        """
        logger.info(f"Setting WatchOS sensitivity to {level}")

        # Validate level
        if level.lower() not in self.VALID_LEVELS:
            return f"Invalid sensitivity level. Please choose: {', '.join(self.VALID_LEVELS)}"

        result = await self.send_tool_request(
            "set_watchos_sensitivity", {"level": level.lower()}
        )

        message = result.get("message", "Sensitivity updated")
        description = result.get("description", "")

        response = f"✅ {message}"
        if description:
            response += f". {description}"

        return response
