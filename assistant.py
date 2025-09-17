"""
Extensible AI Assistant using Tool Manager - LiveKit Cloud Compatible.
"""

import json
import logging
import asyncio
from livekit.agents import Agent, get_job_context

from tools.tool_manager import ToolManager
from tools.time_utils import TimeTool
from tools.name_field_tool import NameFieldTool

logger = logging.getLogger(__name__)


class SimpleAssistant(Agent):
    """AI Assistant with extensible tool management."""

    def __init__(self) -> None:
        # Initialize tool manager
        self.tool_manager = ToolManager()

        # Register tools
        self._register_tools()

        # Initialize agent with all tool functions
        super().__init__(
            instructions="You are a helpful AI assistant that can execute various tools on the user's device.",
            tools=self.tool_manager.get_all_tool_functions(),
        )

    def _register_tools(self):
        """Register all available tools."""
        # Register TimeTool
        time_tool = TimeTool()
        self.tool_manager.register_tool(time_tool)

        name_field_tool = NameFieldTool()
        self.tool_manager.register_tool(name_field_tool)

        logger.info(
            f"Registered {self.tool_manager.get_tool_count()} tools: {self.tool_manager.get_registered_tools()}"
        )

    async def on_enter(self):
        """Called when the agent enters a room."""
        logger.info("Assistant entered the room")

        # Set agent reference for all tools
        self.tool_manager.set_agent_for_all_tools(self)

        # Set up data handler
        await self._setup_data_handler()

    async def _setup_data_handler(self):
        """Setup data handler using job context."""
        try:
            await asyncio.sleep(1)  # Wait for initialization

            ctx = get_job_context()
            if ctx and ctx.room:
                ctx.room.on("data_received", self._handle_data)
                logger.info("Data handler registered successfully")
            else:
                logger.error("No job context room available")

        except Exception as e:
            logger.error(f"Data handler setup failed: {e}")

    def _handle_data(self, data, participant=None):
        """Handle incoming data and route to appropriate tools."""
        logger.info("Data received!")

        try:
            # Extract message bytes
            if hasattr(data, "data"):
                message_bytes = data.data
            else:
                message_bytes = data

            # Parse message
            message = json.loads(message_bytes.decode("utf-8"))
            logger.info(f"Parsed message: {message}")

            # Route tool responses through tool manager
            if message.get("type") == "tool_result":
                success = self.tool_manager.route_tool_response(message)
                if not success:
                    logger.error("Failed to route tool response")
            else:
                logger.info(f"Non-tool message type: {message.get('type')}")

        except Exception as e:
            logger.error(f"Data handling error: {e}")
