"""
Tool for starting video calls with family members on Flutter client.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class StartVideoCallTool(BaseTool):
    """Tool for initiating video calls with family members."""

    def __init__(self):
        super().__init__("start_video_call")

    def get_tool_methods(self) -> list:
        return ["start_video_call"]

    def get_tool_functions(self) -> list:
        return [self.start_video_call]

    @function_tool
    async def start_video_call(self, family_member_name: str) -> str:
        """
        Start a video call with a specific family member.

        Args:
            family_member_name: The name of the family member to call (e.g., "Mom", "John", "Sarah")
        """
        logger.info(f"Starting video call with {family_member_name}")

        result = await self.send_tool_request(
            "start_video_call", {"family_member_name": family_member_name}
        )

        message = result.get("message", "Video call started")
        family_name = result.get("family_member_name", family_member_name)

        return f"✅ {message}"
