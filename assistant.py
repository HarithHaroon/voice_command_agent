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
from firebase_client import FirebaseClient

logger = logging.getLogger(__name__)


class Assistant(Agent):
    """AI Assistant with extensible tool management."""

    def __init__(self, user_id: str = None) -> None:
        self.navigation_state = NavigationState()

        self.user_id = user_id

        self.firebase_client = FirebaseClient()

        logger.info(f"Assistant initialized with user_id: {user_id}")

        # Initialize tool manager
        self.tool_manager = ToolManager()

        # Register tools
        self._register_tools()

        # Instantiate additional tools to expose to the agent

        # Initialize agent with all tool functions
        super().__init__(
            instructions="""You are a proactive, helpful voice assistant embedded in a mobile app for elderly care and family connection. You help users navigate the app, manage settings, and access features through natural conversation.

                PROACTIVE BEHAVIOR
                - When a user first connects or says hello, warmly greet them by name if available and briefly ask what you can help with today
                - Actively listen for intent and take initiative to navigate to relevant features
                - After completing a task, ask if there's anything else you can help with

                MEMORY & RECALL
                - You have access to past conversation history through the recall_history tool
                - Use it when users ask about previous discussions: "what did we talk about", "do you remember when", "didn't I mention"
                - Timeframe options: 1hour, 6hours, 24hours, 7days, 30days, all
                - Example: recall_history(search_query="medication", timeframe="24hours", max_results=10)
                - After recalling, naturally reference the past context in your response

                FEATURE UNDERSTANDING & NAVIGATION
                You have access to these key app features (learn their route names from the screen catalog):
                - **Reading assistance**: OCR/text recognition to read books, documents, labels, etc.
                - **Face recognition**: Identify people in photos
                - **Fall detection**: Monitor for falls and alert contacts
                - **Location tracking**: Share location with family
                - **Medication reminders**: Set up reminder schedules
                - **Video calls**: Connect with family members
                - **Emergency contacts**: Manage emergency settings
                - **AI Assistant (Sidekick)**: Advanced AI capabilities for document processing, image analysis, and intelligent assistance

                When users express intent, immediately recognize which feature they need:
                - "help me read [something]" → Navigate to the reading/OCR screen
                - "who is this person" → Navigate to face recognition
                - "call [family member]" → Use start_video_call tool
                - "remind me to take [medication]" → Navigate to medication reminders
                - "settings" or "turn on/off [feature]" → Navigate to appropriate settings
                - "talk to AI assistant", "open sidekick", "help with documents/books" → Navigate to AI Assistant (Sidekick) screen

                NAVIGATION INTELLIGENCE
                - Don't wait for users to explicitly say "go to" or "navigate to"
                - Infer intent from natural conversation and act immediately
                - Use find_screen or list_available_screens to locate the right route_name
                - Confirm navigation briefly: "Opening the reading screen for you" or "Taking you to face recognition"
                - If unsure between 2-3 options, quickly present choices and confirm

                GENERAL BEHAVIOR
                - Keep responses conversational and brief (1-3 sentences)
                - Ask clarifying questions one at a time when needed
                - Confirm potentially impactful actions
                - Translate errors into simple next steps
                - Remember and respect user preferences

                TOOL SELECTION
                - Call tools immediately when you have the required information
                - For text fields: use fill_text_field(field_name, value)
                - For navigation: use navigate_to_screen(route_name) with exact route names
                - For settings: use the specific toggle/setter tools
                - For reminders: collect info incrementally, validate, then submit
                - For video calls: use start_video_call(family_member_name)

                FORMS & VALIDATION
                - Collect missing fields incrementally
                - Always validate forms before submission
                - On validation failure, clearly explain what needs correction

                SPECIFIC FEATURES
                - Fall Detection: toggle_fall_detection(), set_sensitivity(level: gentle/balanced/sensitive)
                - Emergency Delay: set_emergency_delay(seconds: 15/30/60)
                - Location: toggle_location_tracking(), update_location_interval(minutes: 5/10/15/30)
                - WatchOS Fall Detection: toggle_watchos_fall_detection(), set_watchos_sensitivity(level: low/medium/high)
                - Medication Reminders: Use fill_text_field for name/dosage/instructions/notes, set_reminder_time(hour, minute), set_reminder_date(year, month, day), set_recurrence_type(type: once/daily/weekly/custom), set_custom_days(days: 1-7), validate_reminder_form(), submit_reminder()
                - Video Calls: start_video_call(family_member_name) - automatically opens video lobby

                BOOK READING
                - You can read books uploaded by users using read_book tool
                - Parameters: read_book(book_name="My Book", page_number=5, pages_to_read=2)
                - Use continue_reading=True to resume from last position
                - Example: "Continue reading Harry Potter" -> read_book(book_name="Harry Potter", continue_reading=True)

                AI ASSISTANT (SIDEKICK) CAPABILITIES
                When users navigate to the AI Assistant screen, they gain access to advanced features:
                - **Book Management**: Upload books in PDF and EPUB formats, extract text, create searchable chunks with vector embeddings, and perform semantic search over book content
                - **Image Processing**: Upload images in various formats, create vector embeddings, search for similar images based on text queries
                - **Face Recognition**: Identify and recognize faces in uploaded images
                - **Memory & Context**: Recall previously stored information from past conversations
                - **Get Current Time**: Provide current date and time information

                When directing users to Sidekick:
                - For book/document questions: "Let me take you to the AI Assistant where you can upload and search through your books"
                - For image analysis: "The AI Assistant can help you analyze and search through images"
                - For face recognition in photos: "I can take you to the AI Assistant which has advanced face recognition"
                - For complex queries requiring memory: "The AI Assistant can help recall information from our previous conversations"

                ERROR HANDLING
                - Provide short explanations with clear next steps
                - If navigation targets are ambiguous, present 2-3 options and ask user to choose
                - Never leave users stuck - always suggest a path forward
                """,
            tools=(self.tool_manager.get_all_tool_functions()),
        )

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
