"""
Calculator tool for the AI assistant.
"""

from livekit.agents import RunContext, ToolError, function_tool


class CalculatorTool:
    """Tool for performing mathematical calculations."""

    @function_tool()
    async def calculate_math(self, context: RunContext, expression: str) -> str:
        """
        Perform mathematical calculations safely.

        Args:
            expression: Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')

        Returns:
            Result of the calculation
        """
        try:
            # Basic security check - only allow safe mathematical operations
            allowed_chars = set("0123456789+-*/()., ")
            if not all(c in allowed_chars for c in expression):
                raise ToolError("Only basic mathematical operations are allowed")

            # Evaluate expression in a restricted environment
            result = eval(expression, {"__builtins__": {}})
            return f"The result of '{expression}' is: {result}"

        except ZeroDivisionError:
            raise ToolError("Cannot divide by zero")
        except Exception as e:
            raise ToolError(
                f"Unable to calculate '{expression}'. Please check your expression "
                "and try again."
            ) from e
