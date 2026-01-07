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
        "memory": "Storing/finding item locations, personal information, daily activities - where are my keys, remember my doctor, I just had lunch",
        "story": "Recording and retrieving life stories, memories, family history - tell a story, find stories about childhood, my wedding story",  # ← ADD THIS
        "settings": "Device configuration, fall detection, location tracking",
        "books": "Read books aloud, play books, answer questions about book content",
        "image": "Search for photos",
        "orchestrator": "Navigation between screens, video calls, conversation recall",
    }

    SYSTEM_PROMPT = """You are a routing assistant. Analyze the user's request and determine which specialist should handle it.

        Specialists:
        - health: {health}
        - backlog: {backlog}
        - medication: {medication}
        - memory: {memory}
        - settings: {settings}
        - books: {books}
        - image: {image}
        - orchestrator: {orchestrator}

        CRITICAL ROUTING RULES:
        1. Memory requests (storing/finding items, personal info, activities) → "memory"
        - Storing locations: "I put X on Y", "my keys are on the table"
        - Finding items: "where are my X?"
        - Storing facts: "remember X is Y", "my doctor is Dr. Smith", "I'm allergic to X", "trash day is Tuesday"
        - Recalling facts: "what's my X?", "what am I allergic to?"
        - Logging activities: "I just had lunch", "my daughter visited"

        2. Story requests (recording life stories, retrieving memories) → "story"
        Examples: "I want to tell a story", "tell me about when I was young", "record my memory", "find my childhood stories"
        
        3. ANY mention of medications, pills, prescriptions, doses → "medication"
        Examples: "add my medication", "remind me to take pills"
        
        4. FUTURE reminders (groceries, calls, tasks) → "backlog"
        Examples: "remind me to call mom tomorrow", "don't let me forget to buy groceries"
        NOT: "trash day is Tuesday" (that's storing a FACT = memory)
        
        5. Health DATA queries (metrics, readings) → "health"
        Examples: "what's my blood pressure?", "how many steps today?"
        NOT: "what am I allergic to?" (that's recalling a FACT = memory)
        
        6. Navigation requests → "orchestrator"
        Examples: "go to settings", "navigate to health"

        Respond ONLY with the specialist name.
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
