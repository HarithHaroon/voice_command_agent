import os
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from embedding_service import embedding_service

load_dotenv()

logger = logging.getLogger(__name__)

class PineconeClient:
    def __init__(self):
        self.pc = None
        self.index = None
        # Allow index name to be configured via environment variable
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'nova-sonic-history')
        self._initialize_pinecone()

    def _initialize_pinecone(self):
        """Initialize Pinecone client and index"""
        try:
            api_key = os.getenv('PINECONE_API_KEY')
            if not api_key:
                raise ValueError("PINECONE_API_KEY environment variable not set")

            # Add timeout to prevent indefinite hangs (30 seconds)
            self.pc = Pinecone(api_key=api_key)

            # Check if index exists
            existing_indexes = [index.name for index in self.pc.list_indexes()]

            if self.index_name not in existing_indexes:
                logger.warning(f"Pinecone index '{self.index_name}' not found. Available indexes: {existing_indexes}")
                logger.info("Please create the index manually or use an existing one.")
                # Don't create, just log available indexes
                if existing_indexes:
                    logger.info(f"Using first available index: {existing_indexes[0]}")
                    self.index_name = existing_indexes[0]
                else:
                    raise ValueError("No Pinecone indexes available. Please create one manually.")

            # Create index connection with timeout configuration
            # Note: Pinecone SDK v3+ uses connection pooling internally with default timeouts
            # We rely on the SDK's built-in timeout handling (default: 30s for most operations)
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Pinecone initialized successfully with index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
    
    def _generate_vector_id(self, user_id: str, role: str, content: str, timestamp: str) -> str:
        """Generate a unique ID for the vector"""
        unique_string = f"{user_id}_{role}_{content[:50]}_{timestamp}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    

    async def upsert_message(self, user_id: str, role: str, content: str) -> bool:
        """Create embedding and store message in Pinecone (async)"""
        try:
            # Filter out short messages
            if len(content.strip()) <= 20:
                logger.debug(f"Skipping short message: {content[:20]}...")
                return True
            
            # Filter out common short responses
            short_responses = {'ok', 'thanks', 'thank you', 'yes', 'no', 'sure', 'alright', 'got it'}
            if content.lower().strip() in short_responses:
                logger.debug(f"Skipping common short response: {content}")
                return True
            
            # Generate embedding asynchronously
            embedding = await embedding_service.create_embedding_async(content)
            if not embedding:
                logger.error("Failed to create embedding")
                return False
            
            # Create unique ID
            timestamp = datetime.now().isoformat()
            vector_id = self._generate_vector_id(user_id, role, content, timestamp)
            
            # Prepare metadata
            metadata = {
                'userId': user_id,
                'role': role.upper(),
                'content': content,
                'timestamp': timestamp,
                'content_length': len(content)
            }
            
            # Upsert to Pinecone asynchronously
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: self.index.upsert(
                    vectors=[{
                        'id': vector_id,
                        'values': embedding,
                        'metadata': metadata
                    }]
                )
            )
            
            logger.debug(f"Message upserted to Pinecone: {vector_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error upserting message to Pinecone: {e}")
            return False
    
    async def search_similar_messages(self, user_id: str, query: str, top_k: int = 10, timeframe_hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for similar messages using vector similarity (async)"""
        try:
            # Generate embedding for query asynchronously
            query_embedding = await embedding_service.create_embedding_async(query)
            if not query_embedding:
                logger.error("Failed to create query embedding")
                return []
            
            # Prepare filter
            filter_dict = {'userId': user_id}
            
            # Add timeframe filter if specified
            if timeframe_hours:
                from datetime import datetime, timedelta
                cutoff_time = (datetime.now() - timedelta(hours=timeframe_hours)).isoformat()
                filter_dict['timestamp'] = {'$gte': cutoff_time}
            
            # Search in Pinecone asynchronously
            import asyncio
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                None,
                lambda: self.index.query(
                    vector=query_embedding,
                    filter=filter_dict,
                    top_k=top_k,
                    include_metadata=True
                )
            )
            
            # Format results
            results = []
            for match in search_results.matches:
                if match.score > 0.7:  # Only return high similarity matches
                    metadata = match.metadata
                    results.append({
                        'role': metadata['role'],
                        'content': metadata['content'],
                        'timestamp': metadata['timestamp'],
                        'similarity_score': match.score
                    })
            
            logger.info(f"Found {len(results)} similar messages for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching Pinecone: {e}")
            return []
    
    def get_recent_vectors(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent vectors for a user (for testing/debugging)"""
        try:
            # Note: Pinecone doesn't have a direct "get recent" function
            # This is a workaround using a broad query
            dummy_query = embedding_service.create_embedding("recent messages")
            if not dummy_query:
                return []
            
            search_results = self.index.query(
                vector=dummy_query,
                filter={'userId': user_id},
                top_k=limit,
                include_metadata=True
            )
            
            results = []
            for match in search_results.matches:
                metadata = match.metadata
                results.append({
                    'role': metadata['role'],
                    'content': metadata['content'],
                    'timestamp': metadata['timestamp']
                })
            
            # Sort by timestamp
            results.sort(key=lambda x: x['timestamp'], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error getting recent vectors: {e}")
            return []
    
    def delete_user_vectors(self, user_id: str) -> bool:
        """Delete all vectors for a user (for testing/cleanup)"""
        try:
            # Get all vector IDs for the user
            dummy_query = embedding_service.create_embedding("delete user")
            if not dummy_query:
                return False
            
            search_results = self.index.query(
                vector=dummy_query,
                filter={'userId': user_id},
                top_k=10000,  # Large number to get all
                include_metadata=False
            )
            
            # Extract IDs
            vector_ids = [match.id for match in search_results.matches]
            
            if vector_ids:
                self.index.delete(ids=vector_ids)
                logger.info(f"Deleted {len(vector_ids)} vectors for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user vectors: {e}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            stats = self.index.describe_index_stats()
            return {
                'total_vector_count': stats.total_vector_count,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}

# Global instance - Initialize with error handling
try:
    pinecone_client = PineconeClient()
except Exception as e:
    logger.error(f"Failed to initialize Pinecone client: {e}")
    logger.warning("Continuing without Pinecone - vector search will not be available")
    pinecone_client = None