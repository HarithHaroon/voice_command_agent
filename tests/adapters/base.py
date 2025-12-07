"""
Base adapter implementation with common functionality.
"""

from abc import ABC
from typing import Dict, Any, Optional
from tests.core.interfaces import IAgentAdapter
from tests.core.exceptions import AdapterError, AgentNotInitializedError


class BaseAdapter(IAgentAdapter, ABC):
    """Base class for agent adapters with common functionality"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False

    def _ensure_initialized(self):
        """Check if adapter has been initialized"""
        if not self._initialized:
            raise AgentNotInitializedError(
                "Adapter not initialized. Call initialize() first."
            )

    def is_initialized(self) -> bool:
        """Check if adapter is ready to use"""
        return self._initialized
