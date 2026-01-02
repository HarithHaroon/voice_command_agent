import os
import logging
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from firebase_admin import credentials, firestore
import firebase_admin

logger = logging.getLogger(__name__)


class FirebaseClient:
    """Service class for handling Firebase Firestore operations for Nova Sonic chat history."""

    def __init__(self, credentials_path=None):
        """Initialize Firebase with the provided credentials."""
        # Initialize Firebase only if it hasn't been initialized yet
        if not firebase_admin._apps:
            # Try to get credentials from environment variable (JSON string)
            credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

            if credentials_json:
                # Parse JSON string and use it as credentials
                try:
                    cred_dict = json.loads(credentials_json)
                    cred = credentials.Certificate(cred_dict)
                    logger.info(
                        "Using Firebase credentials from FIREBASE_CREDENTIALS_JSON"
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse FIREBASE_CREDENTIALS_JSON: {e}")
                    raise
            else:
                # Fall back to file path
                credentials_path = os.getenv(
                    "FIREBASE_CREDENTIALS_PATH", "./sidekick_firebase_adminsdk.json"
                )
                cred = credentials.Certificate(credentials_path)
                logger.info(f"Using Firebase credentials from file: {credentials_path}")

            firebase_admin.initialize_app(cred)

        self.db = firestore.client()
        logger.info("Firebase initialized successfully")

    def add_message(self, user_id: str, role: str, content: str) -> bool:
        """Add a message to Firestore"""
        try:
            message_data = {
                "userId": user_id,
                "role": role.upper(),
                "content": content,
                "timestamp": firestore.SERVER_TIMESTAMP,
            }

            # Log what we're about to save
            # logger.info(
            #     f"Saving to Firestore - User: {user_id}, Role: {role.upper()}, Content: {content[:100]}..."
            #     if len(content) > 100
            #     else f"Saving to Firestore - User: {user_id}, Role: {role.upper()}, Content: {content}"
            # )

            # Add to messages collection
            doc_ref = self.db.collection("messages").add(message_data)

            # logger.info(
            #     f"Successfully saved message to Firestore with ID: {doc_ref[1].id}, Role: {role.upper()}"
            # )

            return True

        except Exception as e:
            logger.error(f"Error adding message to Firestore: {e}")
            return False

    async def get_history(self, user_id: str, limit: int = 50):
        """Get recent chat history for a user"""
        try:
            # ✅ Order and limit on server-side
            messages_ref = (
                self.db.collection("messages")
                .where(filter=firestore.FieldFilter("userId", "==", user_id))
                .order_by(
                    "timestamp", direction=firestore.Query.DESCENDING
                )  # Newest first
                .limit(limit)
            )

            docs = await asyncio.to_thread(lambda: list(messages_ref.stream()))

            messages = []
            for doc in docs:
                data = doc.to_dict()
                messages.append(
                    {
                        "role": data["role"],
                        "content": data["content"],
                    }
                )

            # Reverse to chronological order (oldest first)
            messages.reverse()

            logger.info(f"Retrieved {len(messages)} messages for user {user_id}")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving history from Firestore: {e}")
            return []

    async def get_messages_by_timeframe(self, user_id: str, hours: int = 24):
        """Get messages within a specific timeframe"""
        try:
            from datetime import datetime, timedelta, timezone

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # ✅ Filter on Firestore server, not in Python
            messages_ref = (
                self.db.collection("messages")
                .where(filter=firestore.FieldFilter("userId", "==", user_id))
                .where(filter=firestore.FieldFilter("timestamp", ">=", cutoff_time))
                .order_by("timestamp")  # Sort server-side
                .limit(100)  # Reasonable limit
            )

            docs = await asyncio.to_thread(lambda: list(messages_ref.stream()))

            messages = []
            for doc in docs:
                data = doc.to_dict()
                messages.append(
                    {
                        "role": data["role"],
                        "content": data["content"],
                        "timestamp": data.get("timestamp"),
                    }
                )

            logger.info(
                f"Retrieved {len(messages)} messages for user {user_id} in last {hours} hours"
            )
            return messages

        except Exception as e:
            logger.error(f"Error retrieving messages by timeframe: {e}")
            return []

    async def delete_user_history(self, user_id: str) -> bool:
        """Delete all messages for a user (for testing/cleanup)"""
        try:
            messages_ref = self.db.collection("messages").where(
                filter=firestore.FieldFilter("userId", "==", user_id)
            )

            # Wrap blocking stream() call in asyncio.to_thread to avoid blocking event loop
            docs = await asyncio.to_thread(lambda: list(messages_ref.stream()))

            deleted_count = 0
            for doc in docs:
                # Wrap blocking delete() call
                await asyncio.to_thread(doc.reference.delete)
                deleted_count += 1

            logger.info(f"Deleted {deleted_count} messages for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting user history: {e}")
            return False
