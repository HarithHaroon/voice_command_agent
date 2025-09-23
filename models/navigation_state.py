"""
Navigation state management for LiveKit agent sessions.
"""

import logging

logger = logging.getLogger(__name__)


class NavigationState:
    """Manages navigation state for a LiveKit agent session."""

    def __init__(self):
        self.current_stack = []
        self.current_screen = None
        self.available_screens = {}

    def initialize_from_session(self, navigation_data):
        """Initialize state from Flutter session_init"""
        try:
            self.current_stack = navigation_data.get("current_stack", [])
            self.current_screen = navigation_data.get("current_screen")
            self.available_screens = navigation_data.get("available_screens", {})

            logger.info(
                f"Navigation state initialized: stack={self.current_stack}, current={self.current_screen}"
            )
            logger.info(f"Available screens: {list(self.available_screens.keys())}")

        except Exception as e:
            logger.error(f"Failed to initialize navigation state: {e}")
            self.clear()

    def update_from_navigation_success(self, new_stack, new_current_screen):
        """Update state when Flutter confirms successful navigation"""
        try:
            self.current_stack = new_stack
            self.current_screen = new_current_screen

            logger.info(
                f"Navigation state updated: stack={self.current_stack}, current={self.current_screen}"
            )

        except Exception as e:
            logger.error(f"Failed to update navigation state: {e}")

    def clear(self):
        """Clear all navigation state"""
        logger.info("Clearing navigation state")
        self.current_stack = []
        self.current_screen = None
        self.available_screens = {}

    def get_current_screen(self):
        """Get current screen name"""
        return self.current_screen

    def get_current_stack(self):
        """Get current navigation stack"""
        return self.current_stack.copy()  # Return copy to prevent external modification

    def is_initialized(self):
        """Check if navigation state has been initialized"""
        return bool(self.available_screens and self.current_stack)

    def __del__(self):
        """Cleanup when instance is destroyed"""
        if hasattr(self, "current_stack"):
            logger.info("NavigationState instance destroyed - state cleared")
            self.clear()
