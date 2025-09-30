"""
Tool for validating reminder form on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ValidateReminderFormTool(BaseTool):
    """Tool for validating the medication reminder form."""

    def __init__(self):
        super().__init__("validate_reminder_form")

    def get_tool_methods(self) -> list:
        return ["validate_reminder_form"]

    def get_tool_functions(self) -> list:
        return [self.validate_reminder_form]

    @function_tool
    async def validate_reminder_form(self) -> str:
        """
        Validate the medication reminder form to check if all required fields are filled.
        Required fields are: medication name and dosage.
        """
        logger.info("Validating reminder form")

        result = await self.send_tool_request("validate_reminder_form", {})

        message = result.get("message", "Form validated")
        return f"✅ {message}"
