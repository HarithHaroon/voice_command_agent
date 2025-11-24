from typing import List, Optional, Union, Dict, Any
import time
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import Pinecone


# Configuration
INDEX_NAME = "sidekick-images"

# Singleton instances to avoid repeated initializations
_embeddings = None
_pinecone_client = None
_pinecone_index = None
_vectorstore = None


def get_embeddings():
    """Get or initialize the OpenAI embeddings instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            chunk_size=1000,
        )
    return _embeddings


def get_pinecone_client():
    """Get or initialize the Pinecone client."""
    global _pinecone_client
    if _pinecone_client is None:
        _pinecone_client = Pinecone(
            embedding=get_embeddings(),
            index_name=INDEX_NAME,
        )
    return _pinecone_client


def get_pinecone_index():
    """Get or initialize the Pinecone index."""
    global _pinecone_index
    if _pinecone_index is None:
        pc = get_pinecone_client()
        _pinecone_index = pc.Index(INDEX_NAME)
    return _pinecone_index


def get_vectorstore():
    """Get or initialize the Pinecone vector store."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Pinecone(
            index_name=INDEX_NAME,
            embedding=get_embeddings(),
        )
    return _vectorstore


async def query_images(
    query: str,
    top_k: int = 5,
    filter_dict: Optional[dict] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query the vector store for similar images.

    Args:
        query: The text query to find similar images
        top_k: Number of results to return
        filter_dict: Optional dictionary for filtering results
        user_id: Optional user ID to filter results for specific user

    Returns:
        List of dictionaries containing image paths and metadata
    """

    try:
        vectorstore = get_vectorstore()

        # Build filter with user_id if provided
        final_filter = filter_dict.copy() if filter_dict else {}
        if user_id:
            final_filter["user_id"] = user_id

        # Perform similarity search
        results = vectorstore.similarity_search(
            query=query, k=top_k, filter=final_filter if final_filter else None
        )

        # Transform Document objects to a more user-friendly format
        image_results = []
        for doc in results:
            image_info = {
                "image_path": doc.metadata.get("image_path", ""),
                "description": doc.page_content,
                "id": doc.metadata.get("id", ""),
                "score": doc.metadata.get("score", None),
                "tags": doc.metadata.get("tags", []),
                "created_at": doc.metadata.get("created_at", ""),
                "additional_metadata": {
                    k: v
                    for k, v in doc.metadata.items()
                    if k not in ["image_path", "id", "score", "tags", "created_at"]
                },
            }
            image_results.append(image_info)

        # print(f"Image query executed in {execution_time:.4f} seconds")

        return image_results

    except Exception as e:
        print(f"Vector image search error: {e}")
        return []


def add_image_embedding(
    embedding: List[float],
    description: str,
    id: str,
    s3_url: str = None,
    original_filename: str = None,
    user_id: str = None,
):
    """
    Add a single image embedding and description directly to Pinecone.

    Args:
        embedding: Embedding vector for the image
        description: Text description for the image
        id: ID for the vector
        s3_url: URL to the image in S3 (optional)
        original_filename: Original filename of the image (optional)
        user_id: User ID to associate with the image (optional)

    Raises:
        ValueError: If there are issues with the input parameters
        PineconeException: If there are issues with the Pinecone operation
        Exception: For any other unexpected errors
    """
    # Validate inputs
    if not embedding:
        raise ValueError("Embedding vector cannot be empty")
    if not description:
        raise ValueError("Description cannot be empty")
    if not id:
        raise ValueError("ID cannot be empty")

    try:
        # Get the Pinecone index directly
        index = get_pinecone_index()

        # Set up metadata
        metadata = {
            "text": description,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Add S3 URL to metadata if provided
        if s3_url:
            metadata["s3_url"] = s3_url

        # Add original filename to metadata if provided
        if original_filename:
            metadata["original_filename"] = original_filename

        # Add user_id to metadata if provided
        if user_id:
            metadata["user_id"] = user_id

        # Create vector for upsert
        vector = {"id": id, "values": embedding, "metadata": metadata}

        # Upsert vector to Pinecone
        index.upsert(vectors=[vector])
    except Exception as pe:
        # Log and re-raise Pinecone-specific errors
        print(f"Pinecone error: {pe}")
        raise
