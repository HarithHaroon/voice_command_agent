"""
Memory Client - Handles general memory storage for elderly users.
Manages item locations, personal information, and daily activities.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from openai import OpenAI
from dotenv import load_dotenv
from clients.pinecone_client import PineconeClient


load_dotenv(".env.local")
load_dotenv(".env.secrets")

logger = logging.getLogger(__name__)


class MemoryClient:
    """Client for managing elderly user memory across DynamoDB and Pinecone."""

    # Table names
    ITEM_LOCATIONS_TABLE = "memory_item_locations"

    STORED_INFO_TABLE = "memory_stored_information"

    DAILY_CONTEXT_TABLE = "memory_daily_context"

    # Pinecone index
    PINECONE_INDEX_NAME = "elderly-memory"

    def __init__(self, dynamodb_resource=None):
        """Initialize MemoryClient with DynamoDB and Pinecone."""

        # DynamoDB setup
        if dynamodb_resource is None:
            self.dynamodb = boto3.resource(
                "dynamodb",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
        else:
            self.dynamodb = dynamodb_resource

        self.item_table = self.dynamodb.Table(self.ITEM_LOCATIONS_TABLE)

        self.info_table = self.dynamodb.Table(self.STORED_INFO_TABLE)

        self.context_table = self.dynamodb.Table(self.DAILY_CONTEXT_TABLE)

        self.pinecone_client = PineconeClient()

        logger.info("MemoryClient initialized with DynamoDB and Pinecone")

    def _get_today_date(self) -> str:
        """Get today's date in YYYY-MM-DD format."""
        return datetime.now().strftime("%Y-%m-%d")

    def store_item_location(
        self, user_id: str, item: str, location: str, room: str
    ) -> Dict[str, Any]:
        """Store where user put an item."""
        try:
            item_lower = item.lower().strip()

            timestamp = datetime.now().isoformat()

            self.item_table.put_item(
                Item={
                    "user_id": user_id,
                    "item_name": item_lower,
                    "location": location,
                    "room": room,
                    "stored_at": timestamp,
                    "source": "user_reported",
                }
            )

            logger.info(f"Stored location for '{item}': {location} ({room})")

            return {
                "success": True,
                "item": item,
                "location": location,
                "room": room,
            }
        except ClientError as e:
            logger.error(f"Failed to store item location: {e}")

            return {"success": False, "error": str(e)}

    def find_item(self, user_id: str, item: str) -> Optional[Dict[str, Any]]:
        """Find where an item was last stored."""
        try:
            item_lower = item.lower().strip()

            response = self.item_table.get_item(
                Key={"user_id": user_id, "item_name": item_lower}
            )

            if "Item" in response:
                item_data = response["Item"]

                logger.info(f"Found '{item}' at {item_data['location']}")

                return {
                    "found": True,
                    "item": item,
                    "location": item_data["location"],
                    "room": item_data["room"],
                    "stored_at": item_data["stored_at"],
                }
            else:
                logger.info(f"Item '{item}' not found in memory")

                return {"found": False, "item": item}

        except ClientError as e:
            logger.error(f"Failed to find item: {e}")

            return {"found": False, "error": str(e)}

    def store_information(
        self, user_id: str, category: str, key: str, value: str
    ) -> Dict[str, Any]:
        """Store personal information with Pinecone indexing."""
        try:
            key_lower = key.lower().strip()
            timestamp = datetime.now().isoformat()

            # Store in DynamoDB
            self.info_table.put_item(
                Item={
                    "user_id": user_id,
                    "key": key_lower,
                    "category": category,
                    "value": value,
                    "created_at": timestamp,
                    "last_accessed": timestamp,
                    "access_count": 0,
                }
            )

            # Generate embedding and store in Pinecone - USE NEW CLIENT
            embedding_text = f"{key}: {value}"
            embedding = self.pinecone_client.generate_embedding(embedding_text)

            vector_id = f"{user_id}_{key_lower}"

            self.pinecone_client.upsert(
                index_name=self.PINECONE_INDEX_NAME,
                vectors=[
                    (
                        vector_id,
                        embedding,
                        {
                            "user_id": user_id,
                            "key": key_lower,
                            "category": category,
                            "value": value,
                        },
                    )
                ],
                namespace=None,  # Not using namespaces for memory
            )

            logger.info(f"Stored information: {key} = {value} (category: {category})")
            return {"success": True, "key": key, "value": value, "category": category}

        except Exception as e:
            logger.error(f"Failed to store information: {e}")
            return {"success": False, "error": str(e)}

    def recall_information(
        self, user_id: str, search_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Recall stored information.
        First tries exact match, then semantic search via Pinecone.
        """
        try:
            key_lower = search_key.lower().strip()

            # Step 1: Try exact match in DynamoDB
            response = self.info_table.get_item(
                Key={"user_id": user_id, "key": key_lower}
            )

            if "Item" in response:
                item = response["Item"]

                # Update access tracking
                self.info_table.update_item(
                    Key={"user_id": user_id, "key": key_lower},
                    UpdateExpression="SET last_accessed = :t, access_count = access_count + :inc",
                    ExpressionAttributeValues={
                        ":t": datetime.now().isoformat(),
                        ":inc": 1,
                    },
                )

                logger.info(f"Found exact match for '{search_key}': {item['value']}")

                return {
                    "found": True,
                    "match_type": "exact",
                    "key": item["key"],
                    "value": item["value"],
                    "category": item["category"],
                }

            # Step 2: Semantic search via Pinecone - USE NEW CLIENT
            logger.info(f"No exact match, trying semantic search for '{search_key}'")

            query_embedding = self.pinecone_client.generate_embedding(search_key)

            results = self.pinecone_client.query(
                index_name=self.PINECONE_INDEX_NAME,
                vector=query_embedding,
                top_k=1,
                filter={"user_id": {"$eq": user_id}},
                include_metadata=True,
            )

            if results.get("matches") and len(results["matches"]) > 0:
                best_match = results["matches"][0]

                score = best_match["score"]

                if score > 0.7:
                    metadata = best_match["metadata"]

                    logger.info(
                        f"Semantic match for '{search_key}': {metadata['value']} (score: {score:.2f})"
                    )

                    return {
                        "found": True,
                        "match_type": "semantic",
                        "key": metadata["key"],
                        "value": metadata["value"],
                        "category": metadata["category"],
                        "confidence": score,
                    }

            logger.info(f"No information found for '{search_key}'")

            return {"found": False, "search_key": search_key}

        except Exception as e:
            logger.error(f"Failed to recall information: {e}")

            return {"found": False, "error": str(e)}

    def log_activity(
        self, user_id: str, activity_type: str, details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log a daily activity."""
        try:
            timestamp = datetime.now().isoformat()

            date = self._get_today_date()

            self.context_table.put_item(
                Item={
                    "user_id": user_id,
                    "timestamp": timestamp,
                    "activity_type": activity_type,
                    "details": json.dumps(details),
                    "date": date,
                }
            )

            logger.info(f"Logged activity: {activity_type} - {details}")

            return {
                "success": True,
                "activity_type": activity_type,
                "timestamp": timestamp,
            }

        except ClientError as e:
            logger.error(f"Failed to log activity: {e}")

            return {"success": False, "error": str(e)}

    def get_daily_context(
        self, user_id: str, date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all activities for a specific date (defaults to today)."""
        try:
            target_date = date if date else self._get_today_date()

            response = self.context_table.query(
                IndexName="user_date_index",
                KeyConditionExpression=Key("user_id").eq(user_id)
                & Key("date").eq(target_date),
            )

            activities = []
            for item in response.get("Items", []):
                activities.append(
                    {
                        "timestamp": item["timestamp"],
                        "activity_type": item["activity_type"],
                        "details": json.loads(item["details"]),
                    }
                )

            logger.info(f"Retrieved {len(activities)} activities for {target_date}")

            return activities

        except ClientError as e:

            logger.error(f"Failed to get daily context: {e}")

            return []

    def get_recent_activity(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent activity for 'what was I doing' queries."""
        try:
            response = self.context_table.query(
                KeyConditionExpression=Key("user_id").eq(user_id),
                ScanIndexForward=False,  # Descending order
                Limit=1,
            )

            items = response.get("Items", [])

            if items:
                item = items[0]

                logger.info(f"Recent activity: {item['activity_type']}")

                return {
                    "timestamp": item["timestamp"],
                    "activity_type": item["activity_type"],
                    "details": json.loads(item["details"]),
                }
            else:
                logger.info("No recent activities found")

                return None

        except ClientError as e:
            logger.error(f"Failed to get recent activity: {e}")

            return None
