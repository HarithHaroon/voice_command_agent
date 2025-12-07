"""
Adapter factory for creating agent adapters.
"""

from typing import Dict, Any
from tests.core.exceptions import ConfigurationError
from .livekit_adapter import LiveKitAdapter


def create_adapter(config: Dict[str, Any]):
    """
    Factory function to create the appropriate adapter based on config.

    Args:
        config: Adapter configuration with 'type' key

    Returns:
        IAgentAdapter instance

    Raises:
        ConfigurationError: If adapter type is unknown
    """

    adapter_type = config.get("type", "livekit")

    # Registry of available adapters
    adapters = {
        "livekit": LiveKitAdapter,
        # Add more adapters here as needed:
        # 'langchain': LangChainAdapter,
        # 'llamaindex': LlamaIndexAdapter,
    }

    if adapter_type not in adapters:
        available = ", ".join(adapters.keys())
        raise ConfigurationError(
            f"Unknown adapter type: '{adapter_type}'. "
            f"Available adapters: {available}"
        )

    adapter_class = adapters[adapter_type]
    return adapter_class(config)


__all__ = ["create_adapter", "LiveKitAdapter"]
