from typing import List
from attr import dataclass


@dataclass
class IntentResult:
    """Result from intent detection"""

    modules: List[str]
    confidence: float
    reasoning: str
    raw_response: str
