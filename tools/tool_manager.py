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

        self.agent_session = None

        self._method_to_tool: Dict[str, BaseTool] = {}

    # 🆕 ADD THIS METHOD at the end of the class
    def set_session(self, session):
        """Store LiveKit session for tools."""
        self.agent_session = session
        logger.info("Session stored in ToolManager")

    def register_tool(self, tool: BaseTool):
        """Register a tool with the manager."""
        tool_name = tool.tool_name

        if tool_name in self._tools:
            logger.warning(f"Tool {tool_name} already registered, replacing")

        self._tools[tool_name] = tool

        self._tool_functions.extend(tool.get_tool_functions())

        for method_name in tool.get_tool_methods():
            self._method_to_tool[method_name] = tool

        logger.info(f"Registered tool: {tool_name}")

    def set_agent_for_all_tools(self, agent):
        """Set the agent reference for all registered tools."""
        for tool in self._tools.values():
            tool.set_agent(agent)

    def set_user_id_for_all_tools(self, user_id: str):
        """Set the user_id for all registered tools that support it."""
        for tool in self._tools.values():
            if hasattr(tool, "set_user_id"):
                tool.set_user_id(user_id)
                logger.info(f"Set user_id for {tool.tool_name}")

    def set_time_tracker_for_all_tools(self, time_tracker):
        """Set the time_tracker for all registered tools that support it."""
        for tool in self._tools.values():
            if hasattr(tool, "set_time_tracker"):
                tool.set_time_tracker(time_tracker)
                logger.info(f"Set time_tracker for {tool.tool_name}")

    def get_all_tool_functions(self) -> List:
        """Get all tool functions for the agent."""
        return self._tool_functions

    def route_tool_response(self, response_data: Dict[str, Any]) -> bool:
        """Route a tool response to the appropriate tool."""
        request_id = response_data.get("request_id", "")

        tool_name = response_data.get("tool", "")

        logger.info(f"Routing response - ID: {request_id}, Tool: {tool_name}")

        # ✅ O(1) lookup by method name
        if tool_name in self._method_to_tool:
            tool = self._method_to_tool[tool_name]

            logger.info(f"Routing to {tool.tool_name}...")

            tool.handle_tool_response(response_data)

            return True

        # ✅ Fallback: check by request_id prefix (for edge cases)
        for tool in self._tools.values():
            if request_id.startswith(f"{tool.tool_name}_"):  # ✅ Direct prefix check

                logger.info(f"Routing to {tool.tool_name} by request_id...")

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
