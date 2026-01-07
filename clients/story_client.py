"""
Story Client - Handles elderly life story storage and retrieval.
Uses DynamoDB for structured data and Pinecone for semantic search.
"""

import logging
import uuid
import boto3
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Any, Optional
from clients.pinecone_client import PineconeClient

load_dotenv(".env.local")
load_dotenv(".env.secrets")

logger = logging.getLogger(__name__)


class StoryClient:
    """Client for managing elderly life stories"""

    def __init__(self):
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        self.table = self.dynamodb.Table("elderly_stories")

        self.pinecone_client = PineconeClient()

        logger.info("StoryClient initialized with DynamoDB and Pinecone")

    async def store_story(
        self,
        user_id: str,
        title: str,
        content: str,
        life_stage: str,
        themes: Optional[List[str]] = None,
        people_mentioned: Optional[List[str]] = None,
        location: str = "",
        time_period: str = "",
    ) -> Dict[str, Any]:
        """
        Store a new story in DynamoDB and Pinecone.
        """
        try:
            # Handle empty lists
            themes = themes or []

            people_mentioned = people_mentioned or []

            # Generate story ID with timestamp prefix for chronological sorting
            timestamp = datetime.utcnow().isoformat()

            story_id = f"{timestamp}_{uuid.uuid4()}"

            # Calculate word count
            word_count = len(content.split())

            # Store in DynamoDB
            item = {
                "user_id": user_id,
                "story_id": story_id,
                "title": title,
                "content": content,
                "life_stage": life_stage,
                "themes": themes,
                "people_mentioned": people_mentioned,
                "location": location,
                "time_period": time_period,
                "recorded_at": timestamp,
                "word_count": word_count,
            }

            self.table.put_item(Item=item)

            logger.info(f"Stored story {story_id} for user {user_id} in DynamoDB")

            # Generate embedding for Pinecone
            embed_text = self._prepare_embedding_text(
                title, content, themes, people_mentioned
            )

            embedding = self.pinecone_client.generate_embedding(embed_text)

            # Store in Pinecone
            metadata = {
                "story_id": story_id,
                "user_id": user_id,
                "title": title,
                "life_stage": life_stage,
                "themes": ",".join(themes) if themes else "",
                "recorded_at": timestamp,
            }

            self.pinecone_client.upsert(
                index_name="elderly-stories",
                vectors=[(story_id, embedding, metadata)],
                namespace=user_id,
            )

            logger.info(f"Stored story {story_id} embedding in Pinecone")

            return {
                "success": True,
                "story_id": story_id,
                "message": f"Story '{title}' saved successfully",
            }

        except Exception as e:
            logger.error(f"Error storing story: {e}", exc_info=True)

            return {"success": False, "error": str(e)}

    async def find_stories_semantic(
        self, user_id: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find stories using semantic search via Pinecone.
        """
        try:
            # Generate query embedding
            query_embedding = self.pinecone_client.generate_embedding(query)

            # Search Pinecone
            results = self.pinecone_client.query(
                index_name="elderly-stories",
                vector=query_embedding,
                top_k=top_k,
                namespace=user_id,
                include_metadata=True,
            )

            if not results or not results.get("matches"):
                logger.info(f"No semantic matches found for query: {query}")

                return []

            # Fetch full stories from DynamoDB
            stories = []

            for match in results["matches"]:
                story_id = match["id"]

                score = match.get("score", 0)

                story = self.get_story_by_id(user_id, story_id)

                if story:
                    story["relevance_score"] = score
                    stories.append(story)

            logger.info(f"Found {len(stories)} semantic matches for: {query}")

            return stories

        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)

            return []

    def get_story_by_id(self, user_id: str, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific story by ID.
        """
        try:
            response = self.table.get_item(
                Key={"user_id": user_id, "story_id": story_id}
            )

            if "Item" in response:
                logger.info(f"Retrieved story {story_id}")

                return response["Item"]
            else:
                logger.info(f"Story {story_id} not found")

                return None

        except Exception as e:
            logger.error(f"Error retrieving story: {e}", exc_info=True)

            return None

    def list_stories(
        self, user_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List stories with optional filters.
        """
        try:
            filters = filters or {}

            # Filter by life_stage using GSI
            if "life_stage" in filters:
                response = self.table.query(
                    IndexName="user_life_stage_index",
                    KeyConditionExpression="user_id = :uid AND life_stage = :stage",
                    ExpressionAttributeValues={
                        ":uid": user_id,
                        ":stage": filters["life_stage"],
                    },
                )
            else:
                # Get all stories for user
                response = self.table.query(
                    KeyConditionExpression="user_id = :uid",
                    ExpressionAttributeValues={":uid": user_id},
                    ScanIndexForward=False,  # Most recent first
                )

            stories = response.get("Items", [])

            # Apply limit if specified
            if "limit" in filters and filters["limit"]:
                stories = stories[: filters["limit"]]

            logger.info(f"Listed {len(stories)} stories for user {user_id}")

            return stories

        except Exception as e:
            logger.error(f"Error listing stories: {e}", exc_info=True)

            return []

    def get_story_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get summary statistics about user's stories.
        """
        try:
            # Get all stories
            response = self.table.query(
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id},
            )

            stories = response.get("Items", [])

            if not stories:
                return {
                    "total_stories": 0,
                    "message": "No stories recorded yet",
                }

            # Calculate statistics
            total = len(stories)

            # Count by life_stage
            by_life_stage = {}

            total_words = 0

            for story in stories:
                stage = story.get("life_stage", "unknown")
                by_life_stage[stage] = by_life_stage.get(stage, 0) + 1
                total_words += story.get("word_count", 0)

            # Get most recent story
            most_recent = stories[0] if stories else None

            summary = {
                "total_stories": total,
                "by_life_stage": by_life_stage,
                "total_words": total_words,
                "most_recent_story": (
                    {
                        "title": most_recent.get("title"),
                        "recorded_at": most_recent.get("recorded_at"),
                    }
                    if most_recent
                    else None
                ),
            }

            logger.info(f"Generated summary for user {user_id}: {total} stories")

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)

            return {"total_stories": 0, "error": str(e)}

    def _prepare_embedding_text(
        self,
        title: str,
        content: str,
        themes: List[str],
        people_mentioned: List[str],
    ) -> str:
        """Prepare text for embedding by concatenating relevant fields"""
        parts = [title, content]

        if themes:
            parts.append(" ".join(themes))

        if people_mentioned:
            parts.append(" ".join(people_mentioned))

        return " ".join(parts)
