"""
Form submission tool for client-side execution via Flutter app.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class FormSubmissionTool(BaseTool):
    """Tool for submitting forms on Flutter client."""

    def __init__(self, tool_name: str = "contact_form_submission"):
        super().__init__(tool_name)

    def get_tool_methods(self) -> list:
        return ["submit_form"]

    def get_tool_functions(self) -> list:
        return [self.submit_contact_form]

    @function_tool
    async def submit_contact_form(self) -> str:
        """Submit the contact form on Flutter client."""
        logger.info("Submitting contact form")

        result = await self.send_tool_request("submit_form", {}, "submission")

        success = result.get("success", False)
        message = result.get("message", "Submission completed")

        if success:
            submitted_data = result.get("data", {}).get("form_data", {})
            return f"✅ Contact form submitted successfully! Data: {submitted_data}"
        else:
            errors = result.get("errors", [])
            error_msg = ", ".join(errors) if errors else message
            return f"❌ Contact form submission failed: {error_msg}"
