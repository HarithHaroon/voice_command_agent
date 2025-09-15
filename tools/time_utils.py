"""
Time utilities tool for the AI assistant - Flutter integration version.
"""

import json
from livekit.agents import RunContext, ToolError, function_tool


class TimeTool:
    """Tool for getting current time information via Flutter app."""

    @function_tool()
    async def get_current_time(self, context: RunContext, timezone: str = "UTC") -> str:
        """
        Get the current time in a specific timezone via Flutter app.

        Args:
            timezone: The timezone to get time for (e.g., 'UTC', 'EST', 'PST')

        Returns:
            Current time as a formatted string from Flutter app
        """
        try:
            # Send tool request to Flutter app
            tool_request = {
                "type": "tool_request",
                "tool": "get_current_time",
                "params": {"timezone": timezone},
            }

            # Send the request via data channel
            await context.session.room.local_participant.publish_data(
                json.dumps(tool_request).encode("utf-8")
            )

            # Tell user we're getting the time
            await context.session.say(f"Let me check the current time in {timezone}...")

            # In a real implementation, you'd wait for the response
            # For now, return a placeholder
            return f"Time request sent to Flutter app for timezone: {timezone}"

        except Exception as e:
            raise ToolError(f"Unable to get time for timezone {timezone}") from e
