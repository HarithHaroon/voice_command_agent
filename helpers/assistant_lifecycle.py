"""
Assistant Lifecycle - Handles setup and teardown for the multi-agent system.
Refactored to work with SharedState.
"""

import logging
from typing import TYPE_CHECKING
from livekit.agents import get_job_context

if TYPE_CHECKING:
    from models.shared_state import SharedState
    from helpers.assistant_data_handler import AssistantDataHandler

logger = logging.getLogger(__name__)


class AssistantLifecycle:
    """Manages lifecycle (initialization and cleanup) for the multi-agent system."""

    def __init__(
        self, shared_state: "SharedState", data_handler: "AssistantDataHandler"
    ):
        """
        Initialize lifecycle manager.

        Args:
            shared_state: SharedState instance
            data_handler: AssistantDataHandler instance
        """
        self.shared_state = shared_state

        self.data_handler = data_handler

        self.time_monitor = None

        logger.info("AssistantLifecycle initialized")

    async def setup(self):
        """
        Setup multi-agent system when entering a room.
        Called once at session start.
        """
        logger.info("Multi-agent system entering the room")

        # Set agent reference for all tools
        # Note: We'll pass the current agent dynamically, but tools need initial setup
        # For now, tools don't need agent reference until they're called
        # (Navigation tool gets it when accessed)

        # Set user_id for all tools that need it
        if self.shared_state.user_id:
            self.shared_state.tool_manager.set_user_id_for_all_tools(
                self.shared_state.user_id
            )

        # Set time tracker for all tools that need it
        self.shared_state.tool_manager.set_time_tracker_for_all_tools(
            self.shared_state.time_tracker
        )

        # Start time monitor for backlog reminders
        if self.shared_state.user_id:
            await self._setup_time_monitor()

        # Set up data handler
        await self._setup_data_handler()

    async def _setup_time_monitor(self):
        """Initialize and start the time monitor for backlog reminders."""
        try:
            from backlog.time_monitor import TimeMonitor

            self.time_monitor = TimeMonitor(
                user_id=self.shared_state.user_id,
                time_tracker=self.shared_state.time_tracker,
                backlog_manager=self.shared_state.backlog_manager,
            )

            # Get session from tool_manager
            session = getattr(self.shared_state.tool_manager, "agent_session", None)

            if session:
                self.time_monitor.set_session(session)
                await self.time_monitor.start()
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
                ctx.room.on("data_received", self.data_handler.handle_data)

                logger.info("Data handler registered successfully")
            else:
                logger.error("No job context room available")

        except Exception as e:
            logger.error(f"Data handler setup failed: {e}")

    async def teardown(self):
        """
        Cleanup multi-agent system when leaving a room.
        Called once at session end.
        """
        logger.info("Multi-agent system leaving the room - cleaning up")

        # Stop time monitor
        if self.time_monitor:
            await self.time_monitor.stop()

            logger.info("TimeMonitor stopped")

        # Clean up navigation state
        self.shared_state.navigation_state.clear()
