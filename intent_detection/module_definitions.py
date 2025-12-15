"""
Definitions of available modules for intent detection.
"""

# Module descriptions for LLM intent detection
MODULE_DEFINITIONS = {
    "backlog": "Reminders, tasks, to-do items, scheduling future actions, setting alerts, notes to remember",
    "navigation": "Moving between app screens, opening menus, going back, navigating UI, showing screens, opening features, taking user to different parts of the app",
    "video_calling": "Starting video calls, calling family members, video chat, face-to-face communication",
    "memory_recall": "Remembering past conversations, recalling what was discussed, retrieving previous information",
    "fall_detection": "Fall detection settings, sensitivity adjustments, emergency contacts",
    "location_tracking": "GPS tracking, location sharing, geofencing settings",
    "books": "Reading books, audiobooks, book recommendations, searching book content",
    "image_recognition": "Analyzing images, identifying objects in photos that are already uploaded, describing what's in a picture, visual analysis of image content. NOT for navigating to face recognition screen.",
    "health_query": "Health status questions, wellness checks, vital signs, heart rate, blood pressure, blood oxygen, steps, sleep, calories, activity levels, health metrics, 'how am I doing', morning health summaries, health trends, fitness data",
}


def get_module_definitions() -> dict:
    """Get all module definitions"""
    return MODULE_DEFINITIONS.copy()


def get_module_description(module_name: str) -> str:
    """Get description for a specific module"""
    return MODULE_DEFINITIONS.get(module_name, "Unknown module")
