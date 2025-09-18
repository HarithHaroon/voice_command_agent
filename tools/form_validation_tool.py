"""
Form validation tool for client-side execution via Flutter app.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class FormValidationTool(BaseTool):
    """Tool for validating forms on Flutter client."""

    def __init__(self, tool_name: str = "contact_form_validation"):
        super().__init__(tool_name)

    def get_tool_methods(self) -> list:
        return ["validate_form"]

    def get_tool_functions(self) -> list:
        return [self.validate_contact_form]

    @function_tool
    async def validate_contact_form(self) -> str:
        """Validate the contact form on Flutter client."""
        logger.info("Validating contact form")

        result = await self.send_tool_request("validate_form", {}, "validation")

        is_valid = result.get("is_valid", False)
        message = result.get("message", "Validation completed")

        if is_valid:
            return f"✅ Contact form is valid and ready to submit"
        else:
            return f"❌ Contact form validation failed: {message}"
