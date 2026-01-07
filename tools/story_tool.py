"""
Story Tools - Server-side tools for life story management.
Handles story recording, retrieval, and organization.
"""

import logging
from typing import List, Optional
from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from clients.story_client import StoryClient

logger = logging.getLogger(__name__)


class StoryTool(ServerSideTool):
    """Server-side tool for managing elderly user life stories."""

    def __init__(self, story_client: StoryClient):
        super().__init__("story")

        self.story_client = story_client

        self._user_id = None

        logger.info("StoryTool initialized")

    def set_user_id(self, user_id: str):
        """Set the user ID for all story operations."""
        self._user_id = user_id

        logger.info(f"StoryTool user_id set to: {user_id}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return [
            "record_story",
            "find_stories",
            "get_story",
            "list_my_stories",
            "get_story_summary",
        ]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [
            self.record_story,
            self.find_stories,
            self.get_story,
            self.list_my_stories,
            self.get_story_summary,
        ]

    @function_tool
    async def record_story(
        self,
        title: str,
        content: str,
        life_stage: str,
        themes: Optional[str] = "",
        people_mentioned: Optional[str] = "",
        location: str = "",
        time_period: str = "",
    ) -> str:
        """
        Record a new life story.

        Args:
            title: Story title
            content: Full story transcript
            life_stage: Life stage (e.g., "childhood", "young_adult", "family", "career", "retirement", "special_moments")
            themes: Comma-separated themes (e.g., "holidays,family,travel")
            people_mentioned: Comma-separated names (e.g., "Sarah,John,Mom")
            location: Location mentioned (optional)
            time_period: Time period (e.g., "1950s", "summer of 1985")

        Returns:
            Confirmation message
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            # Parse comma-separated strings into lists
            themes_list = (
                [t.strip() for t in themes.split(",") if t.strip()] if themes else []
            )

            people_list = (
                [p.strip() for p in people_mentioned.split(",") if p.strip()]
                if people_mentioned
                else []
            )

            result = await self.story_client.store_story(
                user_id=self._user_id,
                title=title,
                content=content,
                life_stage=life_stage,
                themes=themes_list,
                people_mentioned=people_list,
                location=location,
                time_period=time_period,
            )

            if result.get("success"):
                return f"I've saved your story '{title}'. What a beautiful memory to preserve!"
            else:
                return f"I had trouble saving that story. Error: {result.get('error', 'Unknown')}"

        except Exception as e:
            logger.error(f"Error recording story: {e}")

            return f"Sorry, I couldn't save that story. Error: {str(e)}"

    @function_tool
    async def find_stories(self, query: str, limit: int = 5) -> str:
        """
        Find stories using natural language search.

        Args:
            query: Search query (e.g., "stories about my childhood", "when I met my wife")
            limit: Maximum number of stories to return (default: 5)

        Returns:
            List of matching stories
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            stories = await self.story_client.find_stories_semantic(
                user_id=self._user_id,
                query=query,
                top_k=limit,
            )

            if not stories:
                return f"I couldn't find any stories matching '{query}'. Would you like to record a new story?"

            # Format results
            result_parts = [f"I found {len(stories)} stories:"]

            for i, story in enumerate(stories, 1):
                relevance = story.get("relevance_score", 0)
                result_parts.append(
                    f"{i}. {story['title']} ({story['life_stage']}) - Relevance: {relevance:.0%}"
                )

            result_parts.append(
                "\nWould you like me to read any of these stories to you?"
            )

            return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error finding stories: {e}")

            return f"Sorry, I had trouble searching for stories. Error: {str(e)}"

    @function_tool
    async def get_story(self, story_title: str) -> str:
        """
        Retrieve and read a specific story by title.

        Args:
            story_title: The title of the story to retrieve

        Returns:
            The full story content
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            # Search for the story by title
            stories = await self.story_client.find_stories_semantic(
                user_id=self._user_id,
                query=story_title,
                top_k=1,
            )

            if not stories:
                return f"I couldn't find a story titled '{story_title}'. Would you like to see all your stories?"

            story = stories[0]

            # Format the story for reading
            response_parts = [
                f"Here's your story: {story['title']}",
                f"Life stage: {story['life_stage']}",
                f"Recorded on: {story['recorded_at'][:10]}",
                "",
                story["content"],
            ]

            if story.get("people_mentioned"):
                response_parts.append(
                    f"\nPeople mentioned: {', '.join(story['people_mentioned'])}"
                )

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"Error retrieving story: {e}")

            return f"Sorry, I had trouble retrieving that story. Error: {str(e)}"

    @function_tool
    async def list_my_stories(
        self, life_stage: Optional[str] = "", limit: int = 10
    ) -> str:
        """
        List your recorded stories.

        Args:
            life_stage: Filter by life stage (e.g., "childhood", "family")
            limit: Maximum number of stories to list (default: 10)

        Returns:
            List of stories
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            filters = {"limit": limit}

            if life_stage:
                filters["life_stage"] = life_stage

            stories = self.story_client.list_stories(
                user_id=self._user_id,
                filters=filters,
            )

            if not stories:
                if life_stage:
                    return f"You haven't recorded any {life_stage} stories yet. Would you like to record one now?"

                return "You haven't recorded any stories yet. Would you like to start?"

            # Format results
            filter_text = f" from your {life_stage}" if life_stage else ""

            result_parts = [f"Here are your stories{filter_text}:"]

            for i, story in enumerate(stories, 1):
                themes_text = (
                    f" ({', '.join(story['themes'])})" if story.get("themes") else ""
                )

                result_parts.append(
                    f"{i}. {story['title']} - {story['life_stage']}{themes_text}"
                )

            result_parts.append(
                f"\nTotal: {len(stories)} stories. Would you like to hear any of these?"
            )

            return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error listing stories: {e}")

            return f"Sorry, I had trouble listing your stories. Error: {str(e)}"

    @function_tool
    async def get_story_summary(self) -> str:
        """
        Get a summary of all your recorded stories.

        Returns:
            Summary statistics
        """
        if not self._user_id:
            return "Error: User ID not set"

        try:
            summary = self.story_client.get_story_summary(user_id=self._user_id)

            if summary.get("total_stories", 0) == 0:
                return "You haven't recorded any stories yet. Would you like to start preserving your memories?"

            # Format summary
            result_parts = [
                f"You've recorded {summary['total_stories']} stories totaling {summary['total_words']} words!",
                "\nStories by life stage:",
            ]

            for stage, count in summary.get("by_life_stage", {}).items():
                result_parts.append(f"  - {stage}: {count} stories")

            if summary.get("most_recent_story"):
                recent = summary["most_recent_story"]

                result_parts.append(
                    f"\nMost recent: '{recent['title']}' recorded on {recent['recorded_at'][:10]}"
                )

            return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Error getting summary: {e}")

            return f"Sorry, I had trouble getting your story summary. Error: {str(e)}"
