"""
RAG Books Tool - Search vector store for book content.
Migrated from Nova Sonic for LiveKit Agent.
"""

import logging
from livekit.agents import function_tool
from tools.base_tool import BaseTool


from books_vector_store import query_books

logger = logging.getLogger(__name__)


class RagBooksTool(BaseTool):
    """Tool for searching the vector store for documents related to queries."""

    def __init__(self):
        super().__init__("rag_books_tool")
        self._user_id = None
        logger.info("RagBooksTool initialized")

    def get_tool_methods(self) -> list:
        return ["rag_books_tool"]

    def get_tool_functions(self) -> list:
        return [self.rag_books_tool]

    @function_tool
    async def rag_books_tool(self, query: str) -> str:
        """
        Search the vector store for documents related to the query.

        Args:
            query: The search query
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for rag_books_tool")
                return "Cannot search books without user identification."

            logger.info(f"Searching books vector store with query: {query}")

            docs = await query_books(
                query=query,
                top_k=4,
                user_id=self._user_id,
            )

            if not docs:
                return "No relevant books found for your query. The vector store might be empty or your query didn't match any content."

            # Group documents by book and format for answering the query
            book_groups = {}
            for doc in docs:
                metadata = doc.metadata
                book_key = f"{metadata.get('title', 'Unknown Title')} by {metadata.get('author', 'Unknown Author')}"

                if book_key not in book_groups:
                    book_groups[book_key] = {
                        "title": metadata.get("title", "Unknown Title"),
                        "author": metadata.get("author", "Unknown Author"),
                        "genre": metadata.get("genre", "Unknown Genre"),
                        "chunks": [],
                    }

                book_groups[book_key]["chunks"].append(doc.page_content)

            # Format the results to answer the query based on relevant content
            results = []
            for book_key, book_info in book_groups.items():
                combined_content = "\n".join(book_info["chunks"])
                result_text = (
                    f"From \"{book_info['title']}\" by {book_info['author']}:\n"
                )
                result_text += f"Relevant content: {combined_content}\n"
                results.append(result_text)

            logger.info(f"Found {len(results)} book groups with relevant content")

            return (
                f"Based on the relevant documents found, here's the information to answer your query:\n\n"
                + "\n---\n".join(results)
            )

        except Exception as e:
            logger.error(f"Error in RAG books tool: {e}", exc_info=True)
            return f"Error searching books: {str(e)}. This might be due to missing API keys or vector store configuration issues."
