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
from models.navigation_state import NavigationState
from tools.toggle_fall_detection_tool import ToggleFallDetectionTool
from tools.fall_detection_sensitivity_tool import FallDetectionSensitivityTool
from tools.emergency_delay_tool import EmergencyDelayTool
from tools.toggle_location_tracking_tool import ToggleLocationTrackingTool
from tools.update_location_interval_tool import UpdateLocationIntervalTool
from tools.reminder_tools.set_custom_days_tool import SetCustomDaysTool
from tools.reminder_tools.set_recurrence_type_tool import SetRecurrenceTypeTool
from tools.reminder_tools.set_reminder_date_tool import SetReminderDateTool
from tools.reminder_tools.set_reminder_time_tool import SetReminderTimeTool
from tools.reminder_tools.submit_reminder_tool import SubmitReminderTool
from tools.reminder_tools.validate_reminder_form_tool import ValidateReminderFormTool
from tools.toggle_watchos_fall_detection_tool import ToggleWatchosFallDetectionTool
from tools.set_watchos_sensitivity_tool import SetWatchosSensitivityTool
from tools.start_video_call_tool import StartVideoCallTool
from tools.recall_history_tool import RecallHistoryTool
from tools.read_book_tool import ReadBookTool
from clients.firebase_client import FirebaseClient
from tools.rag_books_tool import RagBooksTool
from tools.query_image_tool import QueryImageTool
from intent_detection.intent_detector import IntentDetector
from prompt_management.prompt_module_manager import PromptModuleManager
from tools.backlog_tools.add_reminder_tool import AddReminderTool
from tools.backlog_tools.view_upcoming_reminders_tool import ViewUpcomingRemindersTool
from tools.backlog_tools.complete_reminder_tool import CompleteReminderTool
from tools.backlog_tools.delete_reminder_tool import DeleteReminderTool
from tools.backlog_tools.list_all_reminders_tool import ListAllRemindersTool


logger = logging.getLogger(__name__)


