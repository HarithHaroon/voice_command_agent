from typing import List, Optional, Dict, Any
import time
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from langchain_pinecone import Pinecone


# Configuration
INDEX_NAME = "sidekick-books"

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
            model="text-embedding-3-small",
            chunk_size=800,
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


async def query_books(
    query: str,
    top_k: int = 3,
    filter_dict: Optional[dict] = None,
    user_id: Optional[str] = None,
) -> List[Document]:
    """
    Query the vector store for similar books.

    Args:
        query: The query string
        top_k: Number of results to return
        filter_dict: Optional dictionary for filtering results (e.g., by genre, author)
        user_id: Optional user ID to filter results for specific user

    Returns:
        List of Document objects representing books
    """
    start_time = time.time()

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

        execution_time = time.time() - start_time
        print(f"Book query executed in {execution_time:.4f} seconds")

        return results

    except Exception as e:
        print(f"Book vector search error: {e}")
        return []


def add_book(
    book_content: str,
    metadata: Dict[str, Any],
    book_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """
    Add a book to the vector store.

    Args:
        book_content: The extracted text content from the book
        metadata: Dictionary with book metadata (title, author, etc.)
        book_id: Optional unique ID for the book
        user_id: Optional user ID to associate with the book
    """
    try:
        # Add user_id to metadata if provided
        if user_id:
            metadata = metadata.copy()
            metadata["user_id"] = user_id

        # Create a Document object
        doc = Document(page_content=book_content, metadata=metadata)

        # Add to vector store
        vectorstore = get_vectorstore()

        if book_id:
            vectorstore.add_documents(documents=[doc], ids=[book_id])
        else:
            vectorstore.add_documents(documents=[doc])

        return "Book added successfully."
    except Exception as e:
        print(f"Error adding book: {e}")
        return f"An error occurred: {str(e)}"


def add_books(books: List[Dict[str, Any]], ids: Optional[List[str]] = None):
    """
    Add multiple books to the vector store.

    Args:
        books: List of dictionaries with 'content' and 'metadata' keys
        ids: Optional list of IDs for the books
    """
    try:
        # Create Document objects
        documents = [
            Document(page_content=book["content"], metadata=book["metadata"])
            for book in books
        ]

        # Add to vector store
        vectorstore = get_vectorstore()
        vectorstore.add_documents(documents=documents, ids=ids)

        return "Books added successfully."
    except Exception as e:
        print(f"Error adding books: {e}")
        return f"An error occurred: {str(e)}"


def update_book(book_id: str, book_content: str, metadata: Dict[str, Any]):
    """
    Update a book in the vector store.

    Args:
        book_id: The ID of the book to update
        book_content: The new book content
        metadata: The new book metadata
    """
    try:
        # Get embeddings for the book content
        embs = get_embeddings()
        vector = embs.embed_documents(texts=[book_content])[0]

        # Update the vector in Pinecone
        index = get_pinecone_index()
        index.update(
            id=book_id,
            values=vector,
            set_metadata={"text": book_content, **metadata},
        )

        return "Book updated successfully."
    except Exception as e:
        print(f"Error updating book: {e}")
        return f"An error occurred: {str(e)}"


def delete_books(book_ids: List[str]):
    """
    Delete books from the vector store by their IDs.

    Args:
        book_ids: List of book IDs to delete
    """
    try:
        vectorstore = get_vectorstore()
        vectorstore.delete(ids=book_ids)
        return "Books deleted successfully."
    except Exception as e:
        print(f"Error deleting books: {e}")
        return f"An error occurred: {str(e)}"


def delete_books_by_filter(filter_dict: dict):
    """
    Delete books from the vector store that match a filter.

    Args:
        filter_dict: Dictionary for filtering books to delete
                    (e.g., {'genre': 'fiction'})
    """
    try:
        vectorstore = get_vectorstore()

        # Find books matching the filter
        results = vectorstore.similarity_search(
            query="",  # Empty query to match based on filter only
            filter=filter_dict,
            k=100,  # Adjust this based on your needs
        )

        if not results:
            return "No matching books found."

        # Extract IDs and delete
        ids = [doc.metadata.get("id") for doc in results if "id" in doc.metadata]
        if ids:
            vectorstore.delete(ids=ids)
            return f"{len(ids)} books deleted successfully."
        else:
            return "Found books but couldn't extract IDs for deletion."
    except Exception as e:
        print(f"Error in delete_books_by_filter: {e}")
        return f"An error occurred: {str(e)}"


def search_books_by_metadata(
    top_k: int = 10, filter_dict: Optional[dict] = None
) -> List[Document]:
    """
    Search for books by a specific metadata field.

    Args:
        metadata_field: The metadata field to search (e.g., 'author', 'title', 'genre')
        value: The value to search for
        top_k: Number of results to return

    Returns:
        List of Document objects representing books
    """
    try:

        vectorstore = get_vectorstore()

        # Use an empty query with metadata filter
        results = vectorstore.similarity_search(query="", k=top_k, filter=filter_dict)
        return results
    except Exception as e:
        print(f"Error searching books by metadata: {e}")
        return []
