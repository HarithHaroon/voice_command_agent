"""
Read Book Tool - Read pages from uploaded books.
Migrated from Nova Sonic for LiveKit Agent.
"""

import logging
from typing import List, Optional, Dict, Any
from livekit.agents import function_tool
from tools.base_tool import BaseTool

# Import from root directory
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from books_vector_store import query_books

logger = logging.getLogger(__name__)


class ReadBookTool(BaseTool):
    """Tool for reading pages from uploaded books."""

    def __init__(self):
        super().__init__("read_book")

        self._user_id = None

        # Simple in-memory storage for last read positions
        # In production, this should be persistent storage (e.g., Redis, Firebase)
        self.last_read_positions = {}

        logger.info("ReadBookTool initialized")

    def get_tool_methods(self) -> list:
        """Return list of tool methods this class provides."""
        return ["read_book"]

    def get_tool_functions(self) -> list:
        """Return list of function_tool decorated methods."""
        return [self.read_book]

    @function_tool
    async def read_book(
        self,
        book_name: str,
        page_number: int = 1,
        continue_reading: bool = False,
        pages_to_read: int = 1,
    ) -> str:
        """
        Read pages from a book by name.

        Args:
            book_name: The name of the book to read
            page_number: Page number to start from (default: 1)
            continue_reading: Continue from last position (default: False)
            pages_to_read: Number of pages to read, 1-10 (default: 2)
        """
        try:
            # Validate user_id
            if not self._user_id:
                logger.error("User ID not set for read_book tool")
                return "Cannot access books without user identification."

            # Validate and constrain pages_to_read
            pages_to_read = max(1, min(10, pages_to_read))

            logger.info(
                f"Reading book: {book_name}, page: {page_number}, "
                f"continue: {continue_reading}, pages_to_read: {pages_to_read}"
            )

            # First, find the book by searching for similar titles
            book_chunks = await self._find_book_chunks(book_name, self._user_id)

            if not book_chunks:
                return f"Book '{book_name}' not found in the library. Please check the book name and try again."

            # Determine starting page
            start_page = self._determine_start_page(
                book_name, page_number, continue_reading
            )

            # Get ALL chunks for the specified pages (complete page content)
            ordered_chunks = await self._get_all_chunks_for_pages(
                book_chunks, start_page, pages_to_read
            )

            if not ordered_chunks:
                return f"No content found for '{book_name}' starting from page {start_page}. The book might not have content at that page."

            # Update last read position (set to the page after the last page read)
            last_chunk = ordered_chunks[-1]
            last_page = last_chunk.metadata.get("page_number", start_page)
            self.last_read_positions[book_name.lower()] = last_page + 1

            # Format the reading content
            result = self._format_reading_content(book_name, ordered_chunks, start_page)

            # Send content to client
            await self._send_book_content_to_client(
                book_name, ordered_chunks, start_page
            )

            # At the very end, before return:
            logger.info(f"📖 RETURNING RESULT - Length: {len(result)} chars")

            logger.info(
                f"Successfully read {len(ordered_chunks)} chunks from '{book_name}'"
            )

            # At the very end, before return:
            logger.info(f"📖 RETURNING RESULT - Length: {len(result)} chars")
            logger.info(f"📖 First 200 chars: {result[:200]}")
            return result

        except Exception as e:
            logger.error(f"Error in read_book tool: {e}", exc_info=True)
            return f"Error reading book: {str(e)}. Please try again or check if the book exists in the library."

    async def _find_book_chunks(self, book_name: str, user_id: str = None) -> List:
        """Find ALL chunks for a book by searching with the book name."""

        logger.info(f"🔍 Searching for book: '{book_name}'")
        logger.info(
            f"🔍 User ID: {user_id}"
        )  # First, try to find a few chunks to identify the book

        initial_chunks = await query_books(
            query=book_name,
            top_k=10,  # Get a few chunks to identify the book
            user_id=user_id,
        )

        logger.info(f"📚 Query returned {len(initial_chunks)} chunks")

        if initial_chunks:
            logger.info(f"📚 First chunk metadata: {initial_chunks[0].metadata}")

        if not initial_chunks:
            logger.warning(
                f"❌ No chunks found for '{book_name}' with user_id '{user_id}'"
            )
            return []

        # Group by title and filename to identify the best matching book
        book_groups = {}
        for chunk in initial_chunks:
            metadata = chunk.metadata
            title = metadata.get("title", "").lower()
            filename = metadata.get("filename", "").lower()

            # Create a key that combines title and filename
            key = f"{title}_{filename}"

            if key not in book_groups:
                book_groups[key] = {
                    "chunks": [],
                    "title": metadata.get("title", "Unknown"),
                    "filename": metadata.get("filename", "Unknown"),
                    "match_score": 0,
                }

            book_groups[key]["chunks"].append(chunk)

            # Simple scoring: how well does the title/filename match the query
            if book_name.lower() in title or book_name.lower() in filename:
                book_groups[key]["match_score"] += 1

        # Find the best matching book
        if not book_groups:
            return initial_chunks

        best_match = max(book_groups.values(), key=lambda x: x["match_score"])
        best_title = best_match["title"]
        best_filename = best_match["filename"]

        # Now search for ALL chunks from this specific book
        # Use the exact title and filename to get complete book content
        all_book_chunks = await query_books(
            query=f"{best_title} {best_filename}",
            top_k=500,  # Get many chunks to ensure complete book content
            user_id=user_id,
        )

        # Filter to only include chunks from the identified book
        filtered_chunks = []
        for chunk in all_book_chunks:
            metadata = chunk.metadata
            if (
                metadata.get("title", "").lower() == best_title.lower()
                and metadata.get("filename", "").lower() == best_filename.lower()
            ):
                filtered_chunks.append(chunk)

        return filtered_chunks if filtered_chunks else all_book_chunks

    def _determine_start_page(
        self, book_name: str, page_number: Optional[int], continue_reading: bool
    ) -> int:
        """Determine which page to start reading from."""
        if continue_reading:
            # Get last read position
            last_position = self.last_read_positions.get(book_name.lower(), 1)
            return last_position
        elif page_number:
            return page_number
        else:
            return 1  # Start from beginning

    async def _get_all_chunks_for_pages(
        self, book_chunks: List, start_page: int, pages_to_read: int
    ) -> List:
        """Get ALL chunks for the specified pages (complete page content)."""
        # Calculate the range of pages to read
        end_page = start_page + pages_to_read - 1

        # Filter chunks that belong to the specified page range
        page_chunks = []

        for chunk in book_chunks:
            chunk_page = chunk.metadata.get("page_number", 0)
            if start_page <= chunk_page <= end_page:
                page_chunks.append(chunk)

        # Sort by page number, then by chunk index to ensure proper order
        sorted_chunks = sorted(
            page_chunks,
            key=lambda doc: (
                doc.metadata.get("page_number", float("inf")),
                doc.metadata.get("chunk_index", 0),
            ),
        )

        # Return ALL chunks for the specified pages
        return sorted_chunks

    def _format_reading_content(
        self, book_name: str, chunks: List, start_page: int
    ) -> str:
        """Format the reading content for the LLM to read aloud."""
        if not chunks:
            return (
                f"No content found for '{book_name}' starting from page {start_page}."
            )

        # Get book metadata from first chunk
        first_chunk = chunks[0]
        metadata = first_chunk.metadata
        title = metadata.get("title", book_name)
        author = metadata.get("author", "Unknown Author")

        # Build the reading content (simplified for voice)
        result = (
            f'Reading from "{title}" by {author}. Starting from page {start_page}.\n\n'
        )

        current_page = None
        for i, chunk in enumerate(chunks):
            chunk_page = chunk.metadata.get("page_number", "Unknown")

            # Add page header if this is a new page
            if chunk_page != current_page:
                if current_page is not None:
                    result += "\n"
                result += f"Page {chunk_page}:\n"
                current_page = chunk_page

            # Add chunk content
            content = chunk.page_content.strip()
            if content:
                result += f"{content}\n\n"

        # Add navigation info
        last_page = chunks[-1].metadata.get("page_number", start_page)
        result += f"\nFinished reading pages {start_page} to {last_page}. "
        result += (
            f"Say 'continue reading {book_name}' to continue from page {last_page + 1}."
        )

        return result

    async def _send_book_content_to_client(
        self, book_name: str, chunks: List, start_page: int
    ):
        """Send book content to the Flutter client for display."""
        try:
            from livekit.agents import get_job_context
            import json

            ctx = get_job_context()
            if not ctx or not ctx.room:
                logger.error("No room context available to send book content")
                return

            # Get book metadata
            first_chunk = chunks[0]
            metadata = first_chunk.metadata
            title = metadata.get("title", book_name)
            author = metadata.get("author", "Unknown Author")

            # Format pages
            pages = []
            current_page = None
            current_page_content = []

            for chunk in chunks:
                chunk_page = chunk.metadata.get("page_number", "Unknown")

                if chunk_page != current_page:
                    # Save previous page if exists
                    if current_page is not None:
                        pages.append(
                            {
                                "page_number": current_page,
                                "content": "\n\n".join(current_page_content),
                            }
                        )
                    # Start new page
                    current_page = chunk_page
                    current_page_content = []

                current_page_content.append(chunk.page_content.strip())

            # Add last page
            if current_page is not None:
                pages.append(
                    {
                        "page_number": current_page,
                        "content": "\n\n".join(current_page_content),
                    }
                )

            # Format message for client
            message = {
                "type": "book_content",
                "book": {
                    "title": title,
                    "author": author,
                    "start_page": start_page,
                    "pages": pages,
                },
            }

            message_bytes = json.dumps(message).encode("utf-8")
            await ctx.room.local_participant.publish_data(message_bytes)
            logger.info(
                f"Sent book content to client: {title}, pages {start_page}-{pages[-1]['page_number']}"
            )

        except Exception as e:
            logger.error(f"Error sending book content to client: {e}", exc_info=True)
