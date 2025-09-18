"""
Form orchestration tool for complete form workflows.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class FormOrchestrationTool(BaseTool):
    def __init__(self):
        super().__init__("form_orchestration")
        # Store references to other tools
        self._text_field_tool = None
        self._validation_tool = None
        self._submission_tool = None

    def set_tools(self, text_field_tool, validation_tool, submission_tool):
        """Set references to other tools."""
        self._text_field_tool = text_field_tool
        self._validation_tool = validation_tool
        self._submission_tool = submission_tool

    def get_tool_methods(self) -> list:
        return []

    def get_tool_functions(self) -> list:
        return [self.complete_contact_form]

    @function_tool
    async def complete_contact_form(self, name: str, email: str, phone: str) -> str:
        """Fill, validate and submit the complete contact form."""
        try:
            # Step 1: Fill all fields
            await self._text_field_tool.fill_name_field(name)
            await self._text_field_tool.fill_email_field(email)
            await self._text_field_tool.fill_phone_field(phone)

            # Step 2: Validate
            validation_result = await self._validation_tool.validate_contact_form()
            if "failed" in validation_result:
                return f"Form completion stopped: {validation_result}"

            # Step 3: Submit
            submission_result = await self._submission_tool.submit_contact_form()
            return f"Contact form workflow completed: {submission_result}"

        except Exception as e:
            logger.error(f"Form orchestration failed: {e}")
            return f"Form completion failed: {str(e)}"
