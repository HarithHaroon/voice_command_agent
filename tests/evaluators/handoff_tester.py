"""
Agent handoff tester.
Tests if agent transitions work correctly.
"""

import logging
from typing import Dict, Any

from tests.core.interfaces import ITester, TestCase, TestContext

logger = logging.getLogger(__name__)


class HandoffTester(ITester):
    """Tests agent handoff success"""

    @property
    def name(self) -> str:
        return "handoff"

    async def test(self, test_case: TestCase, context: TestContext) -> Dict[str, Any]:
        """
        Test agent handoffs.

        Checks if handoffs occurred and completed successfully.
        """
        expected_agent = test_case.agent

        try:
            # Get handoffs from context
            handoffs = context.metadata.get("handoffs", [])

            # Orchestrator tasks don't require handoffs
            if expected_agent == "orchestrator":
                # Should have no handoffs
                passed = len(handoffs) == 0

                return {
                    "passed": passed,
                    "expected_agent": "orchestrator",
                    "handoffs": handoffs,
                    "note": "Orchestrator handles directly, no handoff needed",
                }

            # Specialist agent tasks require handoffs
            if not handoffs:
                return {
                    "passed": False,
                    "error": "No handoffs recorded",
                    "expected_agent": expected_agent,
                }

            # Check if handoff to expected agent occurred
            expected_agent_name = f"{expected_agent.title()}Agent"
            handoff_occurred = any(h.get("to") == expected_agent_name for h in handoffs)

            return {
                "passed": handoff_occurred,
                "expected_agent": expected_agent,
                "expected_agent_name": expected_agent_name,
                "handoffs": handoffs,
                "handoff_occurred": handoff_occurred,
            }

        except Exception as e:
            logger.error(f"Handoff test failed for '{test_case.id}': {e}")
            return {"passed": False, "error": str(e), "error_type": type(e).__name__}
