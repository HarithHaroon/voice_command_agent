"""
Weather lookup tool for the AI assistant.
"""

import asyncio
from typing import Any, Dict

from livekit.agents import RunContext, ToolError, function_tool


class WeatherTool:
    """Tool for looking up weather information."""

    @function_tool()
    async def lookup_weather(
        self,
        context: RunContext,
        location: str,
    ) -> Dict[str, Any]:
        """
        Look up current weather information for a given location.

        Args:
            location: The city and country (e.g., 'New York, USA' or 'London, UK')

        Returns:
            Dictionary containing weather information
        """
        try:
            # Tell user we're looking up weather
            await context.session.say(f"Let me check the weather for {location}...")

            # Simulate API delay
            await asyncio.sleep(1)

            # Mock weather data (replace with real API in production)
            mock_weather_data = {
                "location": location,
                "temperature": "22°C (72°F)",
                "description": "Partly cloudy",
                "humidity": "65%",
                "wind_speed": "10 km/h",
            }

            return mock_weather_data

        except Exception as e:
            raise ToolError(
                f"Unable to retrieve weather for {location}. Please try again later."
            ) from e
