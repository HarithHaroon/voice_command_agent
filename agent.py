"""
Main entry point for the LiveKit AI Assistant.
"""

import datetime
import json
import dotenv
import logging
from livekit import agents
from livekit.agents import AgentSession
from livekit.plugins import openai, silero
import asyncio
from helpers.extract_user_id import extract_user_id

from assistant import Assistant

dotenv.load_dotenv(".env.local")

# Set up logging
logger = logging.getLogger(__name__)


def prewarm_fnc(proc: agents.JobProcess):
    """Prewarm function - runs once per worker process."""
    logger.info("=== PREWARM FUNCTION CALLED ===")

    proc.userdata["vad"] = silero.VAD.load()

    logger.info("=== VAD MODEL LOADED IN PREWARM ===")


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the agent."""

    logger.info("=== ENTRYPOINT START ===")

    # Get room name
    room_name = ctx.room.name

    logger.info(f"Received request for room: {room_name}")

    # Filter: Only join rooms starting with "room_" (your agent rooms)
    if not room_name.startswith("room_"):
        logger.info(f"❌ Ignoring room '{room_name}' - not an agent room")

        return  # Exit immediately without connecting

    logger.info(f"✅ Joining agent room: {room_name}")

    voice_preference = "alloy"

    try:
        metadata = json.loads(ctx.job.metadata)

        voice_preference = metadata.get("voice_preference", "alloy")

        logger.info(f"✅ Voice preference from metadata: {voice_preference}")
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"⚠️ No metadata or invalid JSON, using default voice: {e}")

    # Connect to the room (only reaches here for agent rooms)
    await ctx.connect()

    logger.info("=== CONNECTED TO ROOM ===")

    # Extract voice preference and user_id
    user_id = None

    user_id = extract_user_id(room_name)

    logger.info("Metadata extraction will occur via data message.")

    # Create agent session
    session = AgentSession(
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.2),
        tts=openai.TTS(voice=voice_preference),
        vad=ctx.proc.userdata["vad"],
    )

    logger.info(f"=== SESSION CREATED ===")

    logger.info("=" * 50)
    logger.info(f"🎯 Creating Assistant with user_id: {user_id}")
    logger.info("=" * 50)

    assistant = Assistant(user_id=user_id)

    assistant.tool_manager.set_session(session)

    logger.info("✅ Session linked to ToolManager")

    # 🆕 NEW: Dynamic instruction updater
    async def _update_instructions_for_user_message(user_message: str):
        """Detect intent and update instructions dynamically."""
        try:
            start_time = asyncio.get_event_loop().time()

            # Detect intent from user message + conversation history
            intent_result = assistant.intent_detector.detect_from_history(
                user_message, assistant.conversation_history
            )

            logger.info(
                f"🎯 Intent: {intent_result.reasoning} | Modules: {intent_result.modules} | Conf: {intent_result.confidence:.2f}"
            )

            # Check if modules need to change
            new_modules = set(intent_result.modules)

            current_modules = set(assistant.current_modules)

            if new_modules != current_modules:
                logger.info(
                    f"🔄 Updating: {sorted(current_modules)} → {sorted(new_modules)}"
                )

                # Assemble new instructions from detected modules
                new_instructions = assistant.module_manager.assemble_instructions(
                    modules=list(new_modules),
                    user_message=user_message,
                    current_time=(
                        assistant.time_tracker.get_formatted_datetime()
                        if assistant.time_tracker.is_initialized()
                        else datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
                    ),
                )

                # ✨ THE KEY CALL: Update agent's instructions in real-time
                await assistant.update_instructions(new_instructions)

                assistant.current_modules = list(new_modules)

                elapsed = (asyncio.get_event_loop().time() - start_time) * 1000

                logger.info(
                    f"✅ Updated | {len(new_instructions)} chars | {elapsed:.1f}ms"
                )

            # Track conversation history for context-aware intent detection
            assistant.conversation_history.append(
                {"role": "user", "content": user_message}
            )

            if len(assistant.conversation_history) > 10:
                assistant.conversation_history = assistant.conversation_history[-10:]

        except Exception as e:
            logger.error(f"❌ Error updating instructions: {e}", exc_info=True)

    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        role = event.item.role  # "user" or "assistant"

        content = event.item.text_content

        logger.info(f"💾 Conversation item: {role} - {content[:50]}...")

        # 🆕 NEW: Trigger dynamic instruction update for user messages
        if role == "user":
            asyncio.create_task(_update_instructions_for_user_message(content))

        # Save to Firebase
        asyncio.create_task(assistant.save_message_to_firebase(role, content))

        # Send to client via data channel
        asyncio.create_task(_send_conversation_message(role, content))

    async def _send_conversation_message(role: str, content: str):
        """Send conversation message to Flutter client."""
        try:
            message = {
                "type": "conversation_message",
                "role": role,  # "user" or "assistant"
                "content": content,
            }

            message_bytes = json.dumps(message).encode("utf-8")

            await ctx.room.local_participant.publish_data(message_bytes)

            logger.info(f"📤 Sent {role} message to client")
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")

    # Start the session with our agent
    await session.start(
        room=ctx.room,
        agent=assistant,
    )

    logger.info("=== SESSION STARTED ===")

    # Generate an initial greeting
    logger.info("=== GENERATING INITIAL REPLY ===")

    await session.generate_reply(
        instructions=(
            "You're now connected! Warmly greet the user and proactively ask what they'd like help with today. "
            "Be specific about your capabilities: reading text from books/documents, recognizing faces, "
            "setting medication reminders, making video calls, or managing safety settings. "
            "Keep it brief and friendly."
        )
    )

    logger.info("=== INITIAL REPLY GENERATED ===")


if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm_fnc,
        )
    )
