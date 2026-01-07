import logging

logger = logging.getLogger(__name__)


def extract_user_id(room_name: str) -> str:
    """
    Extract user_id from room name format: room_{userId}_{userName}_{timestamp}

    Example: room_user_20250601111146_bc2d2766-bac9-4271-89d9-9b15c33cab8a_Harith_1704384000000
    Result: user_20250601111146_bc2d2766-bac9-4271-89d9-9b15c33cab8a

    Note: userId can contain underscores, userName and timestamp cannot
    """
    logger.info(f"🔍 FULL ROOM NAME: {room_name}")

    if not room_name.startswith("room_"):
        logger.warning(f"❌ Invalid room name format: {room_name}")

        return None

    # Remove "room_" prefix
    rest = room_name.replace("room_", "", 1)

    logger.info(f"After removing 'room_': {rest}")

    # Split from the RIGHT by last 2 underscores to separate timestamp and userName
    # Format: {userId}_{userName}_{timestamp}
    parts = rest.rsplit("_", 2)

    if len(parts) != 3:
        logger.warning(f"❌ Could not parse room name (expected 3 parts): {room_name}")

        return None

    user_id = parts[0]

    user_name = parts[1]

    timestamp = parts[2]

    logger.info(
        f"✅ Extracted user_id: {user_id}, userName: {user_name}, timestamp: {timestamp}"
    )

    return user_id
