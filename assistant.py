"""
Simple AI Assistant - Final working version for LiveKit Cloud.
"""

import json
import logging
import asyncio
from livekit.agents import Agent, get_job_context
from tools.time_utils import TimeTool

logger = logging.getLogger(__name__)


class SimpleAssistant(Agent):
    def __init__(self) -> None:
        self.time_tool = TimeTool()

        super().__init__(
            instructions="You are a helpful AI assistant that can get the current time from the user's device.",
            tools=[self.time_tool.get_current_time],
        )

    async def on_enter(self):
        logger.info("Simple Assistant entered the room")
        self.time_tool.set_agent(self)

        # Use job context to get the room (correct for LiveKit Cloud)
        await self._setup_data_handler()

        await self.session.say("Hello! I'm your time assistant.")

    async def _setup_data_handler(self):
        """Setup data handler using job context."""
        try:
            await asyncio.sleep(1)  # Wait for initialization

            ctx = get_job_context()
            if ctx and ctx.room:
                ctx.room.on("data_received", self._handle_data)
                logger.info("Data handler registered successfully")
            else:
                logger.error("No job context room available")

        except Exception as e:
            logger.error(f"Data handler setup failed: {e}")

    def _handle_data(self, data, participant=None):
        logger.info("Data received!")

        try:
            # Extract message bytes
            if hasattr(data, "data"):
                message_bytes = data.data
            else:
                message_bytes = data

            # Parse message
            message = json.loads(message_bytes.decode("utf-8"))
            logger.info(f"Parsed message: {message}")

            # Route tool responses
            if message.get("type") == "tool_result":
                logger.info("Routing to time tool...")
                self.time_tool.handle_tool_response(message)

        except Exception as e:
            logger.error(f"Data handling error: {e}")
