"""
Extensible AI Assistant using Tool Manager - LiveKit Cloud Compatible.
"""

import json
import logging
import asyncio
from livekit.agents import Agent, get_job_context

from tools.tool_manager import ToolManager
from tools.time_utils import TimeTool
from tools.form_validation_tool import FormValidationTool
from tools.form_submission_tool import FormSubmissionTool
from tools.text_field_tool import TextFieldTool
from tools.form_orchestration_tool import FormOrchestrationTool
from tools.navigation_tool import NavigationTool

logger = logging.getLogger(__name__)


class SimpleAssistant(Agent):
    """AI Assistant with extensible tool management."""

    def __init__(self) -> None:
        self.navigation_context = None

        # Initialize tool manager
        self.tool_manager = ToolManager()

        # Register tools
        self._register_tools()

        # Initialize agent with all tool functions
        super().__init__(
            instructions="""You are a helpful AI assistant that can execute various tools on the user's device.

            NAVIGATION CAPABILITIES:
            - When users request navigation or ask to access specific features, use the navigate_to_screen tool
            - You receive navigation data at session start with available screens and their descriptions
            - Match user requests to the appropriate screen using the screen descriptions:
            - Use the screen descriptions to intelligently determine which screen contains the requested feature
            - Pass the exact screen route name (not the display name) to the navigate_to_screen tool
            - The tool will automatically calculate the best navigation path from your current location

            Example: If user says "I want to activate fall detection" and you see a screen with route_name "safety_settings" and description "Safety settings including fall detection and emergency contacts", navigate to "safety_settings".

            Always analyze screen descriptions to find the most relevant screen for the user's specific request.""",
            tools=self.tool_manager.get_all_tool_functions(),
        )

    def _register_tools(self):
        """Register all available tools."""
        #! Register Tools
        time_tool = TimeTool()
        self.tool_manager.register_tool(time_tool)

        text_field_tool = TextFieldTool()
        self.tool_manager.register_tool(text_field_tool)

        form_validation_tool = FormValidationTool()
        self.tool_manager.register_tool(form_validation_tool)

        submission_tool = FormSubmissionTool()
        self.tool_manager.register_tool(submission_tool)

        orchestration_tool = FormOrchestrationTool()
        orchestration_tool.set_tools(
            text_field_tool, form_validation_tool, submission_tool
        )
        self.tool_manager.register_tool(orchestration_tool)

        navigation_tool = NavigationTool(agent=self)
        self.tool_manager.register_tool(navigation_tool)

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

            # Store initial navigation context from session init
            if message.get("type") == "session_init":
                self.navigation_context = message.get("navigation", {})
                logger.info(
                    f"Agent {id(self)} stored navigation context: {self.navigation_context}"
                )

            # Update navigation context from tool responses
            elif (
                message.get("type") == "tool_result"
                and message.get("tool") == "navigate_to_screen"
            ):
                if message.get("success") and "result" in message:
                    result = message.get("result", {})
                    if "navigation_stack" in result and self.navigation_context:
                        self.navigation_context["current_stack"] = result[
                            "navigation_stack"
                        ]
                        self.navigation_context["current_screen"] = result[
                            "current_screen"
                        ]
                        logger.info(
                            f"Updated navigation context: current_stack={result['navigation_stack']}, current_screen={result['current_screen']}"
                        )

                # Route tool response to tool manager
                success = self.tool_manager.route_tool_response(message)
                if not success:
                    logger.error("Failed to route tool response")

            # Route other tool responses through tool manager
            elif message.get("type") == "tool_result":
                success = self.tool_manager.route_tool_response(message)
                if not success:
                    logger.error("Failed to route tool response")
            else:
                logger.info(f"Non-tool message type: {message.get('type')}")

        except Exception as e:
            logger.error(f"Data handling error: {e}")
