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
        "backlog": lambda name: "backlog" in name,
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
