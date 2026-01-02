"""
Mock execution mode.
Fast execution without actual LLM calls - uses expected values from test cases.
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


class MockMode(IExecutionMode):
    """Mock execution mode - no LLM calls, uses test expectations"""

    def __init__(self, adapter):
        """Initialize mock mode with adapter"""
        self.adapter = adapter

    async def execute_test(
        self, test_case: TestCase, context: TestContext, testers: List[ITester]
    ) -> TestResult:
        """
        Execute test in mock mode.
        Uses expected values from test_case instead of calling agent.
        """
        start_time = time.time()

        try:
            # Mock mode: Use expected values directly
            expected_tool = test_case.expected.get("tool")
            expected_params = test_case.expected.get("params", {})
            expected_agent = test_case.agent

            # Store in context for testers to access
            # For orchestrator tasks, path is just ["Orchestrator"]
            # For specialist tasks, path is ["Orchestrator", "{Agent}Agent", "Orchestrator"]
            if expected_agent == "orchestrator":
                context.metadata["agent_path"] = ["Orchestrator"]
            else:
                expected_agent_name = f"{expected_agent.title()}Agent"
                context.metadata["agent_path"] = [
                    "Orchestrator",
                    expected_agent_name,
                    "Orchestrator",
                ]

            context.metadata["tools_called"] = [expected_tool] if expected_tool else []

            context.metadata["tool_params"] = expected_params

            context.metadata["handoffs"] = (
                [{"from": "Orchestrator", "to": f"{expected_agent.title()}Agent"}]
                if expected_agent != "orchestrator"
                else []
            )

            context.metadata["mode"] = "mock"

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
                    "mode": "mock",
                    "agent_path": context.metadata["agent_path"],
                    "tools_called": context.metadata["tools_called"],
                    "tester_results": tester_results,
                    "expected": test_case.expected,
                    "metadata": test_case.metadata,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Mock execution failed for test '{test_case.id}': {e}")
            duration_ms = (time.time() - start_time) * 1000

            return TestResult(
                test_id=test_case.id,
                test_input=test_case.input,
                status=TestStatus.FAIL,
                score=0.0,
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration_ms,
            )
