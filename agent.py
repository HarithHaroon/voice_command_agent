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
from helpers.intent_manager import IntentManager
from helpers.conversation_tracker import ConversationTracker
from helpers.data_channel_handler import DataChannelHandler
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

    # Extract voice preference from metadata
    voice_preference = "alloy"

    try:
        metadata = json.loads(ctx.job.metadata)

        voice_preference = metadata.get("voice_preference", "alloy")

        logger.info(f"✅ Voice preference from metadata: {voice_preference}")
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"⚠️ No metadata or invalid JSON, using default voice: {e}")

    # Connect to the room
    await ctx.connect()

    logger.info("=== CONNECTED TO ROOM ===")

    # Extract user_id
    user_id = extract_user_id(room_name)

    logger.info("Metadata extraction will occur via data message.")

    # Create agent session
    session = AgentSession(
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.2),
        tts=openai.TTS(voice=voice_preference),
        vad=ctx.proc.userdata["vad"],
    )

    logger.info("=== SESSION CREATED ===")

    logger.info(f"🎯 Creating Assistant with user_id: {user_id}")

    assistant = Assistant(user_id=user_id)

    assistant.tool_manager.set_session(session)

    logger.info("✅ Session linked to ToolManager")

    intent_manager = IntentManager(assistant)

    conversation_tracker = ConversationTracker(assistant)

    data_handler = DataChannelHandler(ctx.room)

    # Register conversation event handler
    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        role = event.item.role

        content = event.item.text_content

        logger.info(f"💾 Conversation item: {role} - {content[:50]}...")

        # Track assistant messages (check-in questions)
        if role == "assistant":
            conversation_tracker.track_assistant_message(content)

        # Track user messages (responses & intent detection)
        if role == "user":
            conversation_tracker.track_user_response(content)

            asyncio.create_task(intent_manager.update_from_user_message(content))

        # Save to Firebase
        asyncio.create_task(assistant.save_message_to_firebase(role, content))

        # Send to Flutter client
        asyncio.create_task(data_handler.send_conversation_message(role, content))

    # Start the session with our agent
    await session.start(room=ctx.room, agent=assistant)

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
