"""
LiveKit agent adapter.
Connects the test framework to your LiveKit voice agent.
"""

import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

from .base import BaseAdapter
from tests.core.exceptions import AdapterError

# Import your agent code
from assistant import Assistant
from intent_detection.intent_detector import IntentDetector
from prompt_management.prompt_module_manager import PromptModuleManager

logger = logging.getLogger(__name__)


class LiveKitAdapter(BaseAdapter):
    """Adapter for LiveKit voice agent - text-only testing"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.assistant = None
        self.openai_client = None

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the LiveKit agent for testing"""

        try:
            user_id = config.get("user_id", "test_user_123")
            use_llm_intent = config.get("use_llm_intent", False)

            logger.info(f"Initializing LiveKit adapter for user: {user_id}")
            logger.info(f"LLM intent detection: {use_llm_intent}")

            # Create your assistant instance (no LiveKit session)
            self.assistant = Assistant(user_id=user_id, use_llm_intent=use_llm_intent)

            # Initialize OpenAI client for real mode
            self.openai_client = AsyncOpenAI()

            self._initialized = True
            logger.info("LiveKit adapter initialized successfully")

        except Exception as e:
            raise AdapterError(f"Failed to initialize LiveKit adapter: {e}")

    async def detect_intent(self, user_input: str) -> Dict[str, Any]:
        """Detect user intent using your agent's intent detector"""

        self._ensure_initialized()

        try:
            # Use your intent detector directly
            result = await self.assistant.intent_detector.detect(user_input)

            # Check if result is from LLM detector (IntentResult) or regex (dict-like)
            if hasattr(result, "modules"):
                # LLM detector returns IntentResult object
                return {
                    "modules": result.modules,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                    "matched_patterns": {},
                }
            else:
                # Regex detector returns dict-like object with attributes
                return {
                    "modules": result.modules,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                    "matched_patterns": result.matched_patterns,
                }

        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            raise AdapterError(f"Intent detection error: {e}")

    async def process_message(
        self, user_input: str, mode: str = "mock"
    ) -> Dict[str, Any]:
        """
        Process user message through your agent.

        Args:
            user_input: Text input from user
            mode: "mock" or "real"

        Returns:
            {
                "tool": str,           # Tool name called
                "params": dict,        # Tool parameters
                "response": str,       # Agent response text
                "intent": dict         # Intent detection result
            }
        """

        self._ensure_initialized()

        try:
            # Step 1: Always detect intent
            intent = await self.detect_intent(user_input)

            if mode == "mock":
                # Mock mode: Return None (testers will use expected values)
                return {
                    "tool": None,
                    "params": None,
                    "response": None,
                    "intent": intent,
                    "mode": "mock",
                }

            elif mode == "real":
                # Real mode: Actually call OpenAI
                return await self._process_with_llm(user_input, intent)

            else:
                raise AdapterError(f"Unknown mode: {mode}")

        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            raise AdapterError(f"Process message error: {e}")

    async def _process_with_llm(
        self, user_input: str, intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process message using actual LLM (real mode)"""

        try:
            # Step 1: Assemble instructions from detected modules
            instructions = self.assistant.module_manager.assemble_instructions(
                modules=intent["modules"],
                user_message=user_input,
                current_time=(
                    self.assistant.time_tracker.get_formatted_datetime()
                    if self.assistant.time_tracker.is_initialized()
                    else None
                ),
            )

            logger.debug(f"Assembled instructions: {len(instructions)} chars")

            # Step 2: Get available tools
            tool_definitions = self._get_tool_definitions()

            logger.info(f"Got {len(tool_definitions)} tool definitions")

            # Step 3: Call OpenAI
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": user_input},
                ],
                tools=tool_definitions if tool_definitions else None,
                temperature=0.2,
                max_tokens=1000,
            )

            # Step 4: Parse response
            message = response.choices[0].message

            # Check if tool was called
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_params = json.loads(tool_call.function.arguments)

                return {
                    "tool": tool_name,
                    "params": tool_params,
                    "response": f"Called {tool_name}",
                    "intent": intent,
                    "mode": "real",
                }
            else:
                # No tool call, just response text
                return {
                    "tool": None,
                    "params": None,
                    "response": message.content,
                    "intent": intent,
                    "mode": "real",
                }

        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            raise AdapterError(f"LLM processing error: {e}")

    def _get_tool_definitions(self) -> list:
        """Get tool definitions from your agent by building OpenAI schemas"""

        try:
            import inspect
            from typing import get_type_hints, get_origin, get_args

            # Get all tool functions from your tool manager
            tool_functions = self.assistant.tool_manager.get_all_tool_functions()

            logger.info(f"Retrieved {len(tool_functions)} tool functions")

            tools = []
            for func in tool_functions:
                try:
                    # Build OpenAI function schema from function signature
                    schema = self._build_openai_schema(func)
                    if schema:
                        tools.append({"type": "function", "function": schema})
                except Exception as e:
                    logger.warning(f"Failed to build schema for {func.__name__}: {e}")
                    continue

            logger.info(f"Built {len(tools)} tool schemas for OpenAI")
            return tools

        except Exception as e:
            logger.error(f"Failed to get tool definitions: {e}", exc_info=True)
            return []

    def _build_openai_schema(self, func) -> dict:
        """Build OpenAI function schema from a Python function"""
        import inspect
        from typing import get_type_hints

        # Get function metadata
        name = func.__name__
        description = (func.__doc__ or "").strip()

        # Get function signature
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        # Build parameters schema
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            # Skip 'self'
            if param_name == "self":
                continue

            # Get parameter type
            param_type = type_hints.get(param_name, str)

            # Map Python types to JSON schema types
            json_type = self._python_type_to_json_type(param_type)

            # Extract description from docstring (basic extraction)
            param_desc = self._extract_param_description(description, param_name)

            properties[param_name] = {
                "type": json_type,
                "description": param_desc or f"Parameter {param_name}",
            }

            # Check if parameter is required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "name": name,
            "description": description or f"Function {name}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def _python_type_to_json_type(self, python_type) -> str:
        """Convert Python type to JSON schema type"""
        import typing

        # Handle Optional types
        if hasattr(python_type, "__origin__"):
            origin = python_type.__origin__
            if origin is typing.Union:
                # Get non-None type
                args = [t for t in python_type.__args__ if t is not type(None)]
                if args:
                    python_type = args[0]

        # Map types
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        return type_map.get(python_type, "string")

    def _extract_param_description(self, docstring: str, param_name: str) -> str:
        """Extract parameter description from docstring"""
        if not docstring:
            return ""

        # Look for "param_name:" in docstring
        lines = docstring.split("\n")
        for i, line in enumerate(lines):
            if f"{param_name}:" in line.lower():
                # Extract description after the colon
                desc = line.split(":", 1)[-1].strip()
                return desc

        return ""

    def get_available_modules(self) -> list:
        """Get list of available prompt modules"""

        self._ensure_initialized()

        try:
            return self.assistant.module_manager.get_available_modules()
        except Exception as e:
            logger.error(f"Failed to get modules: {e}")
            return []

    def get_available_tools(self) -> list:
        """Get list of available tools"""

        self._ensure_initialized()

        try:
            return self.assistant.tool_manager.get_registered_tools()
        except Exception as e:
            logger.error(f"Failed to get tools: {e}")
            return []
