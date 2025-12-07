"""
Intent detection tester.
Tests if the agent correctly detects user intent and loads appropriate modules.
"""

import logging
from typing import Dict, Any

from tests.core.interfaces import ITester, TestCase, TestContext

logger = logging.getLogger(__name__)


class IntentTester(ITester):
    """Tests intent detection accuracy"""

    @property
    def name(self) -> str:
        return "intent"

    async def test(self, test_case: TestCase, context: TestContext) -> Dict[str, Any]:
        """
        Test intent detection.

        Expected format in test_case.expected:
        {
            "intent": {
                "modules": ["backlog", "navigation"],
                "confidence_min": 0.7
            }
        }
        """
        user_input = test_case.input
        expected = test_case.expected.get("intent", {})

        if not expected:
            return {
                "passed": True,
                "skipped": True,
                "reason": "No intent expectations defined",
            }

        try:
            # Use adapter to detect intent
            adapter = context.agent_instance
            intent_result = await adapter.detect_intent(user_input)

            # Extract results
            detected_modules = intent_result.get("modules", [])
            confidence = intent_result.get("confidence", 0.0)

            # Check expectations
            expected_modules = expected.get("modules", [])
            min_confidence = expected.get("confidence_min", 0.0)

            # Validate modules
            modules_match = all(
                module in detected_modules for module in expected_modules
            )

            # Validate confidence
            confidence_pass = confidence >= min_confidence

            passed = modules_match and confidence_pass

            return {
                "passed": passed,
                "detected_modules": detected_modules,
                "expected_modules": expected_modules,
                "confidence": confidence,
                "min_confidence": min_confidence,
                "modules_match": modules_match,
                "confidence_pass": confidence_pass,
                "details": {
                    "reasoning": intent_result.get("reasoning", ""),
                    "matched_patterns": intent_result.get("matched_patterns", {}),
                },
            }

        except Exception as e:
            logger.error(f"Intent test failed for '{test_case.id}': {e}")
            return {"passed": False, "error": str(e), "error_type": type(e).__name__}
