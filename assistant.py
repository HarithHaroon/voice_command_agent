"""
Simple AI Assistant with tool functions for weather, time, calculations, and preferences.
"""

from livekit.agents import Agent

from tools.weather import WeatherTool
from tools.time_utils import TimeTool
from tools.calculator import CalculatorTool
from tools.preferences import PreferencesTool


class SimpleAssistant(Agent, WeatherTool, TimeTool, CalculatorTool, PreferencesTool):
    """
    AI Assistant that combines multiple tool capabilities.

    This assistant can:
    - Look up weather information
    - Get current time in different timezones
    - Perform mathematical calculations
    - Save and retrieve user preferences
    """

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful AI assistant that can look up weather information, "
                "get the current time, and perform calculations. Always be friendly "
                "and informative."
            )
        )
