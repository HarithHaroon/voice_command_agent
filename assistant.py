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

logger = logging.getLogger(__name__)


class Assistant(Agent):
    """AI Assistant with extensible tool management."""

    def __init__(self) -> None:
        self.navigation_state = NavigationState()

        # Initialize tool manager
        self.tool_manager = ToolManager()

        # Register tools
        self._register_tools()

        # Instantiate additional tools to expose to the agent

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
                - Use fill_text_field(field_name, value) to fill any text input field. Available fields vary by screen:
                * Face Recognition screen: 'person_name', 'person_details'
                * Contact screen: 'name', 'email', 'phone'
                - For form workflows: collect missing fields incrementally; validate before submit; on failure, report which fields need changes.
                - Always validate forms before attempting submission.
                - Use set_emergency_delay(seconds) to adjust emergency call delay. Valid values: 15, 30, or 60 seconds.

                Preferences policy
                - Save preferences (e.g., default city). Use them when relevant; otherwise, ask once and save.

                - Use toggle_fall_detection() to turn fall detection monitoring on or off

                - Use set_sensitivity(level) to adjust fall detection sensitivity. Valid levels: "gentle", "balanced", "sensitive".

                - Use toggle_location_tracking() to turn background location tracking on or off.

                - Use update_location_interval(interval) to change how often location updates are sent. Valid intervals: 5, 10, 15, or 30 minutes.

                Medication Reminders Policy
                - Use fill_text_field to set reminder fields: 'medication_name', 'dosage', 'instructions' (optional), 'notes' (optional)
                - Use set_reminder_time(hour, minute) for 24-hour format times (e.g., hour=14, minute=30 for 2:30 PM)
                - Use set_reminder_date(year, month, day) for the reminder date (only needed for "once" reminders)
                - Use set_recurrence_type(recurrence_type) with values: "once", "daily", "weekly", or "custom"
                - For custom recurrence, use set_custom_days(days) with day numbers: 1=Monday through 7=Sunday
                - Always validate_reminder_form() before calling submit_reminder()
                - Collect all required information (medication name, dosage, time, recurrence) before submitting.

                WatchOS Fall Detection Policy
                - Use toggle_watchos_fall_detection() to turn fall detection on/off on Apple Watch
                - Use set_watchos_sensitivity(level) to adjust WatchOS fall detection sensitivity
                * Valid levels: "low" (fewer alerts), "medium" (balanced), "high" (more sensitive)
                - WatchOS fall detection is separate from phone-based fall detection
                - The smartwatch monitors movements and can detect falls to alert emergency contacts.

                Video Calling Policy
                - Use start_video_call(family_member_name) to initiate video calls with family members
                - The tool will search for matching family members by name
                - If multiple matches are found, ask the user to be more specific
                - If no match is found, the tool will list available family members
                - After successful match, the video call lobby screen will open automatically

                Error & ambiguity handling
                - Provide short explanations and a next step when tools fail. If multiple navigation targets are similarly relevant, ask the user to choose.
            """,
            tools=(self.tool_manager.get_all_tool_functions()),
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
