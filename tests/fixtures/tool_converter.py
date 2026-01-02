"""
Tool converter - Converts LiveKit tools to OpenAI format.
"""

import logging
import inspect
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ToolConverter:
    """Converts LiveKit function tools to OpenAI tool format"""

    @staticmethod
    def convert_tools(tools: List) -> List[Dict[str, Any]]:
        """
        Convert LiveKit tools to OpenAI format.

        Args:
            tools: List of LiveKit tool functions

        Returns:
            List of OpenAI tool definitions
        """
        openai_tools = []

        for tool in tools:
            try:
                converted = ToolConverter._convert_single_tool(tool)
                if converted:
                    openai_tools.append(converted)
                    logger.debug(f"Converted tool: {tool.__name__}")
            except Exception as e:
                logger.warning(f"Failed to convert tool {tool}: {e}")
                continue

        logger.info(f"Converted {len(openai_tools)} tools for OpenAI")
        return openai_tools

    @staticmethod
    def _convert_single_tool(tool) -> Dict[str, Any]:
        """Convert a single tool function to OpenAI format"""
        # Extract metadata from function
        tool_name = tool.__name__
        tool_doc = tool.__doc__ or "No description"
        sig = inspect.signature(tool)

        # Build parameters schema
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Get type annotation
            param_type = ToolConverter._get_param_type(param.annotation)

            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}",
            }

            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        # Build OpenAI tool definition
        return {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_doc.strip(),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    @staticmethod
    def _get_param_type(annotation) -> str:
        """Convert Python type annotation to JSON schema type"""
        if annotation == inspect.Parameter.empty:
            return "string"

        if annotation == str:
            return "string"
        elif annotation == int:
            return "integer"
        elif annotation == bool:
            return "boolean"
        elif annotation == float:
            return "number"
        elif annotation == list:
            return "array"
        elif annotation == dict:
            return "object"
        else:
            return "string"  # default
