"""
Extensible AI Assistant using Tool Manager - LiveKit Cloud Compatible.
"""

from datetime import datetime
import json
import logging
import asyncio
from livekit.agents import Agent, get_job_context
from tools.tool_manager import ToolManager
from models.navigation_state import NavigationState
from clients.firebase_client import FirebaseClient
from intent_detection.intent_detector import IntentDetector
from prompt_management.prompt_module_manager import PromptModuleManager
from helpers.client_time_tracker import ClientTimeTracker
from backlog.backlog_manager import BacklogManager
from helpers.tool_registry import ToolRegistry
from helpers.assistant_data_handler import AssistantDataHandler
from helpers.assistant_lifecycle import AssistantLifecycle

logger = logging.getLogger(__name__)


class Assistant(Agent):
    """AI Assistant with extensible tool management."""

    def __init__(self, user_id: str = None, use_llm_intent: bool = True) -> None:
        """
        Initialize the AI Assistant.

        Args:
            user_id: User identifier
            use_llm_intent: Use LLM-based intent detection (vs regex)
        """
        # Core state
        self.user_id = user_id

        self.use_llm_intent = use_llm_intent

        self.conversation_history = []

        # State management
        self.navigation_state = NavigationState()

        self.time_tracker = ClientTimeTracker()

        self.time_monitor = None

        # External services
        self.firebase_client = FirebaseClient()

        self.backlog_manager = BacklogManager()

        # Emotion/voice quality tracking
        self.pending_check_in = None

        self.waiting_for_check_in_response = False

        self.check_in_question = None

        logger.info(f"Assistant initialized with user_id: {user_id}")

        # Initialize tool manager
        self.tool_manager = ToolManager()

        # Register all tools using ToolRegistry
        ToolRegistry.register_all_tools(
            tool_manager=self.tool_manager,
            navigation_state=self.navigation_state,
            firebase_client=self.firebase_client,
            backlog_manager=self.backlog_manager,
            assistant=self,
        )

        # Initialize modular prompt system
        self.module_manager = PromptModuleManager()

        # Initialize intent detection (LLM or regex)
        if use_llm_intent:
            from intent_detection.llm_intent_detector import LLMIntentDetector
            from intent_detection.module_definitions import get_module_definitions

            self.intent_detector = LLMIntentDetector(
                available_modules=get_module_definitions()
            )
            logger.info("Using LLM-based intent detection")

        else:
            self.intent_detector = IntentDetector()
            logger.info("Using regex-based intent detection")

        self.current_modules = ["navigation", "memory_recall"]

        # Assemble initial instructions from base + default modules
        base_instructions = self.module_manager.assemble_instructions(
            modules=self.current_modules,
            current_time=datetime.now().strftime("%A, %B %d, %Y at %I:%M %p"),
        )

        # Initialize helper classes
        self.data_handler = AssistantDataHandler(self)
        self.lifecycle = AssistantLifecycle(self)

        # Initialize agent with dynamically assembled instructions
        super().__init__(
            instructions=base_instructions,
            tools=(self.tool_manager.get_all_tool_functions()),
        )

        logger.info(f"Assistant ready | Active modules: {self.current_modules}")

    async def save_message_to_firebase(self, role: str, content: str):
        """
        Save message to Firebase.

        Args:
            role: Message role (USER or ASSISTANT)
            content: Message content
        """
        if self.user_id and content:
            await asyncio.to_thread(
                self.firebase_client.add_message,
                self.user_id,
                role.upper(),
                content,
            )

    async def update_emotion_event_with_interaction(
        self, timestamp: str, agent_question: str, user_response: str
    ):
        """
        Update emotion event with Q&A interaction.
        Delegates to data handler.

        Args:
            timestamp: Event timestamp
            agent_question: Question asked by agent
            user_response: User's response
        """
        await self.data_handler.update_emotion_event_with_interaction(
            timestamp, agent_question, user_response
        )

    async def on_enter(self):
        """Called when the agent enters a room."""
        await self.lifecycle.setup()

    async def on_leave(self):
        """Called when the agent leaves the room."""
        await self.lifecycle.teardown()
