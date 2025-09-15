"""
User preferences management tool for the AI assistant.
"""

from livekit.agents import RunContext, ToolError, function_tool


class PreferencesTool:
    """Tool for managing user preferences."""

    @function_tool()
    async def save_user_preference(
        self, context: RunContext, preference_name: str, preference_value: str
    ) -> str:
        """
        Save a user preference for future conversations.

        Args:
            preference_name: Name of the preference (e.g., 'favorite_color', 'location')
            preference_value: Value of the preference

        Returns:
            Confirmation message
        """
        try:
            # Initialize userdata if it doesn't exist
            if not hasattr(context, "userdata") or context.userdata is None:
                context.userdata = {}

            context.userdata[preference_name] = preference_value

            return f"I've saved your preference: {preference_name} = {preference_value}"

        except Exception as e:
            raise ToolError(f"Unable to save preference: {preference_name}") from e

    @function_tool()
    async def get_user_preference(
        self, context: RunContext, preference_name: str
    ) -> str:
        """
        Retrieve a previously saved user preference.

        Args:
            preference_name: Name of the preference to retrieve

        Returns:
            The preference value or a message if not found
        """
        try:
            if (
                hasattr(context, "userdata")
                and context.userdata is not None
                and preference_name in context.userdata
            ):
                preference_value = context.userdata[preference_name]
                return f"Your {preference_name} preference is: {preference_value}"

            return f"I don't have a saved preference for '{preference_name}'"

        except Exception as e:
            raise ToolError(f"Unable to retrieve preference: {preference_name}") from e
