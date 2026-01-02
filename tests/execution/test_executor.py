"""
Main test executor.
Coordinates test execution using execution mode and testers.
"""

import logging
from typing import List, Dict, Any

from tests.core.interfaces import (
    IExecutionMode,
    ITester,
    TestCase,
    TestResult,
    TestContext,
    TestStatus,
)
from tests.core.exceptions import TestExecutionError

logger = logging.getLogger(__name__)


class TestExecutor:
    """Executes tests using injected execution mode and testers"""

    def __init__(
        self,
        execution_mode: IExecutionMode,
        testers: List[ITester],
        config: Dict[str, Any] = None,
    ):
        self.execution_mode = execution_mode
        self.testers = testers
        self.config = config or {}

    async def execute_tests(
        self, tests: List[TestCase], context: TestContext
    ) -> List[TestResult]:
        """Execute all tests and return results"""

        if not tests:
            logger.warning("No tests to execute")
            return []

        logger.info(f"Executing {len(tests)} tests in {context.mode} mode")

        results = []

        for i, test in enumerate(tests, 1):
            logger.info(f"Running test {i}/{len(tests)}: {test.id}")

            try:
                result = await self.execution_mode.execute_test(
                    test_case=test, context=context, testers=self.testers
                )
                results.append(result)

                # Log immediate result
                status_emoji = "✅" if result.passed else "❌"
                logger.info(
                    f"{status_emoji} Test {test.id}: {result.status.value} "
                    f"(score: {result.score:.1f}, duration: {result.duration_ms:.0f}ms)"
                )

            except Exception as e:
                logger.error(f"Failed to execute test '{test.id}': {e}")
                # Create a failed result
                results.append(
                    TestResult(
                        test_id=test.id,
                        test_input=test.input,
                        status=TestStatus.FAIL,
                        score=0.0,
                        details={"error": str(e), "error_type": type(e).__name__},
                        duration_ms=0.0,
                    )
                )

        # Log summary
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        avg_score = sum(r.score for r in results) / len(results) if results else 0

        logger.info(
            f"Execution complete: {passed} passed, {failed} failed "
            f"(avg score: {avg_score:.1f})"
        )

        return results

    async def execute_single(self, test: TestCase, context: TestContext) -> TestResult:
        """Execute a single test"""
        return await self.execution_mode.execute_test(
            test_case=test, context=context, testers=self.testers
        )

    def generate_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """
        Generate summary statistics from test results.

        Returns:
            Dictionary with summary stats
        """
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASS)
        failed = sum(1 for r in results if r.status == TestStatus.FAIL)
        warnings = sum(1 for r in results if r.status == TestStatus.WARNING)

        avg_score = sum(r.score for r in results) / total if total > 0 else 0.0
        avg_duration = sum(r.duration_ms for r in results) / total if total > 0 else 0.0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "success_rate": (passed / total * 100) if total > 0 else 0.0,
            "avg_score": round(avg_score, 2),
            "avg_duration_ms": round(avg_duration, 2),
        }
