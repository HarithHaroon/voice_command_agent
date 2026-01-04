"""
Memory Agent - Specialist for general memory management.
Handles item locations, personal information, and daily activities.
"""

import logging
from typing import List
from agents.base_specialist_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class MemoryAgent(BaseSpecialistAgent):
    """
    Specialist agent for managing elderly user memory.
    Handles:
    - Storing and finding item locations
    - Storing and recalling personal information
    - Logging daily activities and context
    - Retrieving what user was doing
    """

    AGENT_NAME = "MemoryAgent"

    def _get_tools(self) -> List:
        """Get tools specific to memory management."""
        # Start with base tools (recall_history + handoff)
        tools = super()._get_tools()

        # Add memory-specific tools
        memory_tool_names = [
            "store_item_location",
            "find_item",
            "store_information",
            "recall_information",
            "log_activity",
            "get_daily_context",
            "what_was_i_doing",
        ]

        tools.extend(self._get_tools_by_names(memory_tool_names))

        # DEBUG: Print actual tool names
        logger.info(f"=== MEMORY TOOLS DEBUG ===")

        for i, tool in enumerate(tools):
            # Try different ways to get the tool name
            if hasattr(tool, "name"):
                tool_name = tool.name
            elif hasattr(tool, "__name__"):
                tool_name = tool.__name__
            elif hasattr(tool, "function"):
                tool_name = getattr(tool.function, "__name__", "unknown")
            else:
                tool_name = str(type(tool))

            logger.info(f"  {i}: {tool_name}")

        logger.info(f"=== TOTAL: {len(tools)} tools ===")

        logger.info(f"MemoryAgent loaded {len(tools)} tools")

        return tools
