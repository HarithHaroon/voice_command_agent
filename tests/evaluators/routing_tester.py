"""
Agent routing tester.
Tests if the orchestrator routes to the correct specialist agent.
"""

import logging
from typing import Dict, Any

from tests.core.interfaces import ITester, TestCase, TestContext

logger = logging.getLogger(__name__)


class RoutingTester(ITester):
    """Tests agent routing accuracy"""

    @property
    def name(self) -> str:
        return "routing"

    async def test(self, test_case: TestCase, context: TestContext) -> Dict[str, Any]:
        """
        Test agent routing.

        Checks if the correct agent handled the request.
        """
        expected_agent = test_case.agent

        try:
            # Get agent path from context
            agent_path = context.metadata.get("agent_path", [])

            if not agent_path:
                return {
                    "passed": False,
                    "error": "No agent path recorded",
                    "expected_agent": expected_agent,
                }

            # For orchestrator tests, should stay in orchestrator
            if expected_agent == "orchestrator":
                # Should only have ["Orchestrator"] in path
                passed = len(agent_path) == 1 and agent_path[0] == "Orchestrator"

                return {
                    "passed": passed,
                    "expected_agent": "orchestrator",
                    "agent_path": agent_path,
                    "note": "Should not handoff to any specialist",
                }

            # For specialist agent tests, should route to that agent
            expected_agent_name = f"{expected_agent.title()}Agent"
            passed = expected_agent_name in agent_path

            return {
                "passed": passed,
                "expected_agent": expected_agent,
                "expected_agent_name": expected_agent_name,
                "agent_path": agent_path,
                "routed_correctly": passed,
            }

        except Exception as e:
            logger.error(f"Routing test failed for '{test_case.id}': {e}")
            return {"passed": False, "error": str(e), "error_type": type(e).__name__}
