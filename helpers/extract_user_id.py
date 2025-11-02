import logging

logger = logging.getLogger(__name__)


def extract_user_id(room_name: str) -> str:
    """Extract user_id from room name format: room_{userId}_{userName}_{timestamp}"""
    if not room_name.startswith("room_"):
        logger.warning(f"❌ Invalid room name format: {room_name}")
        return None

    logger.info(f"🔍 FULL ROOM NAME: {room_name}")

    # Remove "room_" prefix
    rest = room_name.replace("room_", "", 1)

    # Split by last underscore to remove timestamp
    parts = rest.rsplit("_", 1)
    if len(parts) != 2:
        logger.warning(f"❌ Could not parse room name: {room_name}")
        return None

    # Now split again to separate userId and userName
    user_parts = parts[0].rsplit("_", 1)
    if len(user_parts) != 2:
        logger.warning(f"❌ Could not parse user parts: {parts[0]}")
        return None

    user_id = user_parts[0]
    user_name = user_parts[1]
    logger.info(f"✅ Extracted user_id: {user_id}, userName: {user_name}")

    return user_id
