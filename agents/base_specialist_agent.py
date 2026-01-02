"""
Base agent class for specialist agents in the multi-agent system.
"""

import logging
from typing import List
from livekit.plugins import openai
from livekit.agents import Agent, function_tool

from models.shared_state import SharedState

logger = logging.getLogger(__name__)


class BaseSpecialistAgent(Agent):
    """
    Base class for all specialist agents.

    Provides:
    - Access to shared state via self.shared_state
    - Pattern for defining agent-specific tools
    - Handoff tool back to orchestrator (LLM-callable)
    """

    # Subclasses should override these
    AGENT_NAME = "BaseSpecialist"

    INSTRUCTIONS = ""

    BASE_INSTRUCTIONS = """You are a specialist agent focused on a specific domain.

        **CRITICAL: CONTINUE THE CONVERSATION - DO NOT GREET OR RESTART!**

        **The user already stated their request. Read the conversation history and continue from there.**

        **CONTEXT AWARENESS:**
        - Pay close attention to the conversation history
        - The user's last message contains their request - act on it immediately
        - Resolve pronouns and implicit references using recent context:
        - "the first one" → refers to first item mentioned previously
        - "keep going" → continue the last action
        - "it" → refers to the most recent subject discussed
        - Maintain continuity with what was just discussed

        **Then follow this pattern for EVERY interaction:**

        1. **READ conversation history** - see what user already said
        2. **If you have enough info** → Use tools immediately
        3. **If missing details** → Ask for ONLY the missing information
        4. **After completing task** → IMMEDIATELY call handoff_to_orchestrator(summary="brief description")

        **You MUST handoff after EVERY response, regardless of outcome:**
        - ✓ Tool succeeds → Answer → handoff_to_orchestrator(summary="what you did")
        - ✓ Tool fails → Explain issue → handoff_to_orchestrator(summary="error occurred")  
        - ✓ No data → Inform user → handoff_to_orchestrator(summary="no data available")

        **DO NOT:**
        - Greet the user (conversation already started)
        - Ask "How can I help?" (they already told you)
        - Wait for user confirmation
        - Continue conversation beyond answering their question
        - Ask follow-up questions unless absolutely necessary

        **Pattern:**
        Read history → Act on request → handoff_to_orchestrator(summary="...") → Done

        This ensures users can seamlessly move between specialists without getting stuck or repeating themselves.
    """

    def __init__(self, shared_state: SharedState, instructions: str):
        """
        Initialize specialist agent.

        Args:
            shared_state: Shared state from session.userdata
            instructions: Pre-loaded instructions from orchestrator
        """
        self.shared_state = shared_state

        # Get tools for this specialist
        tools = self._get_tools()

        # Build personalized instructions with user's name
        user_name = self.shared_state.user_name

        personalized_instructions = f"""User's name: {user_name}

            {self.BASE_INSTRUCTIONS}

            {instructions}
        """

        # Initialize Agent
        super().__init__(
            instructions=personalized_instructions,
            tools=tools,
        )

        # Update current agent in shared state
        self.shared_state.current_agent = self.AGENT_NAME

        logger.info(
            f"{self.AGENT_NAME} initialized with {len(tools)} tools for user: {user_name}"
        )

    def _send_initial_greeting(self):
        """
        Send initial greeting when specialist takes over.
        Override in subclasses for custom greetings.
        """
        user_name = self._get_user_name()

        if user_name:
            greeting = f"Hi {user_name}, I'm here to help with {self._get_specialty_description()}."

        else:
            greeting = f"I'm here to help with {self._get_specialty_description()}."

        # This will be the agent's first message
        # LiveKit will speak this automatically
        logger.info(f"🎯 {self.AGENT_NAME} greeting: {greeting}")

    def _get_user_name(self) -> str:
        """
        Get user's name from shared state.
        Override or extend as needed.
        """
        # You'll need to add user_name to SharedState
        # For now, return empty string as fallback
        return getattr(self.shared_state, "user_name", "")

    def _get_specialty_description(self) -> str:
        """
        Get description of this specialist's domain.
        Override in subclasses.
        """
        return "your request"

    def _get_tools(self) -> List:
        """
        Get tool functions for this agent.
        Subclasses should override to provide their specific tools.

        Returns:
            List of function_tool decorated methods
        """
        # Base implementation: all agents get recall_history
        tools = []

        # Get recall_history tool
        recall_tool = self.shared_state.tool_manager.get_tool("recall_history")

        if recall_tool:
            tools.extend(recall_tool.get_tool_functions())

        # DON'T add handoff_to_orchestrator here - it's a @function_tool decorated method
        # LiveKit will discover it automatically from the class

        return tools

    def _get_tools_by_names(self, tool_names: List[str]) -> List:
        """
        Get multiple tools by name and return their functions.

        Args:
            tool_names: List of tool names

        Returns:
            List of tool functions
        """
        tools = []

        for name in tool_names:
            tool = self.shared_state.tool_manager.get_tool(name)

            if tool:
                tools.extend(tool.get_tool_functions())

            else:
                logger.warning(f"{self.AGENT_NAME}: Tool '{name}' not found")

        return tools

    @function_tool
    async def handoff_to_orchestrator(self, summary: str = "") -> tuple:
        """
        Return control to the orchestrator agent.
        Call this when you have completed your task.

        Args:
            summary: Optional summary of what was accomplished

        Returns:
            Tuple of (new_agent, result_message)
        """
        # Mark transition start (prevents emotion check-ins during handoff)
        self.shared_state.is_transitioning = True

        # Reuse existing orchestrator instead of creating new one
        if self.shared_state.orchestrator_agent is None:
            # Import here to avoid circular dependency
            from agents.orchestrator_agent import OrchestratorAgent

            self.shared_state.orchestrator_agent = OrchestratorAgent(self.shared_state)

            logger.info("Created new OrchestratorAgent instance")

        orchestrator = self.shared_state.orchestrator_agent

        # Build result message
        if summary:
            result_message = f"{self.AGENT_NAME} completed: {summary}"

        else:
            result_message = f"{self.AGENT_NAME} task completed. How else can I help?"

        logger.info(f"🔄 {self.AGENT_NAME} → Orchestrator (reused): {result_message}")

        # Mark transition complete
        self.shared_state.is_transitioning = False

        # Return tuple: (agent, message)
        return (orchestrator, result_message)
