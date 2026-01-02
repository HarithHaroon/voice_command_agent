"""
Backlog Agent - Specialist for reminders and task management.
"""

import logging
from typing import List
from livekit.agents import Agent
from models.shared_state import SharedState
from agents.base_specialist_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class BacklogAgent(BaseSpecialistAgent):
    """
    Specialist agent for managing reminders and tasks.
    Handles:
    - Creating reminders with specific times and recurrence
    - Viewing upcoming reminders by timeframe
    - Completing reminders
    - Deleting reminders
    - Listing all active reminders
    """

    AGENT_NAME = "BacklogAgent"

    def _get_tools(self) -> List:
        """Get tools specific to backlog management."""
        # Start with base tools (recall_history + handoff)
        tools = super()._get_tools()

        # Add backlog-specific tools
        backlog_tool_names = [
            "add_reminder",
            "view_upcoming_reminders",
            "complete_reminder",
            "delete_reminder",
            "list_all_reminders",
        ]

        tools.extend(self._get_tools_by_names(backlog_tool_names))

        # DEBUG: Print actual tool names
        logger.info(f"=== BACKLOG TOOLS DEBUG ===")

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

        logger.info(f"BacklogAgent loaded {len(tools)} tools")

        return tools
