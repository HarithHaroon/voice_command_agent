"""
Intent analyzer - Determines which specialist should handle a request.
"""

import logging
from typing import Dict, List, Optional
import openai

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """Analyzes user intent to route to correct specialist"""

    SPECIALIST_DESCRIPTIONS = {
        "health": "Health metrics, vitals, wellness, blood pressure, heart rate, steps, sleep",
        "backlog": "General reminders and tasks (NOT medications) - groceries, calls, appointments, to-dos",
        "medication": "ALL medication requests - add/view/edit/delete medications, take pills, dose tracking, refills, prescriptions",
        "settings": "Device configuration, fall detection, location tracking",
        "books": "Read books aloud, play books, answer questions about book content",
        "image": "Search for photos",
        "orchestrator": "Navigation between screens, video calls, memory recall",
    }

    SYSTEM_PROMPT = """You are a routing assistant. Analyze the user's request and determine which specialist should handle it.

        Specialists:
        - health: {health}
        - backlog: {backlog}
        - medication: {medication}
        - settings: {settings}
        - books: {books}
        - image: {image}
        - orchestrator: {orchestrator}

        CRITICAL ROUTING RULES:
        1. ANY mention of medications, pills, prescriptions, doses → "medication"
        Examples: "add my medication", "remind me to take pills", "I took my Lisinopril"
        
        2. General reminders (groceries, calls, tasks) → "backlog"
        Examples: "remind me to call mom", "buy groceries", "water plants"
        
        3. Navigation requests → "orchestrator"
        Examples: "go to settings", "navigate to health", "take me to medications screen"
        Even if mentioning a specialist area, NAVIGATION = orchestrator

        Respond ONLY with the specialist name (e.g., "health", "medication", "backlog").
    """

    def __init__(self, client: openai.AsyncOpenAI):
        self.client = client
        self.system_prompt = self.SYSTEM_PROMPT.format(**self.SPECIALIST_DESCRIPTIONS)

    async def analyze_intent(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Analyze user intent to determine routing.

        Args:
            user_input: Current user message
            conversation_history: Previous conversation turns

        Returns:
            Specialist name (e.g., "health", "medication", "orchestrator")
        """
        if conversation_history is None:
            conversation_history = []

        messages = [
            {"role": "system", "content": self.system_prompt},
            *conversation_history,
            {
                "role": "user",
                "content": f"Which specialist handles this request: '{user_input}'",
            },
        ]

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
        )

        intent = response.choices[0].message.content.strip().lower()

        logger.info(f"Intent analysis: {intent}")

        return intent
