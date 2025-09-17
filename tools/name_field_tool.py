"""
Name field tool for client-side execution via Flutter app.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class NameFieldTool(BaseTool):
    """Tool for filling name field on Flutter client."""

    def __init__(self):
        super().__init__("name_field")

    def get_tool_methods(self) -> list:
        """Return list of tool methods this class provides."""
        return ["fill_name_field"]

    def get_tool_functions(self) -> list:
        """Return list of function_tool decorated methods."""
        return [self.fill_name_field]

    @function_tool
    async def fill_name_field(self, name: str) -> str:
        """Fill the name field on Flutter client."""
        logger.info(f"Filling name field with: {name}")

        # Use timezone as ID suffix to match original format
        result = await self.send_tool_request("fill_name_field", {"name": name}, name)

        # Extract result from response
        sent_name = result.get("name", "Unknown")
        message = result.get("message", "Field filled")

        logger.info(f"Name field result: {sent_name}")
        return f"Successfully filled the name field with '{sent_name}' and sent to backend."
