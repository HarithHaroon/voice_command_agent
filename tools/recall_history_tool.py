"""
Recall History Tool - Search through past conversation history.
Adapted from Nova Sonic for LiveKit Agent.
"""

import logging
from typing import Optional
from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool

# Import clients from root directory
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.firebase_client import FirebaseClient


logger = logging.getLogger(__name__)


class RecallHistoryTool(ServerSideTool):
    """Tool for searching through past conversation history."""

    def __init__(self):
        super().__init__("recall_history")

        self._user_id = None

        logger.info("RecallHistoryTool initialized with _user_id = None")

        self.firebase_client = None

        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize Firebase client."""
        try:
            self.firebase_client = FirebaseClient()
            logger.info("Firebase client initialized for recall_history")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.firebase_client = None

    def get_tool_methods(self) -> list:
        """Return list of tool methods this class provides."""
        return ["recall_history"]

    def get_tool_functions(self) -> list:
        """Return list of function_tool decorated methods."""
        return [self.recall_history]

    def _convert_timeframe_to_hours(self, timeframe: str) -> Optional[int]:
        """Convert timeframe string to hours."""
        timeframe_map = {
            "1hour": 1,
            "6hours": 6,
            "24hours": 24,
            "7days": 7 * 24,
            "30days": 30 * 24,
            "all": None,
        }
        return timeframe_map.get(timeframe)

    @function_tool
    async def recall_history(
        self, search_query: str, timeframe: str = "all", max_results: int = 10
    ) -> str:
        """
        Search through past conversation history to find relevant messages.

        Args:
            search_query: The search query to find relevant past conversations
            timeframe: Time frame to search within (1hour, 6hours, 24hours, 7days, 30days, all)
            max_results: Maximum number of results to return (1-20)
        """
        try:
            # Validate user_id
            if not self._user_id:
                logger.error("User ID not set for recall_history tool")
                return "Cannot access conversation history without user identification."

            # Validate timeframe
            valid_timeframes = ["1hour", "6hours", "24hours", "7days", "30days", "all"]

            if timeframe not in valid_timeframes:
                return f"Invalid timeframe '{timeframe}'. Must be one of: {', '.join(valid_timeframes)}"

            # Validate max_results
            max_results = max(1, min(20, max_results))

            # Convert timeframe to hours
            timeframe_hours = self._convert_timeframe_to_hours(timeframe)

            logger.info(
                f"Searching history for user {self._user_id}: '{search_query}' "
                f"(timeframe: {timeframe}, max: {max_results})"
            )

            if self.firebase_client is None:
                logger.error("Firebase client not available for history search")
                return "Unable to search conversation history: database connection unavailable."

            # Use a large number of hours for 'all' to effectively get all messages
            search_hours = (
                timeframe_hours if timeframe_hours is not None else 87600
            )  # ~10 years

            recent_messages = await self.firebase_client.get_messages_by_timeframe(
                self._user_id, search_hours
            )

            # Filter messages by keywords
            keywords = search_query.lower().split()
            similar_messages = []
            for message in recent_messages:
                content_lower = message["content"].lower()
                if any(keyword in content_lower for keyword in keywords):
                    similar_messages.append(
                        {
                            "role": message["role"],
                            "content": message["content"],
                        }
                    )

            # Get the most recent results
            similar_messages = similar_messages[-max_results:]

            # Format results for LLM
            if similar_messages:
                # Build natural language response
                result_lines = [
                    f"Found {len(similar_messages)} relevant messages from past conversations:\n"
                ]

                for i, msg in enumerate(similar_messages, 1):
                    role = msg["role"]
                    content = msg["content"]

                    result_lines.append(f"{i}. [{role}]: {content}")

                logger.info(f"Found {len(similar_messages)} relevant messages")
                return "\n".join(result_lines)

            else:
                logger.info(f"No relevant messages found for: {search_query}")
                return (
                    f"I don't have any record of us discussing '{search_query}' "
                    f"in the past {timeframe}."
                )

        except Exception as e:
            logger.error(f"Error in recall_history: {e}", exc_info=True)
            return f"I encountered an error searching conversation history: {str(e)}"
