"""
Image Agent - Specialist for image queries and face recognition.
"""

import logging
from typing import List
from livekit.agents import Agent
from models.shared_state import SharedState
from agents.base_specialist_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class ImageAgent(BaseSpecialistAgent):
    """
    Specialist agent for image queries.
    Handles:
    - Searching for images by text description
    """

    AGENT_NAME = "ImageAgent"

    def _get_tools(self) -> List:
        """Get tools specific to image queries."""
        # Start with base tools (recall_history + handoff)
        tools = super()._get_tools()

        # Add image-specific tools
        image_tool_names = [
            "query_image",
        ]

        tools.extend(self._get_tools_by_names(image_tool_names))

        logger.info(f"{self.AGENT_NAME} loaded {len(tools)} tools")

        return tools
