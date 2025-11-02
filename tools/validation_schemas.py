"""
Validation schemas for tool inputs using Pydantic.
These schemas provide input validation and sanitization for security.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
import re


class RagBooksToolInput(BaseModel):
    """Validation schema for RAG Books Tool"""

    query: str = Field(
        min_length=1, max_length=500, description="The search query for books"
    )

    @field_validator("query")
    def validate_query(cls, v):
        # Remove potentially dangerous characters
        if not re.match(r"^[a-zA-Z0-9\s\.\,\?\!\-\'\"]+$", v):
            raise ValueError(
                "Query contains invalid characters. Only letters, numbers, spaces, and basic punctuation allowed."
            )
        # Remove excessive whitespace
        return " ".join(v.split())


class ReadBookToolInput(BaseModel):
    """Validation schema for Read Book Tool"""

    book_name: str = Field(
        min_length=1, max_length=200, description="The name of the book to read"
    )
    page_number: Optional[int] = Field(
        ge=1,
        le=10000,
        default=None,
        description="The page number to start reading from",
    )
    continue_reading: bool = Field(
        default=False, description="Whether to continue reading from the last position"
    )
    pages_to_read: int = Field(
        ge=1, le=5, default=2, description="Number of pages to read"
    )

    @field_validator("book_name")
    def validate_book_name(cls, v):
        # Remove potentially dangerous characters
        if not re.match(r"^[a-zA-Z0-9\s\.\-\'\"]+$", v):
            raise ValueError(
                "Book name contains invalid characters. Only letters, numbers, spaces, periods, hyphens, and quotes allowed."
            )
        return " ".join(v.split())


class QueryImageToolInput(BaseModel):
    """Validation schema for Query Image Tool"""

    query: str = Field(
        min_length=1,
        max_length=300,
        description="The text query to find similar images",
    )

    @field_validator("query")
    def validate_query(cls, v):
        # Remove potentially dangerous characters
        if not re.match(r"^[a-zA-Z0-9\s\.\,\?\!\-\'\"]+$", v):
            raise ValueError(
                "Query contains invalid characters. Only letters, numbers, spaces, and basic punctuation allowed."
            )
        return " ".join(v.split())


class RecallHistoryToolInput(BaseModel):
    """Validation schema for Recall History Tool"""

    searchQuery: str = Field(
        min_length=1,
        max_length=200,
        description="The search query to find relevant past conversations",
    )
    timeframe: Literal["1hour", "6hours", "24hours", "7days", "30days", "all"] = Field(
        default="all", description="Time frame to search within"
    )
    maxResults: int = Field(
        ge=1, le=10, default=10, description="Maximum number of results to return"
    )

    @field_validator("searchQuery")
    def validate_search_query(cls, v):
        # Remove potentially dangerous characters
        if not re.match(r"^[a-zA-Z0-9\s\.\,\?\!\-\'\"]+$", v):
            raise ValueError(
                "Search query contains invalid characters. Only letters, numbers, spaces, and basic punctuation allowed."
            )
        return " ".join(v.split())


class FaceRecognitionToolInput(BaseModel):
    """Validation schema for Face Recognition Tool"""

    image_path: str = Field(
        min_length=1,
        max_length=500,
        description="The file path to the uploaded image for face recognition",
    )

    @field_validator("image_path")
    def validate_image_path(cls, v):
        import os

        # Basic path validation - ensure it's a valid file path format
        if not re.match(r"^[a-zA-Z0-9\s\.\-\_\/\\:]+$", v):
            raise ValueError("Image path contains invalid characters")

        # Ensure it has a valid image extension
        valid_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"]
        if not any(v.lower().endswith(ext) for ext in valid_extensions):
            raise ValueError(
                "Image path must have a valid image extension (.jpg, .jpeg, .png, .bmp, .gif, .tiff)"
            )

        return v.strip()


# Tool validation mapping
TOOL_VALIDATION_SCHEMAS = {
    "rag_books_tool": RagBooksToolInput,
    "read_book_tool": ReadBookToolInput,
    "queryImageTool": QueryImageToolInput,
    "recall_history": RecallHistoryToolInput,
    "faceRecognitionTool": FaceRecognitionToolInput,
}
