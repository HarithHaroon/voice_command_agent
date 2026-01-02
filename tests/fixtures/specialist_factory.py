"""
Specialist factory - Creates specialist agent instances.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SpecialistFactory:
    """Factory for creating specialist agents"""

    @staticmethod
    def create_specialist(specialist_name: str, shared_state, instructions: str):
        """
        Create specialist agent instance.

        Args:
            specialist_name: Name of specialist (e.g., "HealthAgent")
            shared_state: SharedState instance
            instructions: Agent instructions

        Returns:
            Specialist agent instance or None if not found
        """
        from agents.health_agent import HealthAgent
        from agents.backlog_agent import BacklogAgent
        from agents.books_agent import BooksAgent
        from agents.settings_agent import SettingsAgent
        from agents.image_agent import ImageAgent
        from agents.medication_agent import MedicationAgent

        agent_map = {
            "HealthAgent": HealthAgent,
            "BacklogAgent": BacklogAgent,
            "BooksAgent": BooksAgent,
            "SettingsAgent": SettingsAgent,
            "ImageAgent": ImageAgent,
            "MedicationAgent": MedicationAgent,
        }

        agent_class = agent_map.get(specialist_name)
        if not agent_class:
            logger.error(f"Unknown specialist: {specialist_name}")

            return None

        logger.info(f"Creating specialist: {specialist_name}")

        return agent_class(shared_state, instructions)

    @staticmethod
    def get_specialist_instructions(specialist_name: str, agent_prompts) -> str:
        """
        Get instructions for specialist.

        Args:
            specialist_name: Name of specialist (e.g., "HealthAgent")
            agent_prompts: AgentPrompts instance

        Returns:
            Specialist instructions
        """
        prompt_map = {
            "HealthAgent": agent_prompts.health,
            "BacklogAgent": agent_prompts.backlog,
            "BooksAgent": agent_prompts.books,
            "SettingsAgent": agent_prompts.settings,
            "ImageAgent": agent_prompts.image,
            "MedicationAgent": agent_prompts.medication,
        }

        return prompt_map.get(specialist_name, "")
