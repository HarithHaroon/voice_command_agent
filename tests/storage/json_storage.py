"""
JSON storage implementation for test cases.
"""

import json
import logging
from pathlib import Path
from typing import List

from tests.core.interfaces import ITestStorage, TestCase
from tests.core.exceptions import StorageError

logger = logging.getLogger(__name__)


class JSONStorage(ITestStorage):
    """JSON file storage for test cases"""

    async def save(self, tests: List[TestCase], filepath: str) -> None:
        """Save test cases to JSON file"""
        try:
            # Ensure directory exists
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Convert test cases to dict format
            tests_data = [self._test_to_dict(test) for test in tests]

            # Write to file
            with open(path, "w", encoding="utf-8") as f:
                json.dump(tests_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(tests)} test cases to {filepath}")

        except Exception as e:
            raise StorageError(f"Failed to save tests to {filepath}: {e}")

    async def load(self, filepath: str) -> List[TestCase]:
        """Load test cases from JSON file"""
        try:
            path = Path(filepath)

            if not path.exists():
                raise StorageError(f"File not found: {filepath}")

            # Read from file
            with open(path, "r", encoding="utf-8") as f:
                tests_data = json.load(f)

            # Convert to TestCase objects
            tests = [self._dict_to_test(data) for data in tests_data]

            logger.info(f"Loaded {len(tests)} test cases from {filepath}")

            return tests

        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in {filepath}: {e}")
        except Exception as e:
            raise StorageError(f"Failed to load tests from {filepath}: {e}")

    def _test_to_dict(self, test: TestCase) -> dict:
        """Convert TestCase to dictionary"""
        return {
            "id": test.id,
            "agent": test.agent,
            "input": test.input,
            "expected": test.expected,
            "metadata": test.metadata,
        }

    def _dict_to_test(self, data: dict) -> TestCase:
        """Convert dictionary to TestCase"""
        return TestCase(
            id=data["id"],
            agent=data["agent"],
            input=data["input"],
            expected=data["expected"],
            metadata=data.get("metadata", {}),
        )
