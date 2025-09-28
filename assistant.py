"""
Extensible AI Assistant using Tool Manager - LiveKit Cloud Compatible.
"""

import json
import logging
import asyncio
from livekit.agents import Agent, get_job_context

from tools.tool_manager import ToolManager
from tools.form_validation_tool import FormValidationTool
from tools.form_submission_tool import FormSubmissionTool
from tools.text_field_tool import TextFieldTool
from tools.form_orchestration_tool import FormOrchestrationTool
from tools.navigation_tool import NavigationTool
from tools.preferences import PreferencesTool
from models.navigation_state import NavigationState

logger = logging.getLogger(__name__)


class SimpleAssistant(Agent):
    """AI Assistant with extensible tool management."""

    def __init__(self) -> None:
        self.navigation_state = NavigationState()

        # Initialize tool manager
        self.tool_manager = ToolManager()

        # Register tools
        self._register_tools()

        # Instantiate additional tools to expose to the agent
        self.preferences_tool = PreferencesTool()

        # Initialize agent with all tool functions
        super().__init__(
            instructions="""You are a precise, helpful voice assistant embedded in a mobile app. You can call tools to navigate the app, work with forms, and manage user preferences.

General behavior
- Ask clarifying questions before acting when requests are incomplete or ambiguous; collect missing details one at a time.
- Confirm potentially surprising or impactful actions when confidence is low (e.g., leaving the current task or opening settings).
- Prefer short, direct answers (a few sentences). If a tool errors, translate it into actionable next steps (retry, choose an alternative, or provide missing info).
- Respect saved user preferences; consult them before asking again.

Tool selection rubric
- Only call a tool if inputs are known and it best matches the intent.
- If a navigation destination is unclear, first list or search available screens, then confirm the destination.
- Prefer asking a targeted question over guessing. If no tool fits, reply conversationally and ask for the needed detail.

Navigation policy
- You receive a catalog of screens (route_name, display_name, description) at session start.
- Map user requests to route_name via screen descriptions, not display names.
- When certain: call navigate_to_screen with the exact route_name.
- When uncertain or multiple candidates match: use list_available_screens or find_screen and present 2–3 top candidates; ask the user to pick one.
- After successful navigation, briefly confirm the new location using the current screen name.

Forms policy
- For contact form workflows: collect missing fields (name, email, phone) incrementally; validate before submit; on failure, report which fields need changes.

Preferences policy
- Save preferences (e.g., default city). Use them when relevant; otherwise, ask once and save.

Error & ambiguity handling
- Provide short explanations and a next step when tools fail. If multiple navigation targets are similarly relevant, ask the user to choose.
""",
            tools=(
                self.tool_manager.get_all_tool_functions()
                + [
                    self.preferences_tool.save_user_preference,
                    self.preferences_tool.get_user_preference,
                ]
            ),
        )

    def _register_tools(self):
        """Register all available tools."""
        #! Register Tools
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
                navigation_data = message.get("navigation", {})
                self.navigation_state.initialize_from_session(navigation_data)

            elif (
                message.get("type") == "tool_result"
                and message.get("tool") == "navigate_to_screen"
            ):
                if message.get("success") and "result" in message:
                    result = message.get("result", {})
                    if "navigation_stack" in result and "current_screen" in result:
                        self.navigation_state.update_from_navigation_success(
                            result["navigation_stack"], result["current_screen"]
                        )

                # Route tool response to tool manager (unchanged)
                success = self.tool_manager.route_tool_response(message)
                if not success:
                    logger.error("Failed to route tool response")

            # Route other tool responses (unchanged)
            elif message.get("type") == "tool_result":
                success = self.tool_manager.route_tool_response(message)
                if not success:
                    logger.error("Failed to route tool response")
            else:
                logger.info(f"Non-tool message type: {message.get('type')}")

        except Exception as e:
            logger.error(f"Data handling error: {e}")

    async def on_leave(self):
        """Called when the agent leaves the room."""
        logger.info("Assistant leaving the room - cleaning up navigation state")
        self.navigation_state.clear()
