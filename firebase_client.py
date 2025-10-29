import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from firebase_admin import credentials, firestore
import firebase_admin

logger = logging.getLogger(__name__)

class FirebaseClient:
    """Service class for handling Firebase Firestore operations for Nova Sonic chat history."""

    def __init__(self, credentials_path="../sidekick_firebase_adminsdk.json"):
        """Initialize Firebase with the provided credentials."""
        # Initialize Firebase only if it hasn't been initialized yet
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        logger.info("Firebase initialized successfully")
    
    def add_message(self, user_id: str, role: str, content: str) -> bool:
        """Add a message to Firestore"""
        try:
            message_data = {
                'userId': user_id,
                'role': role.upper(),
                'content': content,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            
            # Log what we're about to save
            logger.info(f"Saving to Firestore - User: {user_id}, Role: {role.upper()}, Content: {content[:100]}..." if len(content) > 100 else f"Saving to Firestore - User: {user_id}, Role: {role.upper()}, Content: {content}")
            
            # Add to messages collection
            doc_ref = self.db.collection('messages').add(message_data)
            logger.info(f"Successfully saved message to Firestore with ID: {doc_ref[1].id}, Role: {role.upper()}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message to Firestore: {e}")
            return False
    
    async def get_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chat history for a user"""
        try:
            # First, get all messages for the user (without ordering by timestamp to avoid index requirement)
            messages_ref = self.db.collection('messages').where(filter=firestore.FieldFilter('userId', '==', user_id))

            # Wrap blocking stream() call in asyncio.to_thread to avoid blocking event loop
            docs = await asyncio.to_thread(lambda: list(messages_ref.stream()))

            messages = []
            for doc in docs:
                data = doc.to_dict()
                # Convert to format expected by Nova Sonic and include timestamp for sorting
                messages.append({
                    'role': data['role'],
                    'content': data['content'],
                    'timestamp': data.get('timestamp')
                })

            # Sort by timestamp in Python (newest first, then reverse for chronological order)
            messages.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=True)

            # Limit the results and remove timestamp from final output
            limited_messages = []
            for msg in messages[:limit]:
                limited_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

            # Reverse to get chronological order (oldest first)
            limited_messages.reverse()

            logger.info(f"Retrieved {len(limited_messages)} messages for user {user_id}")
            return limited_messages

        except Exception as e:
            logger.error(f"Error retrieving history from Firestore: {e}")
            return []
    
    async def get_messages_by_timeframe(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get messages within a specific timeframe"""
        try:
            from datetime import datetime, timedelta

            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Get all messages for user and filter by time in Python to avoid index requirements
            messages_ref = self.db.collection('messages').where(filter=firestore.FieldFilter('userId', '==', user_id))

            # Wrap blocking stream() call in asyncio.to_thread to avoid blocking event loop
            docs = await asyncio.to_thread(lambda: list(messages_ref.stream()))

            messages = []
            for doc in docs:
                data = doc.to_dict()
                msg_timestamp = data.get('timestamp')

                # Filter by timeframe in Python
                if msg_timestamp and msg_timestamp >= cutoff_time:
                    messages.append({
                        'role': data['role'],
                        'content': data['content'],
                        'timestamp': msg_timestamp
                    })

            # Sort by timestamp
            messages.sort(key=lambda x: x.get('timestamp') or datetime.min)

            logger.info(f"Retrieved {len(messages)} messages for user {user_id} in last {hours} hours")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving messages by timeframe: {e}")
            return []
    
    async def delete_user_history(self, user_id: str) -> bool:
        """Delete all messages for a user (for testing/cleanup)"""
        try:
            messages_ref = self.db.collection('messages').where(filter=firestore.FieldFilter('userId', '==', user_id))

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

# Global instance - Initialize with credentials file in root directory
firebase_client = FirebaseClient("../sidekick_firebase_adminsdk.json")