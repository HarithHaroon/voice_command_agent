"""
Tool for setting reminder recurrence type on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SetRecurrenceTypeTool(BaseTool):
    """Tool for setting how often a medication reminder repeats."""

    VALID_TYPES = ["once", "daily", "weekly", "custom"]

    def __init__(self):
        super().__init__("set_recurrence_type")

    def get_tool_methods(self) -> list:
        return ["set_recurrence_type"]

    def get_tool_functions(self) -> list:
        return [self.set_recurrence_type]

    @function_tool
    async def set_recurrence_type(self, recurrence_type: str) -> str:
        """
        Set how often the medication reminder repeats.

        Args:
            recurrence_type: Recurrence pattern - "once", "daily", "weekly", or "custom"
        """
        logger.info(f"Setting recurrence type to {recurrence_type}")

        # Validate type
        if recurrence_type.lower() not in self.VALID_TYPES:
            return (
                f"Invalid recurrence type. Please choose: {', '.join(self.VALID_TYPES)}"
            )

        result = await self.send_tool_request(
            "set_recurrence_type", {"type": recurrence_type.lower()}
        )

        message = result.get("message", "Recurrence type set")
        return f"✅ {message}"
