"""
Generic text field tool for client-side execution via Flutter app.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class TextFieldTool(BaseTool):
    """Generic tool for filling text fields on Flutter client."""

    def __init__(self):
        super().__init__("text_field")

    def get_tool_methods(self) -> list:
        return ["fill_text_field"]

    def get_tool_functions(self) -> list:
        return [self.fill_text_field]

    @function_tool
    async def fill_text_field(self, field_name: str, value: str) -> str:
        """
        Fill any text field on Flutter client.

        Args:
            field_name: Name of the field to fill (e.g., 'name', 'email', 'person_name', 'person_details')
            value: Value to fill in the field
        """
        result = await self.send_tool_request(
            "fill_text_field", {"field_type": field_name, "value": value}
        )
        return f"Successfully filled {field_name} field with '{value}'"
