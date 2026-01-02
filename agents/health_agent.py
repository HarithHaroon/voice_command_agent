"""
Health Agent - Specialist for health data queries and vitals.
"""

import logging
from typing import List
from livekit.agents import Agent
from models.shared_state import SharedState
from agents.base_specialist_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class HealthAgent(BaseSpecialistAgent):
    """
    Specialist agent for querying health data and vital signs.
    Handles:
    - Overall health status summaries
    - Specific vital queries (heart rate, blood pressure, steps, sleep)
    - Health trends and historical data
    """

    AGENT_NAME = "HealthAgent"

    def _get_tools(self) -> List:
        """Get tools for health agent."""
        tools = super()._get_tools()  # Gets recall_history (handoff auto-discovered)

        # Add health query tool
        health_tool = self.shared_state.tool_manager.get_tool("health_query")

        if health_tool:
            tools.extend(health_tool.get_tool_functions())

        else:
            logger.warning("HealthAgent: Tool 'health_query' not found")

        logger.info(f"HealthAgent loaded {len(tools)} tools")

        return tools
