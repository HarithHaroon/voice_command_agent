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
        """Initialize mock mode with adapter for intent detection"""
        self.adapter = adapter

    async def execute_test(
        self, test_case: TestCase, context: TestContext, testers: List[ITester]
    ) -> TestResult:
        """
        Execute test in mock mode.
        Uses expected values from test_case instead of calling LLM.
        """
        start_time = time.time()

        try:
            # Step 1: Detect intent using the adapter
            intent_result = await self.adapter.detect_intent(test_case.input)

            # Step 2: Simulate tool selection using expected values
            expected_tool = test_case.expected.get("tool")
            expected_params = test_case.expected.get("params", {})

            # Store in context for testers to access
            context.metadata["intent_result"] = intent_result
            context.metadata["tool_called"] = expected_tool
            context.metadata["tool_params"] = expected_params
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
            if all_passed:
                status = TestStatus.PASS
            elif any(r.get("error") for r in tester_results.values()):
                status = TestStatus.FAIL
            else:
                status = TestStatus.FAIL

            duration_ms = (time.time() - start_time) * 1000

            return TestResult(
                test_id=test_case.id,
                test_input=test_case.input,
                status=status,
                score=score,
                details={
                    "category": test_case.category,
                    "mode": "mock",
                    "intent_result": intent_result,
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
