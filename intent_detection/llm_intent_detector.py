"""
LLM-based intent detection using OpenAI.
Provides semantic understanding of user intent.
"""

import json
import logging
from typing import Dict
from openai import AsyncOpenAI
from dotenv import load_dotenv

from models.intent_result import IntentResult

load_dotenv(".env.local")


logger = logging.getLogger(__name__)


class LLMIntentDetector:
    """LLM-based intent detector using OpenAI"""

    def __init__(
        self,
        available_modules: Dict[str, str],
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
    ):
        """
        Initialize LLM intent detector.

        Args:
            available_modules: Dict of {module_name: description}
            model: OpenAI model to use
            temperature: Sampling temperature (lower = more deterministic)
        """
        self.available_modules = available_modules
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI()

        logger.info(
            f"LLMIntentDetector initialized with {len(available_modules)} modules"
        )

    async def detect(self, user_input: str) -> IntentResult:
        """
        Detect intent using LLM.

        Args:
            user_input: User's message

        Returns:
            IntentResult with detected modules and confidence
        """
        try:
            # Build prompt
            prompt = self._build_prompt(user_input)

            # Call OpenAI
            logger.debug(f"Detecting intent for: '{user_input}'")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an intent classification expert. Analyze user messages and determine which modules should be activated.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature,
            )

            # Parse response
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)

            modules = result_json.get("modules", [])
            confidence = result_json.get("confidence", 0.0)
            reasoning = result_json.get("reasoning", "")

            logger.info(f"Detected modules: {modules} (confidence: {confidence})")

            return IntentResult(
                modules=modules,
                confidence=confidence,
                reasoning=reasoning,
                raw_response=result_text,
            )

        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            # Return safe default
            return IntentResult(
                modules=[],
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                raw_response="",
            )

    def _build_prompt(self, user_input: str) -> str:
        """Build prompt for LLM intent detection"""

        # Format available modules
        modules_desc = "\n".join(
            [f"- {name}: {desc}" for name, desc in self.available_modules.items()]
        )

        prompt = f"""Analyze this user message and determine which modules should be activated.
        Available modules:
        {modules_desc}

        User message: "{user_input}"

        Rules:
        1. Return 1-3 most relevant modules
        2. Confidence should be 0.0 to 1.0 (higher = more confident)
        3. Provide brief reasoning for your choice
        4. BE RESILIENT TO TYPOS - interpret misspelled words based on context
        5. "show/open/take me to [feature]" = navigation module
        6. Focus on USER INTENT, not just keywords

        Return ONLY valid JSON in this exact format:
        {{
            "modules": ["module1", "module2"],
            "confidence": 0.95,
            "reasoning": "Brief explanation of why these modules were chosen"
        }}"""

        return prompt

    # Add to LLMIntentDetector class

    async def detect_from_history(
        self, user_message: str, conversation_history: list = None
    ) -> IntentResult:
        """
        Detect intent with conversation history context.
        Args:
            user_message: Current user message
            conversation_history: List of recent messages for context
        Returns:
            IntentResult with detected modules
        """
        # If no history or high confidence expected, just use current message
        if not conversation_history or len(conversation_history) < 2:
            return await self.detect(user_message)

        # Include last 3 user messages for context
        recent_context = " ".join(
            [m["content"] for m in conversation_history[-3:] if m.get("role") == "user"]
        )

        # Build enhanced prompt with context
        prompt = self._build_prompt_with_context(user_message, recent_context)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an intent classification expert. Analyze user messages with conversation context and determine which modules should be activated.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature,
            )

            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)

            return IntentResult(
                modules=result_json.get("modules", []),
                confidence=result_json.get("confidence", 0.0),
                reasoning=result_json.get("reasoning", ""),
                raw_response=result_text,
            )

        except Exception as e:
            logger.error(f"Intent detection with history failed: {e}")
            # Fallback to simple detection
            return await self.detect(user_message)

    def _build_prompt_with_context(self, user_message: str, recent_context: str) -> str:
        """Build prompt with conversation context"""
        modules_desc = "\n".join(
            [f"- {name}: {desc}" for name, desc in self.available_modules.items()]
        )

        prompt = f"""Analyze this user message WITH conversation context and determine which modules should be activated.

        Available modules:
        {modules_desc}

        Recent conversation context: "{recent_context}"
        Current user message: "{user_message}"

        Rules:
        1. Return 1-3 most relevant modules
        2. Use conversation context to better understand intent
        3. Confidence should be 0.0 to 1.0
        4. BE RESILIENT TO TYPOS
        5. Focus on USER INTENT

        Return ONLY valid JSON:
        {{
            "modules": ["module1", "module2"],
            "confidence": 0.95,
            "reasoning": "Brief explanation"
        }}"""

        return prompt
