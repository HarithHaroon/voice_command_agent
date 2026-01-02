"""
Books Agent - Specialist for reading books and searching book content.
"""

import logging
from typing import List
from livekit.agents import Agent
from models.shared_state import SharedState
from agents.base_specialist_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class BooksAgent(BaseSpecialistAgent):
    """
    Specialist agent for reading books aloud and answering questions about book content.
    Handles:
    - Reading books page by page (audiobook-style narration)
    - Continuing reading from last position
    - Searching book content to answer questions (RAG)
    """

    AGENT_NAME = "BooksAgent"

    def _get_tools(self) -> List:
        """Get tools specific to books."""
        # Start with base tools (recall_history + handoff)
        tools = super()._get_tools()

        # Add books-specific tools
        books_tool_names = [
            "read_book",
            "rag_books_tool",
        ]

        tools.extend(self._get_tools_by_names(books_tool_names))

        logger.info(f"{self.AGENT_NAME} loaded {len(tools)} tools")

        return tools
