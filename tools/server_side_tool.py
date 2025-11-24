"""
Base class for server-side tools that don't require Flutter client interaction.
"""

import logging
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger(__name__)


class ServerSideTool(ABC):
    """Abstract base class for server-side tools that execute without Flutter client."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name

        self._user_id = None

        self._time_tracker = None

        logger.info(f"ServerSideTool '{tool_name}' initialized")

    def set_user_id(self, user_id: str):
        """Set the current user ID for this tool instance."""
        self._user_id = user_id
        logger.info(f"Set user_id for {self.tool_name}: {user_id}")

    def set_time_tracker(self, time_tracker):
        """Set the time tracker for accurate client time."""
        self._time_tracker = time_tracker
        logger.info(f"Set time_tracker for {self.tool_name}")

    def set_agent(self, agent):
        """Set agent reference (for compatibility with ToolManager)."""
        # Server-side tools don't need agent reference, but this method
        # is called by ToolManager, so we provide a no-op implementation
        pass

    @abstractmethod
    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names this class provides."""
        pass

    @abstractmethod
    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        pass
