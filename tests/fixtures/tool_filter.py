"""
Tool filter - Filters tools based on intent.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ToolFilter:
    """Filters tools to only those relevant for a given intent"""

    INTENT_FILTERS = {
        "health": lambda name: "health" in name,
        "medication": lambda name: "medication" in name,
        "backlog": lambda name: "backlog" in name or "reminder" in name,
        "memory": lambda name: "memory" in name
        or name
        in [
            "store_item_location",
            "find_item",
            "store_information",
            "recall_information",
            "log_activity",
            "get_daily_context",
            "what_was_i_doing",
        ],
        "story": lambda name: "story" in name  # ← ADD THIS LINE
        or name
        in [
            "record_story",
            "find_stories",
            "get_story",
            "list_my_stories",
            "get_story_summary",
        ],
        "settings": lambda name: "settings" in name,
        "books": lambda name: "books" in name,
        "image": lambda name: "image" in name,
        "orchestrator": lambda name: "handoff" not in name,
    }

    @classmethod
    def filter_tools(
        cls,
        tools: List[Dict[str, Any]],
        intent: str,
    ) -> List[Dict[str, Any]]:
        """
        Filter tools based on intent.

        Args:
            tools: List of OpenAI tool definitions
            intent: Intended specialist (e.g., "health", "medication")

        Returns:
            Filtered list of relevant tools
        """
        filter_fn = cls.INTENT_FILTERS.get(intent)

        if not filter_fn:
            # Unknown intent, return all non-handoff tools
            filter_fn = cls.INTENT_FILTERS["orchestrator"]

        relevant_tools = [t for t in tools if filter_fn(t["function"]["name"])]

        logger.info(f"Filtered to {len(relevant_tools)} tools for intent: {intent}")

        return relevant_tools
