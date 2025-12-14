"""
Assistant Lifecycle - Handles setup and teardown for the assistant.
"""

import logging
from typing import TYPE_CHECKING
from livekit.agents import get_job_context

if TYPE_CHECKING:
    from assistant import Assistant

logger = logging.getLogger(__name__)


class AssistantLifecycle:
    """Manages assistant lifecycle (initialization and cleanup)."""

    def __init__(self, assistant: "Assistant"):
        """
        Initialize lifecycle manager.

        Args:
            assistant: Assistant instance to manage
        """
        self.assistant = assistant

        logger.info("AssistantLifecycle initialized")

    async def setup(self):
        """
        Setup assistant when entering a room.
        Called from assistant.on_enter()
        """
        logger.info("Assistant entered the room")

        # Set agent reference for all tools
        self.assistant.tool_manager.set_agent_for_all_tools(self.assistant)

        # Set user_id for all tools that need it
        if self.assistant.user_id:
            self.assistant.tool_manager.set_user_id_for_all_tools(
                self.assistant.user_id
            )

        # Set time tracker for all tools that need it
        self.assistant.tool_manager.set_time_tracker_for_all_tools(
            self.assistant.time_tracker
        )

        # Start time monitor for backlog reminders
        if self.assistant.user_id:
            await self._setup_time_monitor()

        # Set up data handler
        await self._setup_data_handler()

    async def _setup_time_monitor(self):
        """Initialize and start the time monitor for backlog reminders."""
        try:
            from backlog.time_monitor import TimeMonitor

            self.assistant.time_monitor = TimeMonitor(
                user_id=self.assistant.user_id,
                time_tracker=self.assistant.time_tracker,
                backlog_manager=self.assistant.backlog_manager,
            )

            # Get session from tool_manager
            session = getattr(self.assistant.tool_manager, "agent_session", None)

            if session:
                self.assistant.time_monitor.set_session(session)

                await self.assistant.time_monitor.start()

                logger.info("✅ TimeMonitor started")

            else:
                logger.warning("Session not available, TimeMonitor not started")

        except Exception as e:
            logger.error(f"Error setting up time monitor: {e}", exc_info=True)

    async def _setup_data_handler(self):
        """Setup data handler using job context."""
        try:
            ctx = get_job_context()

            if ctx and ctx.room:
                # Use the data handler's handle_data method
                ctx.room.on("data_received", self.assistant.data_handler.handle_data)

                logger.info("Data handler registered successfully")
            else:
                logger.error("No job context room available")

        except Exception as e:
            logger.error(f"Data handler setup failed: {e}")

    async def teardown(self):
        """
        Cleanup assistant when leaving a room.
        Called from assistant.on_leave()
        """
        logger.info("Assistant leaving the room - cleaning up")

        # Stop time monitor
        if self.assistant.time_monitor:
            await self.assistant.time_monitor.stop()

            logger.info("TimeMonitor stopped")

        # Clean up navigation state
        self.assistant.navigation_state.clear()
