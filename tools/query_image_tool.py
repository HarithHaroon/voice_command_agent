"""
Query Image Tool - Search for images using text queries.
Migrated from Nova Sonic for LiveKit Agent.
"""

import logging
from typing import Dict, Any, List
from livekit.agents import function_tool
from tools.base_tool import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vector_stores.images_vector_store import query_images
from helpers.generate_presigned_url import generate_presigned_url


logger = logging.getLogger(__name__)


async def select_best_image_with_llm(
    query: str, image_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Use LLM to select the best matching image from results."""
    llm = ChatOpenAI(model="gpt-4o", temperature=1.0, request_timeout=30.0)

    image_descriptions = ""
    for i, img in enumerate(image_results):
        image_descriptions += (
            f"Image {i+1}: {img.get('description', 'No description provided.')}\n"
        )

    prompt = (
        f"Given the user's query: '{query}', "
        f"and the following image descriptions:\n\n{image_descriptions}\n"
        f"Please identify the number of the image that best fits the query. "
        f"Respond only with the image number (e.g., '1', '2', etc.)."
    )

    message = SystemMessage(content=prompt)
    response = await llm.ainvoke([message])

    try:
        selected_index = int(response.content.strip()) - 1
        if 0 <= selected_index < len(image_results):
            return image_results[selected_index]
        else:
            logger.debug(
                f"LLM returned out-of-bounds index: {selected_index}. Returning first image."
            )
            return image_results[0]
    except ValueError:
        logger.error(
            f"LLM did not return a valid number: {response.content}. Returning first image."
        )
        return image_results[0]
    except Exception as e:
        logger.error(f"Error processing LLM response: {e}. Returning first image.")
        return image_results[0]


class QueryImageTool(BaseTool):
    """Tool for querying images from vector store based on text queries."""

    def __init__(self):
        super().__init__("query_image")
        self._user_id = None
        logger.info("QueryImageTool initialized")

    def get_tool_methods(self) -> list:
        return ["query_image"]

    def get_tool_functions(self) -> list:
        return [self.query_image]

    @function_tool
    async def query_image(self, query: str) -> str:
        """
        Search for images based on a text query.

        Args:
            query: The text query to find similar images
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for query_image tool")
                return "Cannot access images without user identification."

            logger.info(f"Querying images with: '{query}' for user: {self._user_id}")

            # Query the vector store
            image_results = await query_images(query, user_id=self._user_id)

            if not image_results:
                return f"No images found matching '{query}'."

            # Process image results to generate presigned URLs
            processed_results = []
            for image in image_results:
                processed_image = image.copy()

                # Check if s3_url exists in additional_metadata
                s3_url = image.get("additional_metadata", {}).get("s3_url")
                if s3_url:
                    try:
                        # Generate presigned URL
                        presigned_result = await generate_presigned_url(s3_url)
                        if presigned_result["status"] == "success":
                            processed_image["additional_metadata"]["s3_url"] = (
                                presigned_result["url"]
                            )
                            logger.debug(
                                f"Generated presigned URL for image {image.get('id', 'unknown')}"
                            )
                        else:
                            logger.warning(
                                f"Failed to generate presigned URL: {presigned_result.get('error', 'Unknown error')}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error generating presigned URL for image {image.get('id', 'unknown')}: {e}"
                        )

                processed_results.append(processed_image)

            # Select best image using LLM
            best_image = await select_best_image_with_llm(query, processed_results)

            # Send image data to client
            await self._send_image_to_client(best_image, query)

            # Return description to LLM
            description = best_image.get("description", "Image found")
            image_url = best_image.get("additional_metadata", {}).get("s3_url", "")

            return f"Found an image matching '{query}': {description}. The image has been sent to the user's screen."

        except Exception as e:
            logger.error(f"Error in query_image: {e}", exc_info=True)
            return f"Error searching for images: {str(e)}"

    async def _send_image_to_client(self, image_data: Dict[str, Any], query: str):
        """Send image data to the Flutter client for display."""
        try:
            from livekit.agents import get_job_context
            import json

            ctx = get_job_context()
            if not ctx or not ctx.room:
                logger.error("No room context available to send image")
                return

            # Format message for client
            message = {"type": "image_result", "query": query, "image": image_data}

            message_bytes = json.dumps(message).encode("utf-8")
            await ctx.room.local_participant.publish_data(message_bytes)
            logger.info(f"Sent image result to client for query: {query}")

        except Exception as e:
            logger.error(f"Error sending image to client: {e}", exc_info=True)
