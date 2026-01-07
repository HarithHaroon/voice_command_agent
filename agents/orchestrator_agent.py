"""
Orchestrator Agent - Main router for the multi-agent system.
"""

import logging
from typing import List
from livekit.agents import Agent, function_tool

from models.shared_state import SharedState

logger = logging.getLogger(__name__)


class OrchestratorAgent(Agent):
    """
    Orchestrator agent that routes requests to specialist agents.

    Responsibilities:
    - Handle simple queries directly (navigation, video calls, recall history)
    - Route complex queries to specialist agents via handoff tools
    - Maintain conversation flow
    """

    AGENT_NAME = "Orchestrator"

    def __init__(self, shared_state: SharedState):
        """
        Initialize orchestrator agent.

        Args:
            shared_state: Shared state from session.userdata
        """
        self.shared_state = shared_state

        # Get tools
        tools = self._get_tools()

        # Build personalized instructions with user's name
        user_name = self.shared_state.user_name

        # 🚨 CRITICAL RULE AT THE VERY TOP
        personalized_instructions = f"""🚨 CRITICAL FIRST RULE: 

            If user input contains "story", "stories", "tale", or "tales":
            - IMMEDIATELY call handoff_to_story_agent(reason="story request")
            - Do NOT call list_available_screens
            - Do NOT call any other tool
            - JUST handoff to story agent

            Examples:
            - "Show me all my stories" → handoff_to_story_agent("view collection")
            - "How many stories have I recorded?" → handoff_to_story_agent("get count")

            User's name: {user_name}

            {self.shared_state.agent_prompts.orchestrator}
        """

        # Initialize Agent
        super().__init__(instructions=personalized_instructions, tools=tools)

        # Update current agent
        self.shared_state.current_agent = self.AGENT_NAME

        logger.info(
            f"{self.AGENT_NAME} initialized with {len(tools)} tools for user: {user_name}"
        )

    def _get_tools(self) -> List:
        """Get all tools for orchestrator."""
        tools = []

        # Direct action tools (orchestrator handles these)
        tool_names = [
            "navigation",
            "start_video_call",
            "recall_history",
            "memory",
        ]

        for name in tool_names:
            tool = self.shared_state.tool_manager.get_tool(name)

            if tool:
                tools.extend(tool.get_tool_functions())
            else:
                logger.warning(f"Tool '{name}' not found")

        # DON'T manually add handoff tools - they're @function_tool decorated
        # so LiveKit will discover them automatically from the class

        logger.info(
            f"Orchestrator loaded {len(tools)} external tools (handoffs auto-discovered)"
        )

        return tools

    # Handoff tools - LLM calls these to route to specialists
    @function_tool
    async def handoff_to_backlog_agent(self, reason: str = "") -> tuple:
        """
        Transfer to backlog specialist for viewing/managing existing reminders.
        Use for: checking schedule, completing reminders, deleting reminders.
        """
        from agents.backlog_agent import BacklogAgent

        self.shared_state.is_transitioning = True

        agent = BacklogAgent(
            self.shared_state, instructions=self.shared_state.agent_prompts.backlog
        )

        self.shared_state.is_transitioning = False

        logger.info(f"🔀 Orchestrator → BacklogAgent: {reason}")

        return (agent, "Routing to reminder management specialist")

    @function_tool
    async def handoff_to_books_agent(self, reason: str = "") -> tuple:
        """
        Transfer to books specialist.
        Use for: reading books, book content questions.
        """
        from agents.books_agent import BooksAgent

        self.shared_state.is_transitioning = True

        agent = BooksAgent(
            self.shared_state, instructions=self.shared_state.agent_prompts.books
        )

        self.shared_state.is_transitioning = False

        logger.info(f"🔀 Orchestrator → BooksAgent: {reason}")

        return (agent, "Routing to reading specialist")

    @function_tool
    async def handoff_to_health_agent(self, reason: str = "") -> tuple:
        """
        Transfer to health data specialist.

        Use for ANY question about:
        - Health status, wellness, or how they're doing/feeling
        - Health metrics, vitals, measurements (heart rate, blood pressure, steps, sleep, etc.)
        - Health summaries, updates, or reports
        - Medical queries or health concerns

        Examples of health queries:
        - "How am I doing today?"
        - "How's my health?"
        - "How am I feeling?"
        - "What's my blood pressure?"
        - "Give me a health update"

        ALWAYS handoff questions about health/wellness/feeling, even if vaguely phrased.
        """
        from agents.health_agent import HealthAgent

        self.shared_state.is_transitioning = True

        agent = HealthAgent(
            self.shared_state, instructions=self.shared_state.agent_prompts.health
        )

        self.shared_state.is_transitioning = False

        logger.info(f"🔀 Orchestrator → HealthAgent: {reason}")

        return (agent, "Routing to health data specialist")

    @function_tool
    async def handoff_to_settings_agent(self, reason: str = "") -> tuple:
        """
        Transfer to settings specialist.
        Use for: device configuration, fall detection, location tracking.
        """
        from agents.settings_agent import SettingsAgent

        self.shared_state.is_transitioning = True

        agent = SettingsAgent(
            self.shared_state, instructions=self.shared_state.agent_prompts.settings
        )

        self.shared_state.is_transitioning = False

        logger.info(f"🔀 Orchestrator → SettingsAgent: {reason}")

        return (agent, "Routing to settings specialist")

    @function_tool
    async def handoff_to_image_agent(self, reason: str = "") -> tuple:
        """
        Transfer to image specialist.
        Use for: photo searches, finding images.
        """
        from agents.image_agent import ImageAgent

        self.shared_state.is_transitioning = True

        agent = ImageAgent(
            self.shared_state, instructions=self.shared_state.agent_prompts.image
        )

        self.shared_state.is_transitioning = False

        logger.info(f"🔀 Orchestrator → ImageAgent: {reason}")

        return (agent, "Routing to image specialist")

    @function_tool
    async def handoff_to_medication_agent(self, reason: str = "") -> tuple:
        """
        Transfer to medication management specialist.

        Use for:
        - Managing medications (add, view, edit, delete)
        - Tracking doses (confirm taken, skip, query schedule)
        - Checking adherence and refills
        - Drug interaction warnings

        Examples:
        - "Add my blood pressure medication"
        - "What medications am I taking?"
        - "I took my pills"
        - "How am I doing with my medications?"
        - "I need to refill my Lisinopril"
        """
        from agents.medication_agent import MedicationAgent

        self.shared_state.is_transitioning = True

        agent = MedicationAgent(
            self.shared_state, instructions=self.shared_state.agent_prompts.medication
        )

        self.shared_state.is_transitioning = False

        logger.info(f"🔀 Orchestrator → MedicationAgent: {reason}")

        # Return message that preserves context
        return (agent, f"Continuing with medication request: {reason}")

    @function_tool
    async def handoff_to_story_agent(self, reason: str = "") -> tuple:
        """
        Transfer to story preservation specialist.

        Use for:
        - Recording life stories and memories
        - Finding and retrieving stories
        - Browsing story collections
        - Getting story summaries

        Examples:
        - "I want to tell a story about my childhood"
        - "Show me all my stories"
        - "How many stories have I recorded?"
        - "Tell me about my wedding day"
        - "Find stories about my family"
        """
        from agents.story_agent import StoryAgent

        self.shared_state.is_transitioning = True

        agent = StoryAgent(
            self.shared_state, instructions=self.shared_state.agent_prompts.story
        )

        self.shared_state.is_transitioning = False

        logger.info(f"🔀 Orchestrator → StoryAgent: {reason}")

        # Return message that preserves context
        return (agent, f"Continuing with story request: {reason}")
