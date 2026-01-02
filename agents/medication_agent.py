"""
Medication Agent - Manages medications, schedules, dose tracking, and adherence.
"""

import logging
from typing import List

from livekit.agents import function_tool
from agents.base_specialist_agent import BaseSpecialistAgent
from models.shared_state import SharedState

logger = logging.getLogger(__name__)


class MedicationAgent(BaseSpecialistAgent):
    """
    Medication management specialist.

    Responsibilities:
    - Add/view/edit/delete medications
    - Track dose events (taken/skipped/missed)
    - Check drug interactions
    - Calculate adherence
    - Manage refill reminders
    """

    AGENT_NAME = "MedicationAgent"

    def __init__(self, shared_state: SharedState, instructions: str):
        """
        Initialize medication agent.

        Args:
            shared_state: Shared state from session
            instructions: Agent prompt from agent_prompts.medication
        """
        self.shared_state = shared_state

        # Build personalized instructions
        user_name = self.shared_state.user_name

        personalized_instructions = f"""User's name: {user_name}

            {self.BASE_INSTRUCTIONS}

            {instructions}
        """

        # Initialize base agent FIRST (like BacklogAgent does)
        super().__init__(
            instructions=personalized_instructions,
            shared_state=self.shared_state,
        )

        # Update current agent
        self.shared_state.current_agent = self.AGENT_NAME

        # Set session for tools AFTER initialization
        self._set_session_for_tools()

        # Get tool count for logging
        tools = self._get_tools()

        logger.info(
            f"{self.AGENT_NAME} initialized with {len(tools)} tools for user: {user_name}"
        )

    def _set_session_for_tools(self):
        """Set LiveKit session for all medication tools"""
        session = getattr(self.shared_state, "session", None)

        if session:
            tool_names = [
                "add_medication",
                "view_medications",
                "confirm_dose",
                "skip_dose",
                "edit_medication",
                "delete_medication",
            ]

            for tool_name in tool_names:
                tool = self.shared_state.tool_manager.get_tool(tool_name)

                if tool and hasattr(tool, "set_session"):
                    tool.set_session(session)

            logger.info("✅ Session set for medication tools")

    def _get_tools(self) -> List:
        """Get all tools for medication agent."""
        tools = []

        # Medication management tools
        tools.extend(
            self._get_tools_by_names(
                [
                    "add_medication",
                    "view_medications",
                    "edit_medication",
                    "delete_medication",
                ]
            )
        )

        # # Dose tracking tools
        tools.extend(
            self._get_tools_by_names(
                [
                    "confirm_dose",
                    "skip_dose",
                    "query_schedule",
                ]
            )
        )

        # # Monitoring tools
        tools.extend(
            self._get_tools_by_names(
                [
                    "check_adherence",
                    "request_refill",
                ]
            )
        )

        logger.info(f"Loaded {len(tools)} tools for {self.AGENT_NAME}")

        return tools
