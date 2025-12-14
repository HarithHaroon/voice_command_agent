"""
Intent Manager - Handles intent detection and dynamic instruction updates.
"""

import logging
import asyncio
import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant import Assistant

logger = logging.getLogger(__name__)


class IntentManager:
    """Manages intent detection and instruction updates."""

    def __init__(self, assistant: "Assistant"):
        """
        Initialize intent manager.

        Args:
            assistant: Assistant instance to manage
        """
        self.assistant = assistant
        logger.info("IntentManager initialized")

    async def update_from_user_message(self, user_message: str) -> None:
        """
        Detect intent from user message and update instructions if needed.

        Args:
            user_message: The user's message to analyze
        """
        try:
            start_time = asyncio.get_event_loop().time()

            # Detect intent from user message + conversation history
            intent_result = await self.assistant.intent_detector.detect_from_history(
                user_message, self.assistant.conversation_history
            )

            logger.info(
                f"🎯 Intent: {intent_result.reasoning} | "
                f"Modules: {intent_result.modules} | "
                f"Conf: {intent_result.confidence:.2f}"
            )

            # Check if modules need to change
            new_modules = set(intent_result.modules)

            current_modules = set(self.assistant.current_modules)

            if new_modules != current_modules:
                logger.info(
                    f"🔄 Updating: {sorted(current_modules)} → {sorted(new_modules)}"
                )

                # Assemble new instructions from detected modules
                new_instructions = self.assistant.module_manager.assemble_instructions(
                    modules=list(new_modules),
                    user_message=user_message,
                    current_time=(
                        self.assistant.time_tracker.get_formatted_datetime()
                        if self.assistant.time_tracker.is_initialized()
                        else datetime.datetime.now().strftime(
                            "%A, %B %d, %Y at %I:%M %p"
                        )
                    ),
                )

                # Update agent's instructions in real-time
                await self.assistant.update_instructions(new_instructions)

                self.assistant.current_modules = list(new_modules)

                elapsed = (asyncio.get_event_loop().time() - start_time) * 1000

                logger.info(
                    f"✅ Updated | {len(new_instructions)} chars | {elapsed:.1f}ms"
                )

            # Track conversation history for context-aware intent detection
            self.assistant.conversation_history.append(
                {"role": "user", "content": user_message}
            )

            # Trim history to last 10 messages
            if len(self.assistant.conversation_history) > 10:
                self.assistant.conversation_history = (
                    self.assistant.conversation_history[-10:]
                )

        except Exception as e:
            logger.error(f"❌ Error updating instructions: {e}", exc_info=True)
