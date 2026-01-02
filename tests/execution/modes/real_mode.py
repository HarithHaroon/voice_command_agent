"""
Real execution mode.
Actually processes messages through the multi-agent system with real LLM calls.
"""

import logging
import time
from typing import List

from tests.core.interfaces import (
    IExecutionMode,
    ITester,
    TestCase,
    TestResult,
    TestContext,
    TestStatus,
)

logger = logging.getLogger(__name__)


class RealMode(IExecutionMode):
    """Real execution mode - actual LLM calls with multi-agent system"""

    def __init__(self, adapter):
        """Initialize real mode with adapter"""
        self.adapter = adapter

    async def execute_test(
        self, test_case: TestCase, context: TestContext, testers: List[ITester]
    ) -> TestResult:
        """
        Execute test in real mode.
        Actually processes message through the agent system.
        """
        start_time = time.time()

        try:
            # Process message through real agent system
            logger.debug(f"Processing message in real mode: '{test_case.input}'")

            agent_response = await self.adapter.process_message(
                user_input=test_case.input, mode="real"
            )

            # Store results in context
            context.metadata["agent_path"] = agent_response.get("agent_path", [])
            context.metadata["tools_called"] = agent_response.get("tools_called", [])
            context.metadata["tool_params"] = agent_response.get("tool_params", {})
            context.metadata["handoffs"] = agent_response.get("handoffs", [])
            context.metadata["response_text"] = agent_response.get("response", "")
            context.metadata["mode"] = "real"

            # Run all testers
            tester_results = {}
            all_passed = True

            for tester in testers:
                logger.debug(f"Running tester: {tester.name}")
                result = await tester.test(test_case, context)
                tester_results[tester.name] = result

                if not result.get("passed", False) and not result.get("skipped", False):
                    all_passed = False

            # Calculate overall score
            passed_count = sum(
                1 for r in tester_results.values() if r.get("passed", False)
            )
            total_count = sum(
                1 for r in tester_results.values() if not r.get("skipped", False)
            )
            score = (passed_count / total_count * 100) if total_count > 0 else 0

            # Determine status
            status = TestStatus.PASS if all_passed else TestStatus.FAIL

            duration_ms = (time.time() - start_time) * 1000

            return TestResult(
                test_id=test_case.id,
                test_input=test_case.input,
                status=status,
                score=score,
                details={
                    "agent": test_case.agent,
                    "mode": "real",
                    "agent_path": context.metadata["agent_path"],
                    "tools_called": context.metadata["tools_called"],
                    "tool_params": context.metadata["tool_params"],
                    "handoffs": context.metadata["handoffs"],
                    "response_text": context.metadata["response_text"],
                    "tester_results": tester_results,
                    "expected": test_case.expected,
                    "metadata": test_case.metadata,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Real execution failed for test '{test_case.id}': {e}")
            duration_ms = (time.time() - start_time) * 1000

            return TestResult(
                test_id=test_case.id,
                test_input=test_case.input,
                status=TestStatus.FAIL,
                score=0.0,
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration_ms,
            )
