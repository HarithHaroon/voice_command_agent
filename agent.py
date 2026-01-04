"""
Main entry point for the LiveKit AI Assistant - Multi-Agent System.
"""

import json
import dotenv
import logging
from livekit import agents
from livekit.agents import AgentSession
from livekit.plugins import openai, silero
import asyncio

from helpers.extract_user_id import extract_user_id
from helpers.conversation_tracker import ConversationTracker
from helpers.assistant_data_handler import AssistantDataHandler
from helpers.assistant_lifecycle import AssistantLifecycle
from helpers.emotion_handler import EmotionHandler

from models.shared_state import SharedState
from models.navigation_state import NavigationState
from helpers.client_time_tracker import ClientTimeTracker
from tools.tool_manager import ToolManager
from clients.firebase_client import FirebaseClient
from clients.health_data_client import HealthDataClient
from backlog.backlog_manager import BacklogManager
from helpers.tool_registry import ToolRegistry
from agents.orchestrator_agent import OrchestratorAgent
from clients.memory_client import MemoryClient

dotenv.load_dotenv(".env.local")

# Set up logging
logger = logging.getLogger(__name__)


def prewarm_fnc(proc: agents.JobProcess):
    """Prewarm function - runs once per worker process."""
    logger.info("=== PREWARM FUNCTION CALLED ===")

    proc.userdata["vad"] = silero.VAD.load()

    logger.info("=== VAD MODEL LOADED IN PREWARM ===")


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the multi-agent system."""

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

    user_name = ""

    try:
        metadata = json.loads(ctx.job.metadata)

        voice_preference = metadata.get("voice_preference", "alloy")

        user_name = metadata.get("participant_name", "Elderly User")

        logger.info(f"✅ Voice preference from metadata: {voice_preference}")

        logger.info(f"✅ @ user name from metadata: {user_name}")

    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"⚠️ No metadata or invalid JSON, using default voice: {e}")

    # Connect to the room
    await ctx.connect()

    logger.info("=== CONNECTED TO ROOM ===")

    # Extract user_id
    user_id = extract_user_id(room_name)

    logger.info(f"🎯 User ID extracted: {user_id}")

    # Initialize shared components
    navigation_state = NavigationState()

    time_tracker = ClientTimeTracker()

    tool_manager = ToolManager()

    firebase_client = FirebaseClient()

    health_client = HealthDataClient()

    backlog_manager = BacklogManager()

    memory_client = MemoryClient()

    # Register all tools
    ToolRegistry.register_all_tools(
        tool_manager=tool_manager,
        navigation_state=navigation_state,
        firebase_client=firebase_client,
        backlog_manager=backlog_manager,
        memory_client=memory_client,
    )

    logger.info(f"✅ Registered {tool_manager.get_tool_count()} tools")

    # Create agent session
    session = AgentSession(
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.2),
        tts=openai.TTS(voice=voice_preference),
        vad=ctx.proc.userdata["vad"],
    )

    logger.info("=== SESSION CREATED ===")

    # Store session in tool_manager for tools that need it
    tool_manager.set_session(session)

    logger.info("✅ Session linked to ToolManager")

    # Create SharedState
    shared_state = SharedState(
        user_id=user_id,
        user_name=user_name,
        navigation_state=navigation_state,
        time_tracker=time_tracker,
        tool_manager=tool_manager,
        firebase_client=firebase_client,
        backlog_manager=backlog_manager,
        health_data_client=health_client,
    )

    logger.info("✅ SharedState created")

    shared_state.tool_manager.set_session_for_all_tools(session)

    # Store shared state in session.userdata (accessible by all agents)
    session.userdata = shared_state

    # Create EmotionHandler
    emotion_handler = EmotionHandler(
        session=session, user_id=user_id, shared_state=shared_state
    )

    logger.info("✅ EmotionHandler created")

    # Create ConversationTracker
    conversation_tracker = ConversationTracker(emotion_handler=emotion_handler)

    logger.info("✅ ConversationTracker created")

    # Create DataHandler
    data_handler = AssistantDataHandler(
        shared_state=shared_state, emotion_handler=emotion_handler
    )

    logger.info("✅ AssistantDataHandler created")

    # Create Lifecycle manager
    lifecycle = AssistantLifecycle(shared_state=shared_state, data_handler=data_handler)

    logger.info("✅ AssistantLifecycle created")

    # Setup lifecycle (tools, time monitor, data handler)
    await lifecycle.setup()

    logger.info("✅ Lifecycle setup complete")

    # Register conversation event handler
    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        role = event.item.role
        content = event.item.text_content

        logger.info(f"💾 Conversation item: {role} - {content[:50]}...")

        # Track assistant messages
        if role == "assistant":
            conversation_tracker.track_assistant_message(content)

        # Track user messages
        if role == "user":
            conversation_tracker.track_user_response(content)

            # Add to shared conversation history
            shared_state.add_to_history("user", content)

        # Track assistant messages in history too
        if role == "assistant":
            shared_state.add_to_history("assistant", content)

        # Save to Firebase
        asyncio.create_task(
            asyncio.to_thread(
                firebase_client.add_message, user_id, role.upper(), content
            )
        )

    # Create orchestrator agent
    orchestrator = OrchestratorAgent(shared_state)

    logger.info("✅ OrchestratorAgent created")

    # Start the session with orchestrator
    await session.start(room=ctx.room, agent=orchestrator)

    logger.info("=== SESSION STARTED WITH ORCHESTRATOR ===")

    # Generate an initial greeting
    logger.info("=== GENERATING INITIAL REPLY ===")

    await session.generate_reply(
        instructions=(
            "You're now connected! Warmly greet the user and proactively ask what they'd like help with today. "
            "Be specific about your capabilities: navigation, video calls, reminders, reading books, "
            "health data, or adjusting settings. Keep it brief and friendly."
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
