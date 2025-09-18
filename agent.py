"""
Main entry point for the LiveKit AI Assistant.
"""

import dotenv
import json
import logging
from livekit import agents
from livekit.agents import AgentSession
from livekit.plugins import openai, silero

from assistant import SimpleAssistant

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

    # Connect to the room
    await ctx.connect()
    logger.info("=== CONNECTED TO ROOM ===")

    # Extract voice preference from token metadata
    voice_preference = "alloy"  # default
    try:
        # Access the local participant's metadata (contains the voice preference)
        local_participant = ctx.room.local_participant
        if local_participant and local_participant.metadata:
            participant_data = json.loads(local_participant.metadata)
            voice_preference = participant_data.get("voice_preference", "alloy")
            logger.info(f"Using voice preference from token: {voice_preference}")
    except Exception as e:
        logger.warning(
            f"Failed to parse participant metadata, using default voice: {e}"
        )

    # Create agent session with OpenAI for everything
    session = AgentSession(
        # Speech-to-Text using OpenAI Whisper
        stt=openai.STT(),
        # Large Language Model using OpenAI GPT
        llm=openai.LLM(model="gpt-4o-mini"),
        # Text-to-Speech using OpenAI TTS
        tts=openai.TTS(voice=voice_preference),  # Use dynamic voice
        # Voice Activity Detection (free local model)
        vad=ctx.proc.userdata["vad"],
    )
    logger.info(f"=== SESSION CREATED WITH VOICE: {voice_preference} ===")

    # Start the session with our agent
    await session.start(
        room=ctx.room,
        agent=SimpleAssistant(),
    )
    logger.info("=== SESSION STARTED ===")

    # Generate an initial greeting
    logger.info("=== GENERATING INITIAL REPLY ===")
    await session.generate_reply(
        instructions=(
            "Greet the user warmly and let them know what you can help with. "
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
