"""
CSV storage implementation for test cases.
Makes it easy for non-technical stakeholders to edit test data.
"""

import csv
import json
import logging
from pathlib import Path
from typing import List

from tests.core.interfaces import ITestStorage, TestCase
from tests.core.exceptions import StorageError

logger = logging.getLogger(__name__)


class CSVStorage(ITestStorage):
    """CSV file storage for test cases"""

    async def save(self, tests: List[TestCase], filepath: str) -> None:
        """Save test cases to CSV file"""
        try:
            # Ensure directory exists
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write to CSV
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["id", "agent", "input", "expected", "metadata"],
                )
                writer.writeheader()

                for test in tests:
                    writer.writerow(
                        {
                            "id": test.id,
                            "agent": test.agent,
                            "input": test.input,
                            "expected": json.dumps(test.expected),
                            "metadata": json.dumps(test.metadata),
                        }
                    )

            logger.info(f"Saved {len(tests)} test cases to {filepath}")

        except Exception as e:
            raise StorageError(f"Failed to save tests to {filepath}: {e}")

    async def load(self, filepath: str) -> List[TestCase]:
        """Load test cases from CSV file"""
        try:
            path = Path(filepath)

            if not path.exists():
                raise StorageError(f"File not found: {filepath}")

            tests = []

            # Read from CSV
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    test = TestCase(
                        id=row["id"],
                        agent=row["agent"],
                        input=row["input"],
                        expected=json.loads(row["expected"]),
                        metadata=json.loads(row.get("metadata", "{}")),
                    )
                    tests.append(test)

            logger.info(f"Loaded {len(tests)} test cases from {filepath}")

            return tests

        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in CSV file {filepath}: {e}")
        except Exception as e:
            raise StorageError(f"Failed to load tests from {filepath}: {e}")
