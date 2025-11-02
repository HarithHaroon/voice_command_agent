"""
Main entry point for the LiveKit AI Assistant.
"""

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

    # Connect to the room (only reaches here for agent rooms)
    await ctx.connect()

    logger.info("=== CONNECTED TO ROOM ===")

    # Extract voice preference and user_id
    voice_preference = "alloy"  # Default voice preference

    user_id = None

    user_id = extract_user_id(room_name)

    # Metadata will be extracted from the first data message (session_init)
    # after the agent connects.
    # For now, user_id remains None until received via data message.
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

    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        role = event.item.role  # "user" or "assistant"
        content = event.item.text_content

        logger.info(f"💾 Conversation item: {role} - {content[:50]}...")

        # Create background task to save
        asyncio.create_task(assistant.save_message_to_firebase(role, content))

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
