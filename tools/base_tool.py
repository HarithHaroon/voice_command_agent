"""
Base class for all client-side tools.
"""

import json
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from livekit.agents import ToolError, get_job_context

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all client-side tools."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self.agent = None
        self._user_id = None
        self.session = None
        # Start cleanup task
        asyncio.create_task(self._cleanup_old_requests())

    def set_agent(self, agent):
        """Set the agent reference."""
        self.agent = agent
        logger.info(f"{self.tool_name} linked to agent")

    def set_user_id(self, user_id: str):
        """Set the current user ID for this tool instance."""
        self._user_id = user_id

    def set_session(self, session):
        """Set the agent session reference."""
        self.session = session

        logger.info(f"{self.tool_name} linked to session")

    async def send_tool_request(
        self, method: str, params: Dict[str, Any], param_for_id: str = None
    ) -> Dict[str, Any]:
        """Send a tool request to the Flutter client and wait for response."""
        logger.info(f"Tool {self.tool_name} calling method: {method}")

        try:
            ctx = get_job_context()
            if not ctx or not ctx.room:
                raise ToolError("Room context not available")

            # Generate request ID in the original working format: "toolname_timestamp_param"
            id_suffix = param_for_id if param_for_id else method
            request_id = (
                f"{self.tool_name}_{asyncio.get_event_loop().time()}_{id_suffix}"
            )
            logger.info(f"Generated request ID: {request_id}")

            # Create response future
            response_future = asyncio.Future()
            self._pending_responses[request_id] = response_future

            # Build tool request in exact original format
            tool_request = {
                "type": "tool_request",
                "tool": method,
                "request_id": request_id,
                "params": params,
            }

            logger.info(f"Sending tool request: {tool_request}")
            message_bytes = json.dumps(tool_request).encode("utf-8")
            await ctx.room.local_participant.publish_data(message_bytes)
            logger.info("Tool request sent successfully")

            # Wait for response
            try:
                response = await asyncio.wait_for(response_future, timeout=60.0)
                logger.info(f"Received response: {response}")

                if response.get("success", False):
                    return response.get("result", {})
                else:
                    error_msg = response.get("error", "Unknown error")
                    logger.error(f"Flutter returned error: {error_msg}")
                    raise ToolError(f"Client error: {error_msg}")

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for Flutter response")
                raise ToolError(f"Timeout waiting for response from {self.tool_name}")

            finally:
                # Clean up if we got a response
                if (
                    request_id in self._pending_responses
                    and self._pending_responses[request_id].done()
                ):
                    self._pending_responses.pop(request_id, None)
                    logger.info(f"Cleaned up completed request: {request_id}")

        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.tool_name}: {e}")
            raise ToolError(f"Failed to execute {self.tool_name}: {str(e)}")

    def handle_tool_response(self, response_data: Dict[str, Any]):
        """Handle tool response from Flutter client."""
        request_id = response_data.get("request_id")
        logger.info(f"Handling response for {self.tool_name} request: {request_id}")
        logger.info(f"Current pending requests: {list(self._pending_responses.keys())}")

        if request_id and request_id in self._pending_responses:
            future = self._pending_responses[request_id]
            if not future.done():
                future.set_result(response_data)
                logger.info(f"Response delivered successfully: {request_id}")
            else:
                logger.warning(f"Future already completed: {request_id}")
        else:
            logger.warning(f"No pending request found for: {request_id}")

    def can_handle_request(self, request_id: str, tool_name: str) -> bool:
        """Check if this tool can handle the given request."""
        # Check by request ID prefix (e.g., "time_" for TimeTool)
        if request_id.startswith(f"{self.tool_name}_"):
            return True

        # Check by tool method name (e.g., "get_current_time" for TimeTool)
        if tool_name in self.get_tool_methods():
            return True

        return False

    @abstractmethod
    def get_tool_methods(self) -> list:
        """Return list of tool methods this class provides."""
        pass

    @abstractmethod
    def get_tool_functions(self) -> list:
        """Return list of function_tool decorated methods."""
        pass

    async def _cleanup_old_requests(self):
        """Clean up requests older than 5 minutes."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            current_time = asyncio.get_event_loop().time()

            old_requests = []
            for request_id in list(self._pending_responses.keys()):
                try:
                    parts = request_id.split("_")
                    request_time = float(parts[1])
                    if current_time - request_time > 300:  # 5 minutes old
                        old_requests.append(request_id)
                except (IndexError, ValueError):
                    continue

            for request_id in old_requests:
                if request_id in self._pending_responses:
                    future = self._pending_responses.pop(request_id)
                    if not future.done():
                        future.cancel()
                    logger.info(
                        f"Cleaned up old {self.tool_name} request: {request_id}"
                    )
