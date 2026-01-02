"""
Settings Agent - Specialist for device configuration and settings.
"""

import logging
from typing import List
from livekit.agents import Agent
from models.shared_state import SharedState
from agents.base_specialist_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class SettingsAgent(BaseSpecialistAgent):
    """
    Specialist agent for managing device settings and configuration.
    Handles:
    - Fall detection settings (toggle, sensitivity, emergency delay)
    - Location tracking settings (toggle, update interval)
    - WatchOS fall detection settings
    """

    AGENT_NAME = "SettingsAgent"

    def _get_tools(self) -> List:
        """Get tools specific to settings management."""
        # Start with base tools (recall_history + handoff)
        tools = super()._get_tools()

        # Add settings-specific tools
        settings_tool_names = [
            "toggle_fall_detection",
            "set_sensitivity",
            "set_emergency_delay",
            "toggle_location_tracking",
            "update_location_interval",
            "toggle_watchos_fall_detection",
            "set_watchos_sensitivity",
        ]

        tools.extend(self._get_tools_by_names(settings_tool_names))

        logger.info(f"{self.AGENT_NAME} loaded {len(tools)} tools")

        return tools
