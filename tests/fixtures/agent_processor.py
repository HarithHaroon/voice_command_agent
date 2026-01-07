"""
Agent processor - Handles calling orchestrator and specialist agents.
"""

import logging
from typing import Dict, Any, List, Optional
import openai
import os

from tests.fixtures.tool_converter import ToolConverter
from tests.fixtures.intent_analyzer import IntentAnalyzer
from tests.fixtures.tool_filter import ToolFilter
from tests.fixtures.specialist_factory import SpecialistFactory
from tests.fixtures.message_parser import MessageParser
from models.shared_state import SharedState

logger = logging.getLogger(__name__)


class AgentProcessor:
    """Processes messages through orchestrator and specialist agents"""

    def __init__(self, shared_state: SharedState, orchestrator):
        self.shared_state = shared_state

        self.orchestrator = orchestrator

        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize helper components
        self.intent_analyzer = IntentAnalyzer(self.client)

        self.message_parser = MessageParser()

    async def process_message(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Process message through full agent pipeline.

        Args:
            user_input: Current user message
            conversation_history: Previous turns in conversation

        Returns:
            Trajectory with all agent actions
        """
        if conversation_history is None:
            conversation_history = []

        # Call orchestrator
        orchestrator_result = await self._call_orchestrator(
            user_input=user_input,
            conversation_history=conversation_history,
        )

        # Check for handoff to specialist
        handoff_info = self.message_parser.extract_handoff(orchestrator_result)

        if handoff_info:
            # Call specialist
            specialist_result = await self._call_specialist(
                user_input=user_input,
                specialist_name=handoff_info["specialist"],
                handoff_reason=handoff_info["reason"],
                conversation_history=conversation_history,
            )

            return self._merge_results(orchestrator_result, specialist_result)
        else:
            # Orchestrator handled directly
            tools_called = orchestrator_result.get("tools_called", [])

            # Generate synthetic response showing what was done
            if tools_called:
                response_text = f"Completed: {', '.join(tools_called)}"
            else:
                response_text = orchestrator_result.get("response_text", "Done")

            return {
                "agent_path": ["Orchestrator"],
                "tools_called": tools_called,
                "tool_params": orchestrator_result.get("tool_params", {}),
                "response": response_text,  # ← Now returns "Completed: log_activity"
                "handoffs": [],
                "mode": "real",
            }

    async def _call_orchestrator(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Call orchestrator agent with conversation history"""
        if conversation_history is None:
            conversation_history = []

        logger.info("Calling orchestrator agent")

        # Step 1: Analyze intent
        intended_agent = await self.intent_analyzer.analyze_intent(
            user_input=user_input,
            conversation_history=conversation_history,
        )

        # Step 2: Get and filter tools
        tools = self.orchestrator.tools

        openai_tools = ToolConverter.convert_tools(tools)

        relevant_tools = ToolFilter.filter_tools(openai_tools, intended_agent)

        # Step 3: Build messages
        instructions = self.orchestrator.instructions

        messages = [
            {"role": "system", "content": instructions},
            *conversation_history,
            {"role": "user", "content": user_input},
        ]

        # Step 4: Determine tool choice strategy
        is_implicit_completion = any(
            phrase in user_input.lower()
            for phrase in ["i finished", "done with", "completed"]
        )

        tool_choice = (
            None if is_implicit_completion else ("required" if relevant_tools else None)
        )

        # Step 5: Call OpenAI
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=relevant_tools if relevant_tools else None,
            tool_choice=tool_choice,
            temperature=0.2,
        )

        message = response.choices[0].message

        return {
            "agent": "Orchestrator",
            "response_text": message.content or "",
            "tools_called": self.message_parser.extract_tool_calls(message),
            "tool_params": self.message_parser.extract_tool_params(message),
        }

    async def _call_specialist(
        self,
        user_input: str,
        specialist_name: str,
        handoff_reason: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Call specialist agent with conversation history"""
        if conversation_history is None:
            conversation_history = []

        logger.info(f"Calling specialist: {specialist_name}")

        # Get specialist instructions
        instructions = SpecialistFactory.get_specialist_instructions(
            specialist_name,
            self.shared_state.agent_prompts,
        )

        # Create specialist agent
        specialist = SpecialistFactory.create_specialist(
            specialist_name,
            self.shared_state,
            instructions,
        )

        if not specialist:
            logger.error(f"Failed to create specialist: {specialist_name}")
            return {
                "agent": specialist_name,
                "response_text": "",
                "tools_called": [],
                "tool_params": {},
            }

        # Get and convert tools
        tools = specialist.tools

        openai_tools = ToolConverter.convert_tools(tools)

        # Build messages
        messages = [
            {"role": "system", "content": instructions},
            *conversation_history,
            {"role": "user", "content": user_input},
        ]

        # Call OpenAI
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=openai_tools if openai_tools else None,
            tool_choice="required" if openai_tools else None,
            temperature=0.2,
        )

        message = response.choices[0].message

        return {
            "agent": specialist_name,
            "response_text": message.content or "",
            "tools_called": self.message_parser.extract_tool_calls(message),
            "tool_params": self.message_parser.extract_tool_params(message),
        }

    def _merge_results(
        self,
        orchestrator_result: Dict,
        specialist_result: Dict,
    ) -> Dict[str, Any]:
        """Merge orchestrator and specialist results"""
        specialist_name = specialist_result["agent"]

        # Generate synthetic confirmation
        tools_called = specialist_result["tools_called"]
        response_text = (
            f"Completed: {', '.join(tools_called)}"
            if tools_called
            else specialist_result.get("response_text", "Done")
        )

        return {
            "agent_path": ["Orchestrator", specialist_name, "Orchestrator"],
            "tools_called": specialist_result["tools_called"],
            "tool_params": specialist_result["tool_params"],
            "response": response_text,  # ← Use synthetic response
            "handoffs": [{"from": "Orchestrator", "to": specialist_name}],
            "mode": "real",
        }
