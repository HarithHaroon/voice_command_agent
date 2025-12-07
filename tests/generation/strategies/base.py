"""
Base interface for test variation generation strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from tests.core.interfaces import IVariationStrategy


class BaseVariationStrategy(IVariationStrategy):
    """Base class for variation generation strategies"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    async def generate_variations(
        self, seed_input: str, count: int, context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate variations of a seed input.

        Args:
            seed_input: Original input to create variations from
            count: Number of variations to generate
            context: Optional context (category, expected behavior, etc.)

        Returns:
            List of variation strings
        """
        pass

    def _deduplicate(self, variations: List[str]) -> List[str]:
        """Remove duplicate variations while preserving order"""
        seen = set()
        result = []
        for var in variations:
            normalized = var.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                result.append(var)
        return result
