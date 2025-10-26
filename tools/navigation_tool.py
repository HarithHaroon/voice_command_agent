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
        return [
            "navigate_to_screen",
            "list_available_screens",
            "find_screen",
        ]

    def get_tool_functions(self) -> list:
        """Return list of function_tool decorated methods."""
        return [
            self.navigate_to_screen,
            self.list_available_screens,
            self.find_screen,
        ]

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

            # Check NavigationState instead of navigation_context
            if not self.agent or not hasattr(self.agent, "navigation_state"):
                return "Navigation state not available - agent not properly initialized"

            nav_state = self.agent.navigation_state
            if not nav_state.is_initialized():
                return "Navigation state not available - no session data received"

            # Get data from NavigationState
            current_stack = nav_state.get_current_stack()
            current_screen = nav_state.get_current_screen()
            screens = nav_state.available_screens

            # FIXED: Debug logging AFTER variables are defined
            logger.info(f"Debug - Available screens: {list(screens.keys())}")
            logger.info(f"Debug - Current stack: {current_stack}")
            logger.info(f"Debug - Current screen: {current_screen}")
            logger.info(f"Debug - Target: {target_screen}")

            logger.info(f"Navigation request: {current_screen} -> {target_screen}")

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

    @function_tool
    async def list_available_screens(self) -> dict:
        """
        List available screens with route_name, display_name, and description.
        Returns a dictionary with current_screen and a list of screen entries.
        """
        try:
            if not self.agent or not hasattr(self.agent, "navigation_state"):
                return {
                    "success": False,
                    "error": "Navigation state not available",
                }

            nav_state = self.agent.navigation_state
            if not nav_state.is_initialized():
                return {"success": False, "error": "No session navigation data"}

            screens = nav_state.available_screens or {}
            items = []
            for route_name, meta in screens.items():
                items.append(
                    {
                        "route_name": route_name,
                        "display_name": meta.get("display_name", route_name),
                        "description": meta.get("description", ""),
                    }
                )

            return {
                "success": True,
                "current_screen": nav_state.get_current_screen(),
                "screens": items,
            }

        except Exception as e:
            logger.error(f"list_available_screens failed: {e}")
            return {"success": False, "error": str(e)}

    @function_tool
    async def find_screen(self, query: str) -> dict:
        """
        Find candidate screens matching a free-text query. Returns top matches
        with simple keyword scoring over route_name, display_name, and description.
        """
        try:
            if not self.agent or not hasattr(self.agent, "navigation_state"):
                return {
                    "success": False,
                    "error": "Navigation state not available",
                }

            nav_state = self.agent.navigation_state
            if not nav_state.is_initialized():
                return {"success": False, "error": "No session navigation data"}

            screens = nav_state.available_screens or {}
            q = (query or "").strip().lower()
            if not q:
                return {"success": False, "error": "Empty query"}

            def score(text: str) -> int:
                t = (text or "").lower()
                s = 0
                # naive keyword scoring: exact contains and token overlap
                if q in t:
                    s += 3
                for token in set(q.split()):
                    if token and token in t:
                        s += 1
                return s

            results = []
            for route_name, meta in screens.items():
                dn = meta.get("display_name", route_name)
                desc = meta.get("description", "")
                total = score(route_name) + score(dn) + score(desc)
                if total > 0:
                    results.append(
                        {
                            "route_name": route_name,
                            "display_name": dn,
                            "description": desc,
                            "score": total,
                        }
                    )

            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            top = results[:5]

            return {"success": True, "query": query, "candidates": top}

        except Exception as e:
            logger.error(f"find_screen failed: {e}")
            return {"success": False, "error": str(e)}

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

        # Special case: if current screen is not 'home', pop back to home first
        # then push to target (keeps navigation stack clean)
        if current_screen != "home" and target_screen != "home":
            logger.info(
                f"Lateral navigation: {current_screen} -> {target_screen} via home"
            )
            return [
                {"action": "pop"},  # Go back to home
                {"action": "push", "screen": target_screen},  # Push target
            ]

        # Check for direct connection (already at home, just push target)
        current_connections = screens.get(current_screen, {}).get("connections", [])
        if target_screen in current_connections:
            return [{"action": "push", "screen": target_screen}]

        # Find shortest path through graph (fallback for complex navigation)
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
