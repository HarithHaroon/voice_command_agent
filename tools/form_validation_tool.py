"""
Form validation tool for client-side execution via Flutter app.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class FormValidationTool(BaseTool):
    def __init__(self):
        super().__init__("form_validation")

    def get_tool_methods(self) -> list:
        return ["validate_form"]

    def get_tool_functions(self) -> list:
        return [self.validate_form]

    @function_tool
    async def validate_form(self, form_name: str = "current") -> str:
        """
        Validate any form on Flutter client.

        Args:
            form_name: Name of the form to validate (e.g., 'contact', 'face_recognition')
        """
        logger.info(f"Validating {form_name} form")

        result = await self.send_tool_request(
            "validate_form", {"form_name": form_name}, "validation"
        )

        is_valid = result.get("is_valid", False)
        message = result.get("message", "Validation completed")

        if is_valid:
            return f"✅ {form_name} form is valid and ready to submit"
        else:
            return f"❌ {form_name} form validation failed: {message}"
