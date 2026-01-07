"""
Agent adapter for multi-agent system testing.
Connects the test framework to the LiveKit multi-agent voice assistant.
"""

import logging
from typing import Dict, Any, Optional, List

from tests.core.exceptions import AdapterError
from tests.fixtures.agent_processor import AgentProcessor

from models.shared_state import SharedState
from agents.orchestrator_agent import OrchestratorAgent
from models.navigation_state import NavigationState
from helpers.client_time_tracker import ClientTimeTracker
from tools.tool_manager import ToolManager
from clients.firebase_client import FirebaseClient
from backlog.backlog_manager import BacklogManager
from clients.memory_client import MemoryClient

logger = logging.getLogger(__name__)


class MultiAgentAdapter:
    """Adapter for multi-agent voice assistant - text-only testing"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        self.shared_state: Optional[SharedState] = None

        self.orchestrator: Optional[OrchestratorAgent] = None

        self.processor: Optional[AgentProcessor] = None

        self._initialized = False

    async def initialize(self, user_id: str = "test_user_123") -> None:
        """Initialize the multi-agent system for testing"""
        try:
            logger.info(f"Initializing MultiAgentAdapter for user: {user_id}")

            # Create shared state components
            navigation_state = NavigationState()

            time_tracker = ClientTimeTracker()

            tool_manager = ToolManager()

            # Initialize clients
            firebase_client = FirebaseClient()

            backlog_manager = BacklogManager()

            memory_client = MemoryClient()

            # Use mock health client for testing (returns test data)
            from tests.fixtures.mock_health_data_client import MockHealthDataClient

            health_client = MockHealthDataClient(user_id=user_id)

            logger.info("✅ Using MockHealthDataClient with test data")

            # Create shared state
            self.shared_state = SharedState(
                user_id=user_id,
                user_name="Test User",
                navigation_state=navigation_state,
                time_tracker=time_tracker,
                tool_manager=tool_manager,
                firebase_client=firebase_client,
                backlog_manager=backlog_manager,
                health_data_client=health_client,
            )

            # Register all tools
            from helpers.tool_registry import ToolRegistry

            ToolRegistry.register_all_tools(
                tool_manager=tool_manager,
                navigation_state=navigation_state,
                firebase_client=firebase_client,
                backlog_manager=backlog_manager,
                memory_client=memory_client,
            )

            logger.info("✅ All tools registered")

            # Initialize time tracker
            from datetime import datetime

            time_tracker.initialize(
                datetime.now().astimezone().tzinfo.tzname(None) or "UTC"
            )

            # Create orchestrator
            self.orchestrator = OrchestratorAgent(self.shared_state)

            # Create processor
            self.processor = AgentProcessor(self.shared_state, self.orchestrator)

            self._initialized = True

            logger.info("MultiAgentAdapter initialized successfully")

        except Exception as e:
            raise AdapterError(f"Failed to initialize adapter: {e}")

    def _ensure_initialized(self):
        """Check if adapter has been initialized"""
        if not self._initialized:
            raise AdapterError("Adapter not initialized. Call initialize() first.")

    async def process_message(
        self, user_input: str, mode: str = "mock"
    ) -> Dict[str, Any]:
        """
        Process user message through the multi-agent system.

        Args:
            user_input: Text input from user
            mode: "mock" or "real"

        Returns:
            {
                "agent_path": ["Orchestrator", "HealthAgent", "Orchestrator"],
                "tools_called": ["get_health_summary"],
                "tool_params": {...},
                "response": "agent response text",
                "handoffs": [{"from": "Orchestrator", "to": "HealthAgent"}],
                "mode": "mock" or "real"
            }
        """
        self._ensure_initialized()

        try:
            if mode == "mock":
                return await self._process_mock(user_input)
            elif mode == "real":
                return await self._process_real(user_input)
            else:
                raise AdapterError(f"Unknown mode: {mode}")

        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            raise AdapterError(f"Process message error: {e}")

    async def _process_mock(self, user_input: str) -> Dict[str, Any]:
        """
        Mock mode: Returns expected values without calling LLM.
        Used for fast, free testing.
        """
        # Mock mode handled by mock_mode.py execution mode
        return {
            "agent_path": None,
            "tools_called": None,
            "tool_params": None,
            "response": None,
            "handoffs": None,
            "mode": "mock",
        }

    async def _process_real(self, user_input: str) -> Dict[str, Any]:
        """
        Real mode: Actually processes through multi-agent system.
        Delegates to AgentProcessor for full pipeline.
        """
        try:
            result = await self.processor.process_message(user_input)

            return result

        except Exception as e:
            logger.error(f"Real mode processing failed: {e}", exc_info=True)

            raise AdapterError(f"Real processing error: {e}")

    def get_current_agent(self) -> str:
        """Get name of currently active agent"""
        self._ensure_initialized()

        return self.shared_state.current_agent or "Orchestrator"

    def get_available_agents(self) -> List[str]:
        """Get list of available agent names"""
        return [
            "Orchestrator",
            "HealthAgent",
            "BacklogAgent",
            "BooksAgent",
            "SettingsAgent",
            "ImageAgent",
            "MedicationAgent",
            "StoryAgent",
        ]

    def reset(self) -> None:
        """Reset adapter state between tests"""
        if self.shared_state:
            self.shared_state.current_agent = None

            self.shared_state.is_transitioning = False

            self.shared_state.conversation_history = []
