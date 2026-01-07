"""
Tool Registry - Centralized tool registration for the Assistant.
"""

import logging
from typing import TYPE_CHECKING

from models.navigation_state import NavigationState
from clients.firebase_client import FirebaseClient
from backlog.backlog_manager import BacklogManager
from clients.health_data_client import HealthDataClient
from tools.health_query_tool import HealthQueryTool
from clients.memory_client import MemoryClient


if TYPE_CHECKING:
    from tools.tool_manager import ToolManager


logger = logging.getLogger(__name__)


class ToolRegistry:
    """Handles registration of all assistant tools."""

    @staticmethod
    def register_all_tools(
        tool_manager: "ToolManager",
        navigation_state: "NavigationState",
        firebase_client: "FirebaseClient",
        backlog_manager: "BacklogManager",
        memory_client: "MemoryClient",
    ) -> None:
        """
        Register all available tools with the tool manager.

        Args:
            tool_manager: ToolManager instance
            navigation_state: NavigationState instance
            firebase_client: FirebaseClient instance
            backlog_manager: BacklogManager instance
        """
        from tools.navigation_tool import NavigationTool
        from tools.toggle_fall_detection_tool import ToggleFallDetectionTool
        from tools.fall_detection_sensitivity_tool import FallDetectionSensitivityTool
        from tools.emergency_delay_tool import EmergencyDelayTool
        from tools.toggle_location_tracking_tool import ToggleLocationTrackingTool
        from tools.update_location_interval_tool import UpdateLocationIntervalTool
        from tools.toggle_watchos_fall_detection_tool import (
            ToggleWatchosFallDetectionTool,
        )
        from tools.set_watchos_sensitivity_tool import SetWatchosSensitivityTool
        from tools.start_video_call_tool import StartVideoCallTool
        from tools.recall_history_tool import RecallHistoryTool
        from tools.read_book_tool import ReadBookTool
        from tools.rag_books_tool import RagBooksTool
        from tools.query_image_tool import QueryImageTool
        from tools.backlog_tools.add_reminder_tool import AddReminderTool
        from tools.backlog_tools.view_upcoming_reminders_tool import (
            ViewUpcomingRemindersTool,
        )
        from tools.backlog_tools.complete_reminder_tool import CompleteReminderTool
        from tools.backlog_tools.delete_reminder_tool import DeleteReminderTool
        from tools.backlog_tools.list_all_reminders_tool import ListAllRemindersTool
        from tools.medication_tools.view_medications_tool import ViewMedicationsTool
        from tools.medication_tools.add_medication_tool import AddMedicationTool
        from tools.medication_tools.confirm_dose_tool import ConfirmDoseTool
        from tools.medication_tools.skip_dose_tool import SkipDoseTool
        from tools.medication_tools.query_schedule_tool import QueryScheduleTool
        from tools.medication_tools.check_adherence_tool import CheckAdherenceTool
        from tools.medication_tools.request_refill_tool import RequestRefillTool
        from tools.medication_tools.edit_medication_tool import EditMedicationTool
        from tools.medication_tools.delete_medication_tool import DeleteMedicationTool
        from tools.memory_tool import MemoryTool
        from tools.story_tool import StoryTool
        from clients.story_client import StoryClient

        # Navigation tool
        navigation_tool = NavigationTool(navigation_state=navigation_state)

        tool_manager.register_tool(navigation_tool)

        # Fall detection tools
        toggle_fall_detection_tool = ToggleFallDetectionTool()

        tool_manager.register_tool(toggle_fall_detection_tool)

        sensitivity_tool = FallDetectionSensitivityTool()

        tool_manager.register_tool(sensitivity_tool)

        emergency_delay_tool = EmergencyDelayTool()
        tool_manager.register_tool(emergency_delay_tool)

        # Location tracking tools
        toggle_location_tracking_tool = ToggleLocationTrackingTool()

        tool_manager.register_tool(toggle_location_tracking_tool)

        update_location_interval_tool = UpdateLocationIntervalTool()

        tool_manager.register_tool(update_location_interval_tool)

        # WatchOS fall detection tools
        toggle_watchos_fall_detection_tool = ToggleWatchosFallDetectionTool()

        tool_manager.register_tool(toggle_watchos_fall_detection_tool)

        set_watchos_sensitivity_tool = SetWatchosSensitivityTool()

        tool_manager.register_tool(set_watchos_sensitivity_tool)

        # Communication tools
        start_video_call_tool = StartVideoCallTool()

        tool_manager.register_tool(start_video_call_tool)

        # Memory and content tools
        recall_history_tool = RecallHistoryTool(firebase_client=firebase_client)

        tool_manager.register_tool(recall_history_tool)

        read_book_tool = ReadBookTool()

        tool_manager.register_tool(read_book_tool)

        rag_books_tool = RagBooksTool()

        tool_manager.register_tool(rag_books_tool)

        query_image_tool = QueryImageTool()

        tool_manager.register_tool(query_image_tool)

        # Backlog reminder tools
        add_reminder_tool = AddReminderTool(backlog_manager=backlog_manager)

        tool_manager.register_tool(add_reminder_tool)

        view_upcoming_reminders_tool = ViewUpcomingRemindersTool(
            backlog_manager=backlog_manager
        )

        tool_manager.register_tool(view_upcoming_reminders_tool)

        complete_reminder_tool = CompleteReminderTool(backlog_manager=backlog_manager)

        tool_manager.register_tool(complete_reminder_tool)

        delete_reminder_tool = DeleteReminderTool(backlog_manager=backlog_manager)

        tool_manager.register_tool(delete_reminder_tool)

        list_all_reminders_tool = ListAllRemindersTool(backlog_manager=backlog_manager)

        tool_manager.register_tool(list_all_reminders_tool)

        logger.info("Registering health query tools...")

        # Create health data client
        health_client = HealthDataClient()

        # Create health query tool
        health_query_tool = HealthQueryTool(health_client=health_client)

        # Register the tool (so it gets user_id, time_tracker, etc.)
        tool_manager.register_tool(health_query_tool)

        logger.info("✅ Health query tools registered")

        view_meds_tool = ViewMedicationsTool()

        tool_manager.register_tool(view_meds_tool)

        add_medication_tool = AddMedicationTool()

        tool_manager.register_tool(add_medication_tool)

        confirm_dose_tool = ConfirmDoseTool()

        tool_manager.register_tool(confirm_dose_tool)

        skip_dose_tool = SkipDoseTool()

        tool_manager.register_tool(skip_dose_tool)

        query_schedule_tool = QueryScheduleTool()

        tool_manager.register_tool(query_schedule_tool)

        check_adherence_tool = CheckAdherenceTool()

        tool_manager.register_tool(check_adherence_tool)

        request_refill_tool = RequestRefillTool()

        tool_manager.register_tool(request_refill_tool)

        edit_medication_tool = EditMedicationTool()

        tool_manager.register_tool(edit_medication_tool)

        delete_medication_tool = DeleteMedicationTool()

        tool_manager.register_tool(delete_medication_tool)

        memory_tool = MemoryTool(memory_client=memory_client)

        tool_manager.register_tool(memory_tool)

        logger.info("✅ Registered medication tools")

        story_client = StoryClient()

        story_tool = StoryTool(story_client=story_client)

        tool_manager.register_tool(story_tool)

        logger.info(
            f"✅ Registered {tool_manager.get_tool_count()} tools: "
            f"{tool_manager.get_registered_tools()}"
        )
