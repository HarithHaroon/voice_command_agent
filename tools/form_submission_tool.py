"""
Form submission tool for client-side execution via Flutter app.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class FormSubmissionTool(BaseTool):
    def __init__(self):
        super().__init__("form_submission")

    def get_tool_methods(self) -> list:
        return ["submit_form"]

    def get_tool_functions(self) -> list:
        return [self.submit_form]

    @function_tool
    async def submit_form(self, form_name: str = "current") -> str:
        """
        Submit any form on Flutter client.

        Args:
            form_name: Name of the form to submit (e.g., 'contact', 'face_recognition')
        """
        logger.info(f"Submitting {form_name} form")

        result = await self.send_tool_request(
            "submit_form", {"form_name": form_name}, "submission"
        )

        success = result.get("success", False)
        message = result.get("message", "Submission completed")

        if success:
            return f"✅ {form_name} form submitted successfully!"
        else:
            return f"❌ {form_name} form submission failed: {message}"
