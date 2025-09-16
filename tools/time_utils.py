"""
Time utilities tool for client-side execution via Flutter app.
"""

import json
import asyncio
import logging
from livekit.agents import function_tool, ToolError, get_job_context

logger = logging.getLogger(__name__)


class TimeTool:
    """Tool for getting current time information from Flutter client."""

    def __init__(self):
        self._pending_responses = {}
        self._agent = None
        # Start cleanup task
        asyncio.create_task(self._cleanup_old_requests())

    def set_agent(self, agent):
        """Set the agent reference."""
        self._agent = agent
        logger.info("TimeTool linked to agent")

    @function_tool
    async def get_current_time(self, timezone: str = "local") -> str:
        logger.info(f"Tool called - requesting time for timezone: {timezone}")

        try:
            ctx = get_job_context()
            if not ctx or not ctx.room:
                raise ToolError("Room context not available")

            request_id = f"time_{asyncio.get_event_loop().time()}_{timezone}"
            logger.info(f"Generated request ID: {request_id}")

            # Create response future
            response_future = asyncio.Future()
            self._pending_responses[request_id] = response_future

            # Send tool request
            tool_request = {
                "type": "tool_request",
                "tool": "get_current_time",
                "request_id": request_id,
                "params": {"timezone": timezone},
            }

            logger.info(f"Sending tool request: {tool_request}")
            message_bytes = json.dumps(tool_request).encode("utf-8")
            await ctx.room.local_participant.publish_data(message_bytes)
            logger.info("Tool request sent successfully")

            logger.info("Waiting for Flutter response...")

            # CHANGED: Don't clean up immediately on timeout
            try:
                response = await asyncio.wait_for(response_future, timeout=60.0)
                logger.info(f"Received response: {response}")

                if response.get("success", False):
                    result = response.get("result", {})
                    time_info = result.get("time", "Unknown time")
                    logger.info(f"Time retrieved: {time_info}")
                    return f"The current time is {time_info}"
                else:
                    error_msg = response.get("error", "Unknown error")
                    logger.error(f"Flutter returned error: {error_msg}")
                    raise ToolError(f"Client error: {error_msg}")

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for Flutter response")
                # DON'T clean up here - let it stay for late responses
                logger.info("Keeping request in pending list for late response")
                raise ToolError("Timeout waiting for time from Flutter app")

            finally:
                # ONLY clean up if we got a response
                if (
                    request_id in self._pending_responses
                    and self._pending_responses[request_id].done()
                ):
                    self._pending_responses.pop(request_id, None)
                    logger.info(f"Cleaned up completed request: {request_id}")

        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ToolError(f"Failed to get time: {str(e)}")

    def handle_tool_response(self, response_data):
        """Handle tool response from Flutter client."""
        request_id = response_data.get("request_id")
        logger.info(f"Handling response for request: {request_id}")
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

    async def _cleanup_old_requests(self):
        """Clean up requests older than 5 minutes."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            current_time = asyncio.get_event_loop().time()

            old_requests = []
            for request_id in list(self._pending_responses.keys()):
                # Extract timestamp from request_id
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
                    logger.info(f"Cleaned up old request: {request_id}")
