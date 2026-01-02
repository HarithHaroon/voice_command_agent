"""
LLM-based test variation generation strategy.
Uses OpenAI to generate creative test variations from seed cases.
"""

import dotenv
import logging
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional

from tests.core.interfaces import IVariationStrategy
from tests.core.exceptions import TestGenerationError

dotenv.load_dotenv(".env.local")

logger = logging.getLogger(__name__)


class LLMVariationStrategy(IVariationStrategy):
    """Generates test variations using LLM"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model = self.config.get("model", "gpt-4o-mini")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 2000)
        self.client = AsyncOpenAI()

    async def generate_variations(
        self, seed_input: str, count: int, context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate variations using OpenAI LLM"""
        context = context or {}
        agent = context.get("agent", "general")
        expected_tool = context.get("expected_tool", "")

        prompt = self._build_prompt(seed_input, count, agent, expected_tool)

        try:
            logger.info(f"Generating {count} variations for: '{seed_input}'")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a test case generator for multi-agent voice AI systems. Generate diverse, realistic variations of user inputs for elderly users.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content
            variations = self._parse_variations(content)
            variations = self._deduplicate(variations)

            logger.info(f"Generated {len(variations)} variations for: '{seed_input}'")

            return variations[:count]

        except Exception as e:
            logger.error(f"Failed to generate variations: {e}")
            raise TestGenerationError(f"LLM generation failed: {e}")

    def _build_prompt(
        self, seed_input: str, count: int, agent: str, expected_tool: str
    ) -> str:
        """Build the LLM prompt for variation generation"""

        prompt = f"""Generate {count} diverse variations of this user input for testing a voice AI agent for elderly users:

Original input: "{seed_input}"
Agent: {agent}
{f"Expected action: {expected_tool}" if expected_tool else ""}

IMPORTANT CONTEXT:
- Users are elderly (60-90 years old)
- Voice interface (not typed text)
- Users may speak casually, use simple language
- Some users may have speech recognition errors

Create variations that test:
1. Different phrasings and word choices (casual vs formal)
2. Short vs verbose expressions
3. Common speech patterns for elderly users
4. Minor speech recognition errors (typos, mishearings)
5. Different ways to express the same intent
6. Edge cases (ambiguous requests, missing details)

GUIDELINES:
- Keep language natural and conversational
- Avoid technical jargon
- Include some simple, direct phrases
- Include some longer, more descriptive phrases
- Vary politeness levels ("please", "could you", etc.)

Return ONLY the variations, one per line, without numbering or explanation.
Make them realistic - how real elderly users would actually speak to a voice assistant."""

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
