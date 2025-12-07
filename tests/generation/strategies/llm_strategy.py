"""
LLM-based test variation generation strategy.
Uses OpenAI to generate creative test variations.
"""

import logging
import dotenv
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from .base import BaseVariationStrategy

logger = logging.getLogger(__name__)

dotenv.load_dotenv(".env.local")


class LLMVariationStrategy(BaseVariationStrategy):
    """Generates test variations using LLM"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.model = self.config.get("model", "gpt-4o-mini")
        self.temperature = self.config.get("temperature", 0.7)
        self.client = AsyncOpenAI()  # Uses OPENAI_API_KEY env var

    async def generate_variations(
        self, seed_input: str, count: int, context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate variations using OpenAI LLM"""

        context = context or {}
        category = context.get("category", "general")
        expected_behavior = context.get("expected_behavior", "")

        prompt = self._build_prompt(seed_input, count, category, expected_behavior)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a test case generator for voice AI agents. Generate diverse, realistic variations of user inputs.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            variations = self._parse_variations(content)
            variations = self._deduplicate(variations)

            logger.info(f"Generated {len(variations)} variations for: '{seed_input}'")

            return variations[:count]

        except Exception as e:
            logger.error(f"Failed to generate variations: {e}")
            return []

    def _build_prompt(
        self, seed_input: str, count: int, category: str, expected_behavior: str
    ) -> str:
        """Build the LLM prompt for variation generation"""

        prompt = f"""Generate {count} diverse variations of this user input for testing a voice AI agent:

Original input: "{seed_input}"
Category: {category}
{f"Expected behavior: {expected_behavior}" if expected_behavior else ""}

Create variations that test:
1. Different phrasings and word choices
2. Casual vs formal language
3. Short vs verbose expressions
4. Different ways to express the same intent
5. Minor typos or speech recognition errors
6. Edge cases (ambiguous times, missing details)

Return ONLY the variations, one per line, without numbering or explanation.
Make them realistic - how real users would actually speak."""

        return prompt

    def _parse_variations(self, content: str) -> List[str]:
        """Parse variations from LLM response"""
        lines = content.strip().split("\n")
        variations = []

        for line in lines:
            # Remove numbering, bullets, quotes
            line = line.strip()
            line = line.lstrip("0123456789.-*•› ")
            line = line.strip("\"'")

            if line and len(line) > 5:  # Skip too short lines
                variations.append(line)

        return variations
