"""
Tool Manager for handling multiple client-side tools.
"""

import logging
from typing import Dict, List, Any
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages registration and routing of client-side tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_functions: List = []

    def register_tool(self, tool: BaseTool):
        """Register a tool with the manager."""
        tool_name = tool.tool_name
        if tool_name in self._tools:
            logger.warning(f"Tool {tool_name} already registered, replacing")

        self._tools[tool_name] = tool
        self._tool_functions.extend(tool.get_tool_functions())
        logger.info(f"Registered tool: {tool_name}")

    def set_agent_for_all_tools(self, agent):
        """Set the agent reference for all registered tools."""
        for tool in self._tools.values():
            tool.set_agent(agent)

    def get_all_tool_functions(self) -> List:
        """Get all tool functions for the agent."""
        return self._tool_functions

    def route_tool_response(self, response_data: Dict[str, Any]) -> bool:
        """Route a tool response to the appropriate tool."""
        request_id = response_data.get("request_id", "")
        tool_name = response_data.get("tool", "")

        logger.info(f"Routing response - ID: {request_id}, Tool: {tool_name}")

        # Try to find the right tool to handle this response
        for tool in self._tools.values():
            if tool.can_handle_request(request_id, tool_name):
                logger.info(f"Routing to {tool.tool_name}...")
                tool.handle_tool_response(response_data)
                return True

        logger.warning(
            f"No tool found to handle response: {tool_name} (ID: {request_id})"
        )
        return False

    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    def get_tool_count(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)