class Assistant(Agent):
    """AI Assistant with extensible tool management."""

    def __init__(self, user_id: str = None) -> None:
        # Existing navigation and Firebase setup
        self.navigation_state = NavigationState()
        self.user_id = user_id
        self.firebase_client = FirebaseClient()

        logger.info(f"Assistant initialized with user_id: {user_id}")

        # Initialize tool manager
        self.tool_manager = ToolManager()

        # Register tools
        self._register_tools()

        # 🆕 NEW: Initialize modular prompt system
        self.module_manager = PromptModuleManager()
        self.intent_detector = IntentDetector()
        self.current_modules = ["navigation", "memory_recall"]
        self.conversation_history = []

        # Assemble initial instructions from base + default modules
        base_instructions = self.module_manager.assemble_instructions(
            modules=self.current_modules
        )

        # Initialize agent with dynamically assembled instructions
        super().__init__(
            instructions=base_instructions,  # 🔄 Changed from hard-coded string to dynamic instructions
            tools=(self.tool_manager.get_all_tool_functions()),
        )

        logger.info(f"Assistant ready | Active modules: {self.current_modules}")

    async def save_message_to_firebase(self, role: str, content: str):
        """Save message to Firebase (called from event handler)"""
        if self.user_id and content:
            await asyncio.to_thread(
                self.firebase_client.add_message,
                self.user_id,
                role.upper(),  # "USER" or "ASSISTANT"
                content,
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

        toggle_fall_detection_tool = ToggleFallDetectionTool()
        self.tool_manager.register_tool(toggle_fall_detection_tool)

        sensitivity_tool = FallDetectionSensitivityTool()
        self.tool_manager.register_tool(sensitivity_tool)

        emergency_delay_tool = EmergencyDelayTool()
        self.tool_manager.register_tool(emergency_delay_tool)

        toggle_location_tracking_tool = ToggleLocationTrackingTool()
        self.tool_manager.register_tool(toggle_location_tracking_tool)

        update_location_interval_tool = UpdateLocationIntervalTool()
        self.tool_manager.register_tool(update_location_interval_tool)

        #! Reminder tools
        set_reminder_time_tool = SetReminderTimeTool()
        self.tool_manager.register_tool(set_reminder_time_tool)

        set_reminder_date_tool = SetReminderDateTool()
        self.tool_manager.register_tool(set_reminder_date_tool)

        set_recurrence_type_tool = SetRecurrenceTypeTool()
        self.tool_manager.register_tool(set_recurrence_type_tool)

        set_custom_days_tool = SetCustomDaysTool()
        self.tool_manager.register_tool(set_custom_days_tool)

        validate_reminder_form_tool = ValidateReminderFormTool()
        self.tool_manager.register_tool(validate_reminder_form_tool)

        submit_reminder_tool = SubmitReminderTool()
        self.tool_manager.register_tool(submit_reminder_tool)

        #! WatchOS fall detection tools
        toggle_watchos_fall_detection_tool = ToggleWatchosFallDetectionTool()
        self.tool_manager.register_tool(toggle_watchos_fall_detection_tool)

        set_watchos_sensitivity_tool = SetWatchosSensitivityTool()
        self.tool_manager.register_tool(set_watchos_sensitivity_tool)

        logger.info(
            f"Registered {self.tool_manager.get_tool_count()} tools: {self.tool_manager.get_registered_tools()}"
        )

        #! Video call tool
        start_video_call_tool = StartVideoCallTool()
        self.tool_manager.register_tool(start_video_call_tool)

        #! Recall History tool (server-side)
        recall_history_tool = RecallHistoryTool()
        self.tool_manager.register_tool(recall_history_tool)

        #! read book tool
        read_book_tool = ReadBookTool()
        self.tool_manager.register_tool(read_book_tool)

        #! RAG books tool
        rag_books_tool = RagBooksTool()
        self.tool_manager.register_tool(rag_books_tool)

        #! Query image tool
        query_image_tool = QueryImageTool()
        self.tool_manager.register_tool(query_image_tool)

        #! Backlog reminder tools (server-side)
        add_reminder_tool = AddReminderTool()
        self.tool_manager.register_tool(add_reminder_tool)

        view_upcoming_reminders_tool = ViewUpcomingRemindersTool()
        self.tool_manager.register_tool(view_upcoming_reminders_tool)

        complete_reminder_tool = CompleteReminderTool()
        self.tool_manager.register_tool(complete_reminder_tool)

        delete_reminder_tool = DeleteReminderTool()
        self.tool_manager.register_tool(delete_reminder_tool)

        list_all_reminders_tool = ListAllRemindersTool()
        self.tool_manager.register_tool(list_all_reminders_tool)

    async def on_enter(self):
        """Called when the agent enters a room."""
        logger.info("Assistant entered the room")

        # Set agent reference for all tools
        self.tool_manager.set_agent_for_all_tools(self)

        # Set user_id for all tools that need it
        if self.user_id:
            self.tool_manager.set_user_id_for_all_tools(self.user_id)

        # Set up data handler
        await self._setup_data_handler()

    async def _setup_data_handler(self):
        """Setup data handler using job context."""
        try:
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

            # Route all tool responses through tool manager first
            elif message.get("type") == "tool_result":
                success = self.tool_manager.route_tool_response(message)
                if not success:
                    logger.error("Failed to route tool response")

                # Update navigation state if this was a successful navigation
                if (
                    message.get("tool") == "navigate_to_screen"
                    and message.get("success")
                    and "result" in message
                ):
                    result = message.get("result", {})
                    if "navigation_stack" in result and "current_screen" in result:
                        self.navigation_state.update_from_navigation_success(
                            result["navigation_stack"], result["current_screen"]
                        )
            else:
                logger.info(f"Non-tool message type: {message.get('type')}")

        except Exception as e:
            logger.error(f"Data handling error: {e}")

    async def on_leave(self):
        """Called when the agent leaves the room."""
        logger.info("Assistant leaving the room - cleaning up navigation state")
        self.navigation_state.clear()
