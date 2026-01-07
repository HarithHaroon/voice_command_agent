"""
Memory Tools - Server-side tools for general memory management.
Handles item locations, stored information, and daily activities.
"""

import logging
from typing import List, Optional
from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from clients.memory_client import MemoryClient

logger = logging.getLogger(__name__)


class MemoryTool(ServerSideTool):
    """Server-side tool for managing elderly user memory."""

    def __init__(self, memory_client: MemoryClient):
        super().__init__("memory")

        self.memory_client = memory_client

        self._user_id = None

        logger.info("MemoryTool initialized")

    def set_user_id(self, user_id: str):
        """Set the user ID for all memory operations."""
        self._user_id = user_id

        logger.info(f"MemoryTool user_id set to: {user_id}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return [
            "store_item_location",
            "find_item",
            "store_information",
            "recall_information",
            "log_activity",
            "get_daily_context",
            "what_was_i_doing",
        ]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [
            self.store_item_location,
            self.find_item,
            self.store_information,
            self.recall_information,
            self.log_activity,
            self.get_daily_context,
            self.what_was_i_doing,
        ]

    @function_tool
    async def store_item_location(
        self, item: str, location: str, room: str = ""
    ) -> str:
        """
        Store where the user put an item.

        Args:
            item: Name of the item (e.g., "glasses", "keys", "phone")
            location: Specific location (e.g., "nightstand", "kitchen counter")
            room: Room name (e.g., "bedroom", "kitchen") - optional

        Returns:
            Confirmation message
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            result = self.memory_client.store_item_location(
                user_id=self._user_id,
                item=item,
                location=location,
                room=room,
            )

            if result.get("success"):
                room_part = f" in the {room}" if room else ""

                return f"Got it! I'll remember your {item} is at {location}{room_part}."
            else:
                return f"I had trouble saving that. Error: {result.get('error', 'Unknown')}"

        except Exception as e:
            logger.error(f"Error storing item location: {e}")

            return f"Sorry, I couldn't save that information. Error: {str(e)}"

    @function_tool
    async def find_item(self, item: str) -> str:
        """
        Find where an item was last stored.

        Args:
            item: Name of the item to find (e.g., "glasses", "keys")

        Returns:
            Location information or "not found" message
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            result = self.memory_client.find_item(
                user_id=self._user_id,
                item=item,
            )

            if result.get("found"):
                location = result["location"]

                room = result.get("room", "")

                room_part = f" in the {room}" if room else ""

                return f"Your {item} is at {location}{room_part}."
            else:
                return f"I don't have a record of where your {item} is. Would you like me to remember it when you find it?"

        except Exception as e:
            logger.error(f"Error finding item: {e}")

            return f"Sorry, I had trouble looking that up. Error: {str(e)}"

    @function_tool
    async def store_information(self, category: str, key: str, value: str) -> str:
        """
        Store personal information.

        Args:
            category: Type of info (personal/practical/medical/household)
            key: Short identifier (e.g., "doctor_name", "wifi_password")
            value: The actual information to remember

        Returns:
            Confirmation message
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            # Validate category
            valid_categories = ["personal", "practical", "medical", "household"]

            if category not in valid_categories:
                category = "personal"  # Default fallback

            result = self.memory_client.store_information(
                user_id=self._user_id,
                category=category,
                key=key,
                value=value,
            )

            if result.get("success"):
                return f"I've stored that information. I'll remember: {key} = {value}"
            else:
                return f"I had trouble saving that. Error: {result.get('error', 'Unknown')}"

        except Exception as e:
            logger.error(f"Error storing information: {e}")

            return f"Sorry, I couldn't save that information. Error: {str(e)}"

    @function_tool
    async def recall_information(self, key: str) -> str:
        """
        Recall stored personal information.
        Uses exact match first, then semantic search.

        Args:
            key: What to look up (e.g., "doctor", "wifi password", "plumber")

        Returns:
            The stored information or "not found" message
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            result = self.memory_client.recall_information(
                user_id=self._user_id,
                search_key=key,
            )

            if result.get("found"):
                value = result["value"]

                match_type = result.get("match_type", "exact")

                if match_type == "semantic":
                    return f"I found this (based on similar meaning): {value}"
                else:
                    return f"Here's what I have: {value}"
            else:
                return f"I don't have any information stored about '{key}'. Would you like me to remember something?"

        except Exception as e:
            logger.error(f"Error recalling information: {e}")

            return f"Sorry, I had trouble looking that up. Error: {str(e)}"

    @function_tool
    async def log_activity(self, activity_type: str, details: str) -> str:
        """
        Log a daily activity.

        Args:
            activity_type: Type (meal/visitor/outing/activity/conversation)
            details: Description of what happened

        Returns:
            Confirmation message
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            # Validate activity type
            valid_types = ["meal", "visitor", "outing", "activity", "conversation"]

            if activity_type not in valid_types:
                activity_type = "activity"  # Default fallback

            result = self.memory_client.log_activity(
                user_id=self._user_id,
                activity_type=activity_type,
                details={"description": details},
            )

            if result.get("success"):
                return f"I've noted that down: {details}"
            else:
                return f"I had trouble logging that. Error: {result.get('error', 'Unknown')}"

        except Exception as e:
            logger.error(f"Error logging activity: {e}")

            return f"Sorry, I couldn't log that activity. Error: {str(e)}"

    @function_tool
    async def get_daily_context(self, date: Optional[str] = None) -> str:
        """
        Get summary of activities for a specific day.

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Summary of the day's activities
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            activities = self.memory_client.get_daily_context(
                user_id=self._user_id,
                date=date,
            )

            if not activities:  # Check for empty list
                day = date if date else "today"

                return f"I don't have any activities recorded for {day}."

            # Group by activity type
            summary_parts = []

            activity_groups = {}

            for activity in activities:
                act_type = activity["activity_type"]

                if act_type not in activity_groups:
                    activity_groups[act_type] = []

                activity_groups[act_type].append(activity["details"]["description"])

            # Build summary
            for act_type, items in activity_groups.items():
                if len(items) == 1:
                    summary_parts.append(f"{act_type}: {items[0]}")
                else:
                    summary_parts.append(
                        f"{act_type} ({len(items)} times): {', '.join(items[:3])}"
                    )

            day = date if date else "today"

            return f"Here's what happened {day}: " + "; ".join(summary_parts)

        except Exception as e:
            logger.error(f"Error getting daily context: {e}")

            return f"Sorry, I had trouble retrieving that information. Error: {str(e)}"

    @function_tool
    async def what_was_i_doing(self) -> str:
        """
        Get the most recent activity to help user remember what they were doing.

        Returns:
            Description of the last recorded activity
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            activity = self.memory_client.get_recent_activity(user_id=self._user_id)

            if activity is None:  # Explicit None check
                return "I don't have any recent activities recorded. What have you been up to?"

            activity_type = activity["activity_type"]

            details = activity["details"]["description"]

            return f"The last thing I recorded was: {details} (as a {activity_type})"

        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")

            return f"Sorry, I had trouble checking that. Error: {str(e)}"
