"""
Navigation tool for sending navigation operations to Flutter client.
"""

import logging
from collections import deque
from livekit.agents import function_tool
from .base_tool import BaseTool

logger = logging.getLogger(__name__)


class NavigationTool(BaseTool):
    """Tool for handling navigation requests to Flutter client."""

    def __init__(self, agent=None) -> None:
        super().__init__("navigation")
        self.agent = agent
        logger.info(
            f"NavigationTool initialized with agent: {id(agent) if agent else 'None'}"
        )

    def get_tool_methods(self) -> list:
        """Return list of tool methods this class provides."""
        return ["navigate_to_screen"]

    def get_tool_functions(self) -> list:
        """Return list of function_tool decorated methods."""
        return [self.navigate_to_screen]

    @function_tool
    async def navigate_to_screen(self, target_screen: str) -> str:
        """
        Navigate to specified screen using intelligent pathfinding.

        Args:
            target_screen: Name of the screen to navigate to (e.g., "settings", "home")
        """

        try:

            logger.info(
                f"Tool agent reference: {id(self.agent) if self.agent else 'None'}"
            )
            logger.info(
                f"Agent has navigation_context: {hasattr(self.agent, 'navigation_context') if self.agent else False}"
            )
            # Get navigation context from agent
            if not self.agent or not hasattr(self.agent, "navigation_context"):
                return (
                    "Navigation context not available - agent not properly initialized"
                )

            nav_context = self.agent.navigation_context
            if not nav_context:
                return "Navigation context not available - no session data received"

            current_stack = nav_context.get("current_stack", ["home"])
            screens = nav_context.get("available_screens", {})

            logger.info(f"Navigation request: {current_stack[-1]} -> {target_screen}")

            # Calculate path using pathfinding algorithm
            operations = self._calculate_navigation_path(
                current_stack, target_screen, screens
            )

            if not operations:
                return f"Already on {target_screen} screen"

            logger.info(f"Calculated navigation operations: {operations}")

            # Send operations to Flutter
            result = await self.send_tool_request(
                "navigate_to_screen", {"operations": operations}
            )

            return f"Successfully navigated to {target_screen}"

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return f"Navigation failed: {str(e)}"

    def _calculate_navigation_path(self, current_stack, target_screen, screens):
        """Calculate shortest path from current location to target."""
        current_screen = current_stack[-1]

        logger.info(
            f"Pathfinding: current_stack={current_stack}, target={target_screen}"
        )
        logger.info(f"Current screen: {current_screen}")
        logger.info(f"Target in stack? {target_screen in current_stack}")

        # Already at target
        if current_screen == target_screen:
            logger.info("Already at target, returning empty operations")
            return []

        # Target is in current stack - pop back to it
        if target_screen in current_stack:
            logger.info(
                f"Target '{target_screen}' found in stack, using pop operations"
            )
            return self._pop_to_screen(current_stack, target_screen)

        # Target not in stack - find path and push
        logger.info(f"Target '{target_screen}' not in stack, finding path")
        return self._find_path_and_push(current_screen, target_screen, screens)

    def _pop_to_screen(self, current_stack, target_screen):
        """Generate pop operations to reach target screen in stack."""
        try:
            target_index = current_stack.index(target_screen)
            current_index = len(current_stack) - 1
            pops_needed = current_index - target_index

            return [{"action": "pop"} for _ in range(pops_needed)]
        except ValueError:
            logger.error(f"Target screen '{target_screen}' not found in current stack")
            return []

    def _find_path_and_push(self, current_screen, target_screen, screens):
        """Find shortest path to target and generate push operations."""
        # Validate target screen exists
        if target_screen not in screens:
            logger.error(
                f"Target screen '{target_screen}' not found in available screens: {list(screens.keys())}"
            )
            return []

        # Check for direct connection
        current_connections = screens.get(current_screen, {}).get("connections", [])
        if target_screen in current_connections:
            return [{"action": "push", "screen": target_screen}]

        # Find shortest path through graph
        path = self._find_shortest_path(current_screen, target_screen, screens)

        if not path:
            logger.error(
                f"No navigation path found from '{current_screen}' to '{target_screen}'"
            )
            return []

        # Convert path to push operations (skip current screen)
        return [{"action": "push", "screen": screen} for screen in path[1:]]

    def _find_shortest_path(self, start_screen, target_screen, screens):
        """Use BFS to find shortest path between screens."""
        if start_screen == target_screen:
            return [start_screen]

        queue = deque([[start_screen]])
        visited = {start_screen}

        while queue:
            path = queue.popleft()
            current = path[-1]

            # Get connections for current screen
            screen_data = screens.get(current, {})
            connections = screen_data.get("connections", [])

            for next_screen in connections:
                if next_screen == target_screen:
                    return path + [next_screen]

                if next_screen not in visited and next_screen in screens:
                    visited.add(next_screen)
                    queue.append(path + [next_screen])

        return None
