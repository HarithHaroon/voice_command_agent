"""
Main entry point for the LiveKit AI Assistant.
"""

import dotenv
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

    # Create agent session with OpenAI for everything
    session = AgentSession(
        # Speech-to-Text using OpenAI Whisper
        stt=openai.STT(),
        # Large Language Model using OpenAI GPT
        llm=openai.LLM(model="gpt-4o-mini"),
        # Text-to-Speech using OpenAI TTS
        tts=openai.TTS(),
        # Voice Activity Detection (free local model)
        vad=ctx.proc.userdata["vad"],
    )
    logger.info("=== SESSION CREATED ===")

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
