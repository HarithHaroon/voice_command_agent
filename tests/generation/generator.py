"""
Main test generator.
Orchestrates test case generation from seed examples.
"""

import logging
from typing import List, Dict, Any, Optional

from tests.core.interfaces import TestCase, IVariationStrategy, ITestStorage
from tests.core.exceptions import TestGenerationError

logger = logging.getLogger(__name__)


class TestGenerator:
    """Generates test cases from seed examples"""

    def __init__(
        self,
        strategy: IVariationStrategy,
        storage: ITestStorage,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.strategy = strategy
        self.storage = storage
        self.config = config or {}

    async def generate_from_seeds(
        self, seed_cases: List[TestCase], variations_per_seed: int = 10
    ) -> List[TestCase]:
        """
        Generate test variations from seed test cases.

        Args:
            seed_cases: Original seed test cases
            variations_per_seed: Number of variations to generate per seed

        Returns:
            List including seed cases + generated variations
        """

        if not seed_cases:
            raise TestGenerationError("No seed cases provided")

        logger.info(f"Generating variations from {len(seed_cases)} seed cases")

        all_tests = []

        # Include original seed cases
        all_tests.extend(seed_cases)

        # Generate variations for each seed
        for seed in seed_cases:
            logger.info(f"Generating {variations_per_seed} variations for: {seed.id}")

            try:
                # Extract expected tool for context
                expected_tool = seed.expected.get("tool", "")

                variations = await self.strategy.generate_variations(
                    seed_input=seed.input,
                    count=variations_per_seed,
                    context={
                        "agent": seed.agent,
                        "expected_tool": expected_tool,
                        "metadata": seed.metadata,
                    },
                )

                # Create test cases from variations
                for i, variation_input in enumerate(variations, 1):
                    variation_test = TestCase(
                        id=f"{seed.id}_var_{i}",
                        agent=seed.agent,
                        input=variation_input,
                        expected=seed.expected.copy(),
                        metadata={
                            **seed.metadata,
                            "generated": True,
                            "seed_id": seed.id,
                            "variation_number": i,
                        },
                    )
                    all_tests.append(variation_test)

                logger.info(f"Generated {len(variations)} variations for {seed.id}")

            except Exception as e:
                logger.error(f"Failed to generate variations for {seed.id}: {e}")
                continue

        logger.info(f"Total test cases generated: {len(all_tests)}")

        return all_tests

    async def save_tests(self, tests: List[TestCase], filepath: str) -> None:
        """Save generated tests to storage"""
        try:
            await self.storage.save(tests, filepath)
            logger.info(f"Saved {len(tests)} tests to {filepath}")
        except Exception as e:
            raise TestGenerationError(f"Failed to save tests: {e}")

    async def load_tests(self, filepath: str) -> List[TestCase]:
        """Load tests from storage"""
        try:
            tests = await self.storage.load(filepath)
            logger.info(f"Loaded {len(tests)} tests from {filepath}")
            return tests
        except Exception as e:
            raise TestGenerationError(f"Failed to load tests: {e}")

    async def generate_and_save(
        self,
        seed_cases: List[TestCase],
        output_path: str,
        variations_per_seed: int = 10,
    ) -> List[TestCase]:
        """
        Convenience method: generate variations and save them.

        Returns:
            Generated test cases
        """
        tests = await self.generate_from_seeds(seed_cases, variations_per_seed)
        await self.save_tests(tests, output_path)
        return tests

    def estimate_cost(
        self, seed_count: int, variations_per_seed: int
    ) -> Dict[str, float]:
        """
        Estimate generation cost.

        Returns:
            {
                "total_variations": int,
                "estimated_cost_usd": float,
                "model": str
            }
        """
        total_variations = seed_count * variations_per_seed

        # Cost estimates for gpt-4o-mini
        # ~$0.001 per variation (rough estimate)
        cost_per_variation = 0.001

        estimated_cost = total_variations * cost_per_variation

        return {
            "total_variations": total_variations,
            "estimated_cost_usd": round(estimated_cost, 2),
            "model": (
                self.strategy.model if hasattr(self.strategy, "model") else "unknown"
            ),
        }
