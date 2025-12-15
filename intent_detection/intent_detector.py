"""Intent Detector - Maps user messages to required modules."""

import re
import logging
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    modules: List[str]
    confidence: float
    reasoning: str
    matched_patterns: Dict[str, int]


class IntentDetector:
    INTENT_PATTERNS = {
        "reading_ocr": [
            r"\b(read|label|document|bottle|text|book)\b",
            r"\bwhat does (this|that|it) say\b",
        ],
        "medication_reminders": [
            r"\b(remind|medication|medicine|pills?|dose)\b",
            r"\bset (a )?reminder\b",
        ],
        "face_recognition": [
            r"\b(who is|recognize|person|face|photo)\b",
            r"\bwho('s| is) (this|that)\b",
        ],
        "video_calling": [
            r"\b(call|video call|talk to|contact)\b",
            r"\b(daughter|son|family|grandchild)\b",
        ],
        "memory_recall": [
            r"\b(remember|recall|talked about|mentioned)\b",
            r"\bwhat did (we|I) (talk|say)\b",
        ],
        "settings_fall_detection": [
            r"\b(fall detection|sensitivity|emergency)\b",
            r"\bturn (on|off) fall\b",
        ],
        "settings_location": [
            r"\b(location|tracking|gps)\b",
            r"\bturn (on|off) location\b",
        ],
        "book_reading": [
            r"\b(book|chapter|page|continue reading)\b",
            r"\bread (the |my )?book\b",
        ],
        "ai_assistant": [
            r"\b(ai assistant|sidekick|upload|analyze)\b",
            r"\bhelp (me )?(with|search)\b",
        ],
        "form_handling": [r"\b(form|fill out|submit)\b"],
        "backlog": [
            r"\b(remind|reminder|don'?t forget|remember to)\b",
            r"\bwhat do I have\b",
            r"\b(today|tomorrow|this week)('s| schedule)?\b",
            r"\b(cancel|delete|done|completed|finished)\b.*\breminder\b",
        ],
        "health_query": [
            r"\bhow (am I|is my health|am I doing)\b",
            r"\b(health|wellness) (status|check|update|summary|report)\b",
            r"\b(heart rate|blood pressure|blood oxygen|steps|sleep|calories)\b",
            r"\bhow (many|much) (steps|calories|sleep)\b",
            r"\bwhat('s| is) my (heart rate|blood pressure|steps|sleep)\b",
            r"\bgood morning\b",
            r"\bvital signs?\b",
            r"\bhealth metrics?\b",
        ],
    }

    CORE_MODULES = ["navigation"]
    MODULE_DEPENDENCIES = {"medication_reminders": ["form_handling"]}

    def __init__(self):
        self.compiled_patterns = {
            module: [re.compile(p, re.IGNORECASE) for p in patterns]
            for module, patterns in self.INTENT_PATTERNS.items()
        }
        logger.info("IntentDetector initialized")

    def detect(self, user_message: str) -> IntentResult:
        detected_modules = set(self.CORE_MODULES)
        match_scores = {}

        for module, patterns in self.compiled_patterns.items():
            matches = sum(1 for p in patterns if p.search(user_message))
            if matches > 0:
                match_scores[module] = matches
                detected_modules.add(module)
                if module in self.MODULE_DEPENDENCIES:
                    detected_modules.update(self.MODULE_DEPENDENCIES[module])

        confidence = (
            min(0.5 + (max(match_scores.values()) * 0.2), 1.0) if match_scores else 0.3
        )
        if not match_scores:
            detected_modules.add("memory_recall")

        reasoning = (
            f"Detected: {', '.join([m for m, _ in sorted(match_scores.items(), key=lambda x: x[1], reverse=True)[:3]])}"
            if match_scores
            else "No specific intent"
        )

        return IntentResult(
            modules=sorted(list(detected_modules)),
            confidence=confidence,
            reasoning=reasoning,
            matched_patterns=match_scores,
        )

    def detect_from_history(
        self, user_message: str, conversation_history: List[Dict]
    ) -> IntentResult:
        result = self.detect(user_message)

        if result.confidence < 0.7 and conversation_history:
            recent = " ".join(
                [
                    m["content"]
                    for m in conversation_history[-3:]
                    if m.get("role") == "user"
                ]
            )
            if recent:
                context_result = self.detect(recent)
                result.modules = sorted(
                    list(set(result.modules) | set(context_result.modules))
                )
                result.confidence = min(result.confidence + 0.2, 1.0)
                result.reasoning += f" | Context: {context_result.reasoning}"

        return result
