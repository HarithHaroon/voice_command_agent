"""
Tool selection tester.
Tests if the agent calls the correct tool for the given input.
"""

import logging
from typing import Dict, Any

from tests.core.interfaces import ITester, TestCase, TestContext

logger = logging.getLogger(__name__)


class ToolTester(ITester):
    """Tests tool selection accuracy"""

    @property
    def name(self) -> str:
        return "tool"

    async def test(self, test_case: TestCase, context: TestContext) -> Dict[str, Any]:
        """
        Test tool selection.

        Expected format in test_case.expected:
        {
            "tool": "get_health_summary"
        }
        """
        expected_tool = test_case.expected.get("tool")

        if not expected_tool:
            return {
                "passed": True,
                "skipped": True,
                "reason": "No tool expectations defined",
            }

        try:
            # Get tools called from context metadata
            tools_called = context.metadata.get("tools_called", [])

            if not tools_called:
                return {
                    "passed": False,
                    "error": "No tool was called",
                    "expected_tool": expected_tool,
                    "actual_tools": [],
                }

            # Check if expected tool was called
            passed = expected_tool in tools_called

            return {
                "passed": passed,
                "expected_tool": expected_tool,
                "actual_tools": tools_called,
                "match": passed,
            }

        except Exception as e:
            logger.error(f"Tool test failed for '{test_case.id}': {e}")
            return {"passed": False, "error": str(e), "error_type": type(e).__name__}
