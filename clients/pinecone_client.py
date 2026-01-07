"""
Pinecone Client - Reusable wrapper for Pinecone operations.
Used by MemoryClient and StoryClient for vector storage and semantic search.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env.secrets")

logger = logging.getLogger(__name__)


class PineconeClient:
    """Reusable client for Pinecone vector operations"""

    EMBEDDING_MODEL = "text-embedding-3-small"

    EMBEDDING_DIMENSION = 1536

    def __init__(self):
        """Initialize Pinecone and OpenAI clients"""
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        logger.info("PineconeClient initialized")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL, input=text
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")

            raise

    def upsert(
        self, index_name: str, vectors: List[tuple], namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert vectors to Pinecone index.

        Args:
            index_name: Name of the Pinecone index
            vectors: List of (id, values, metadata) tuples
            namespace: Optional namespace for isolation

        Returns:
            Upsert response
        """
        try:
            index = self.pc.Index(index_name)

            # Format vectors for Pinecone
            formatted_vectors = [
                {
                    "id": vec[0],
                    "values": vec[1],
                    "metadata": vec[2] if len(vec) > 2 else {},
                }
                for vec in vectors
            ]

            index.upsert(vectors=formatted_vectors, namespace=namespace or "")

            logger.info(f"Upserted {len(vectors)} vectors to {index_name}")

            return {"success": True, "upserted_count": len(vectors)}

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")

            return {"success": False, "error": str(e)}

    def query(
        self,
        index_name: str,
        vector: List[float],
        top_k: int = 5,
        filter: Optional[Dict] = None,
        namespace: Optional[str] = None,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Query Pinecone index for similar vectors.

        Args:
            index_name: Name of the Pinecone index
            vector: Query vector
            top_k: Number of results to return
            filter: Metadata filter
            namespace: Optional namespace
            include_metadata: Whether to include metadata in results

        Returns:
            Query results with matches
        """
        try:
            index = self.pc.Index(index_name)

            results = index.query(
                vector=vector,
                top_k=top_k,
                filter=filter,
                namespace=namespace or "",
                include_metadata=include_metadata,
            )

            logger.info(f"Query returned {len(results.get('matches', []))} results")

            return results

        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")

            return {"matches": []}

    def delete(
        self, index_name: str, ids: List[str], namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete vectors from Pinecone index.

        Args:
            index_name: Name of the Pinecone index
            ids: List of vector IDs to delete
            namespace: Optional namespace

        Returns:
            Delete response
        """
        try:
            index = self.pc.Index(index_name)

            index.delete(ids=ids, namespace=namespace or "")

            logger.info(f"Deleted {len(ids)} vectors from {index_name}")

            return {"success": True, "deleted_count": len(ids)}

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")

            return {"success": False, "error": str(e)}
