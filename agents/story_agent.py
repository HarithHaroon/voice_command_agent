"""
Story Agent - Specialist for life story recording and retrieval.
"""

import logging
from typing import List
from agents.base_specialist_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class StoryAgent(BaseSpecialistAgent):
    """
    Specialist agent for life story management.
    Handles:
    - Recording new stories
    - Finding and retrieving stories
    - Listing story collections
    - Story summaries
    """

    AGENT_NAME = "StoryAgent"

    def _get_tools(self) -> List:
        """Get tools specific to story management."""
        # Start with base tools (recall_history + handoff)
        tools = super()._get_tools()

        story_tool_names = ["story"]

        tools.extend(self._get_tools_by_names(story_tool_names))

        logger.info(f"{self.AGENT_NAME} loaded {len(tools)} tools")

        return tools
