"""
Tool selection tester.
Tests if the agent selects the correct tool for the given input.
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
            "tool": "add_reminder"
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
            # Get tool selection from context metadata
            # (populated by execution mode)
            actual_tool = context.metadata.get("tool_called")

            if actual_tool is None:
                return {
                    "passed": False,
                    "error": "No tool was called",
                    "expected_tool": expected_tool,
                }

            passed = actual_tool == expected_tool

            return {
                "passed": passed,
                "expected_tool": expected_tool,
                "actual_tool": actual_tool,
                "match": passed,
            }

        except Exception as e:
            logger.error(f"Tool test failed for '{test_case.id}': {e}")
            return {"passed": False, "error": str(e), "error_type": type(e).__name__}
