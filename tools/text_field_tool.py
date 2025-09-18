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
        return [self.fill_name_field, self.fill_email_field, self.fill_phone_field]

    @function_tool
    async def fill_name_field(self, name: str) -> str:
        """Fill the name field on Flutter client."""
        result = await self.send_tool_request(
            "fill_text_field", {"field_type": "name", "value": name}, name
        )
        return f"Successfully filled name field with '{name}'"

    @function_tool
    async def fill_email_field(self, email: str) -> str:
        """Fill the email field on Flutter client."""
        result = await self.send_tool_request(
            "fill_text_field", {"field_type": "email", "value": email}, email
        )
        return f"Successfully filled email field with '{email}'"

    @function_tool
    async def fill_phone_field(self, phone: str) -> str:
        """Fill the phone field on Flutter client."""
        result = await self.send_tool_request(
            "fill_text_field", {"field_type": "phone", "value": phone}, phone
        )
        return f"Successfully filled phone field with '{phone}'"
