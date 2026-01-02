"""
Shared state for multi-agent system.
Stored in session.userdata and accessible by all agents.
"""

from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional
import logging


from models.navigation_state import NavigationState
from helpers.client_time_tracker import ClientTimeTracker
from tools.tool_manager import ToolManager
from clients.firebase_client import FirebaseClient
from backlog.backlog_manager import BacklogManager
from clients.health_data_client import HealthDataClient
from models.agent_prompts import AgentPrompts

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.orchestrator_agent import OrchestratorAgent

logger = logging.getLogger(__name__)


@dataclass
class SharedState:
    """
    Shared state accessible by all agents via session.userdata.

    This contains state that needs to persist across agent handoffs.
    """

    # User identification
    user_id: str

    user_name: str

    # Navigation state (from Flutter client)
    navigation_state: NavigationState

    # Client time tracking
    time_tracker: ClientTimeTracker

    # Tool management (shared across agents)
    tool_manager: ToolManager

    # External service clients
    firebase_client: FirebaseClient

    backlog_manager: BacklogManager

    health_data_client: HealthDataClient

    # Conversation context (last 10 messages for intent detection)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    # Current active agent name (for debugging/logging)
    current_agent: Optional[str] = None

    orchestrator_agent: Optional["OrchestratorAgent"] = None

    is_transitioning: bool = False  # Track agent transitions

    agent_prompts: AgentPrompts = field(default_factory=AgentPrompts)

    session: Optional[Any] = None

    def add_to_history(self, role: str, content: str) -> None:
        """
        Add message to conversation history.
        Maintains only last 10 messages for context.

        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        self.conversation_history.append({"role": role, "content": content})

        # Keep only last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

        logger.debug(f"Added to history: {role} - {content[:50]}...")

    def get_recent_context(self, num_messages: int = 5) -> List[Dict[str, str]]:
        """
        Get recent conversation context.

        Args:
            num_messages: Number of recent messages to return

        Returns:
            List of recent messages
        """
        return self.conversation_history[-num_messages:]
