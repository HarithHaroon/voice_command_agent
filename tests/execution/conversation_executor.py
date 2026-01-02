"""
Conversation executor - Runs multi-turn conversation tests.
"""

import logging
import time
from typing import List

from tests.core.interfaces import (
    ConversationTest,
    ConversationResult,
    ConversationTurn,
    TestResult,
    TestCase,
    TestContext,
    TestStatus,
    ITester,
)
from tests.fixtures.agent_processor import AgentProcessor

logger = logging.getLogger(__name__)


class ConversationExecutor:
    """Executes multi-turn conversation tests"""

    def __init__(self, processor: AgentProcessor, testers: List[ITester]):
        self.processor = processor
        self.testers = testers

    async def execute_conversation(
        self, conversation: ConversationTest, context: TestContext
    ) -> ConversationResult:
        """
        Execute a multi-turn conversation test.

        Returns:
            ConversationResult with all turn results
        """
        start_time = time.time()
        conversation_history = []
        turn_results = []

        logger.info(f"Executing conversation: {conversation.name}")

        for i, turn in enumerate(conversation.turns, 1):
            logger.info(f"Turn {i}/{len(conversation.turns)}: {turn.input}")

            # Process turn through agent system
            turn_result = await self._execute_turn(
                turn=turn,
                conversation_history=conversation_history,
                context=context,
                turn_number=i,
            )

            turn_results.append(turn_result)

            # Update conversation history
            conversation_history.append({"role": "user", "content": turn.input})
            conversation_history.append(
                {
                    "role": "assistant",
                    "content": turn_result.details.get("response", ""),
                }
            )

        # Calculate overall results
        duration_ms = (time.time() - start_time) * 1000
        passed_turns = sum(1 for r in turn_results if r.passed)
        failed_turns = len(turn_results) - passed_turns
        overall_score = (passed_turns / len(turn_results) * 100) if turn_results else 0

        # Determine overall status
        if passed_turns == len(turn_results):
            status = TestStatus.PASS
        elif passed_turns > 0:
            status = TestStatus.WARNING
        else:
            status = TestStatus.FAIL

        return ConversationResult(
            test_id=conversation.id,
            test_name=conversation.name,
            status=status,
            total_turns=len(conversation.turns),
            passed_turns=passed_turns,
            failed_turns=failed_turns,
            turn_results=turn_results,
            overall_score=overall_score,
            duration_ms=duration_ms,
            details={
                "description": conversation.description,
                "metadata": conversation.metadata,
            },
        )

    async def _execute_turn(
        self,
        turn: ConversationTurn,
        conversation_history: List[dict],
        context: TestContext,
        turn_number: int,
    ) -> TestResult:
        """Execute a single turn in the conversation"""
        turn_start = time.time()

        try:
            # Process message with history
            agent_response = await self.processor.process_message(
                user_input=turn.input, conversation_history=conversation_history
            )

            # Store results in context for testers
            context.metadata["agent_path"] = agent_response.get("agent_path", [])
            context.metadata["tools_called"] = agent_response.get("tools_called", [])
            context.metadata["tool_params"] = agent_response.get("tool_params", {})
            context.metadata["handoffs"] = agent_response.get("handoffs", [])
            context.metadata["response_text"] = agent_response.get("response", "")
            context.metadata["mode"] = "real"

            # Create temporary TestCase for this turn
            test_case = TestCase(
                id=f"turn_{turn_number}",
                agent=turn.expected_agent or "unknown",
                input=turn.input,
                expected={
                    "tool": turn.expected_tool,
                    "params": turn.expected_params or {},
                },
                metadata=turn.metadata,
            )

            # Run testers
            tester_results = {}
            all_passed = True

            for tester in self.testers:
                result = await tester.test(test_case, context)
                tester_results[tester.name] = result

                if not result.get("passed", False) and not result.get("skipped", False):
                    all_passed = False

            # Calculate score
            passed_count = sum(
                1 for r in tester_results.values() if r.get("passed", False)
            )
            total_count = sum(
                1 for r in tester_results.values() if not r.get("skipped", False)
            )
            score = (passed_count / total_count * 100) if total_count > 0 else 0

            status = TestStatus.PASS if all_passed else TestStatus.FAIL
            duration_ms = (time.time() - turn_start) * 1000

            return TestResult(
                test_id=f"turn_{turn_number}",
                test_input=turn.input,
                status=status,
                score=score,
                details={
                    "turn_number": turn_number,
                    "agent_path": context.metadata["agent_path"],
                    "tools_called": context.metadata["tools_called"],
                    "tool_params": context.metadata["tool_params"],
                    "handoffs": context.metadata["handoffs"],
                    "response": context.metadata["response_text"],
                    "tester_results": tester_results,
                    "expected": {
                        "agent": turn.expected_agent,
                        "tool": turn.expected_tool,
                        "params": turn.expected_params,
                    },
                    "context_check": turn.context_check,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Turn {turn_number} failed: {e}", exc_info=True)
            duration_ms = (time.time() - turn_start) * 1000

            return TestResult(
                test_id=f"turn_{turn_number}",
                test_input=turn.input,
                status=TestStatus.FAIL,
                score=0.0,
                details={
                    "turn_number": turn_number,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                duration_ms=duration_ms,
            )
