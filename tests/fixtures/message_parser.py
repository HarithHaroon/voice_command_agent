"""
Message parser - Extracts tool calls and handoffs from OpenAI messages.
"""

import logging
import json
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class MessageParser:
    """Parses OpenAI messages to extract tool calls and handoffs"""

    @staticmethod
    def extract_tool_calls(message) -> List[str]:
        """Extract tool names from OpenAI message"""
        if not message.tool_calls:
            return []

        tools = []
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name

            # Skip handoff tools for specialist tracking
            if "handoff_to_" not in tool_name:
                tools.append(tool_name)

        return tools

    @staticmethod
    def extract_tool_params(message) -> Dict[str, Any]:
        """Extract tool parameters from OpenAI message"""
        if not message.tool_calls:
            return {}

        params = {}
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name

            try:
                args = json.loads(tool_call.function.arguments)

                params[tool_name] = args
            except Exception as e:
                logger.error(f"Failed to parse tool args: {e}")

                params[tool_name] = {}

        return params

    @staticmethod
    def extract_handoff(result: Dict) -> Optional[Dict]:
        """Extract handoff information from agent result"""
        tool_params = result.get("tool_params", {})

        for tool_name, params in tool_params.items():
            if "handoff_to_" in tool_name:
                # Extract specialist name
                specialist = tool_name.replace("handoff_to_", "").replace("_agent", "")

                specialist_name = f"{specialist.title()}Agent"

                # Get handoff reason
                reason = params.get("reason", "")

                return {"specialist": specialist_name, "reason": reason}

        return None
