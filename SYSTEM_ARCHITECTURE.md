# Voice Command Agent: System Architecture

This document outlines the architecture of the Voice Command Agent, a modular and extensible AI assistant designed for voice interactions. It details the system's components, their interactions, and the overall data flow from user voice input to system action.

## High-Level Overview

The system is designed as a real-time voice-first AI assistant. It listens to user commands, understands the user's intent, and uses a set of tools to perform actions. The architecture is highly modular, allowing for the easy addition of new capabilities and a dynamic response to user needs.

The core of the system is a dynamic instruction and tool-switching mechanism. Instead of using a single, static prompt, the agent detects the user's intent and assembles a tailored set of instructions and tools in real-time. This makes the agent more focused, efficient, and capable of handling a wide range of tasks without being overwhelmed by irrelevant context.

## System Diagram

The following diagram illustrates the flow of information from the user's voice command to the final action and response.

```mermaid
sequenceDiagram
    participant User
    participant LiveKit as AgentSession
    participant Agent as agent.py
    participant Assistant as assistant.py
    participant IntentDetector as intent_detector.py
    participant PromptManager as prompt_module_manager.py
    participant ToolManager as tool_manager.py
    participant ClientApp as Client Application

    User->>+LiveKit: Speaks command
    LiveKit->>LiveKit: Transcribes audio (STT)
    LiveKit->>Agent: on_conversation_item_added(user_message)
    Agent->>+IntentDetector: detect_from_history(user_message, history)
    IntentDetector-->>-Agent: IntentResult (e.g., ["reading_ocr"])
    Agent->>+PromptManager: assemble_instructions(modules=["reading_ocr"])
    PromptManager-->>-Agent: Dynamically assembled instructions
    Agent->>LiveKit: update_instructions(new_instructions)
    LiveKit->>Assistant: Executes LLM call with new instructions
    Assistant->>+ToolManager: Executes tool (e.g., query_image_tool)
    ToolManager->>ClientApp: Sends tool command (e.g., via WebSocket)
    ClientApp->>ClientApp: Executes command (e.g., capture and send image)
    ClientApp-->>-ToolManager: Returns tool_result
    ToolManager->>Assistant: Processes tool response
    Assistant->>LiveKit: Generates final text response (TTS)
    LiveKit-->>-User: Speaks response
```

## Core Components

The system is composed of several key modules that work together to process user requests.

### 1. Entrypoint (`agent.py`)

This is the main entry point that initializes the `AgentSession`. It connects to the LiveKit services, including Speech-to-Text (STT), the core Large Language Model (LLM), and Text-to-Speech (TTS). Its primary role is to instantiate the `Assistant` and dynamically update its instructions based on the user's conversation.

**Key Responsibilities:**
- Initialize the LiveKit `AgentSession` with STT, LLM, and TTS services.
- Instantiate the `Assistant`.
- Listen for new user messages from the conversation.
- Use the `IntentDetector` to determine the required modules for the current user request.
- Assemble new instructions using the `PromptModuleManager`.
- Update the agent's system prompt in real-time.

**Simplified Code Sample:**
```python
# agent.py

async def _update_instructions_for_user_message(user_message: str):
    """Detect intent and update instructions dynamically."""
    # Detect intent from the user's message
    intent_result = assistant.intent_detector.detect_from_history(
        user_message, assistant.conversation_history
    )

    # Assemble new instructions from the detected modules
    new_instructions = assistant.module_manager.assemble_instructions(
        modules=list(intent_result.modules)
    )

    # Update the agent's instructions in real-time
    await assistant.update_instructions(new_instructions)

# Listen for new messages and trigger the update
@session.on("conversation_item_added")
def on_conversation_item_added(event):
    if event.item.role == "user":
        asyncio.create_task(_update_instructions_for_user_message(event.item.text_content))
```

### 2. Assistant (`assistant.py`)

The `Assistant` is the central orchestrator. It inherits from the base `Agent` class and integrates all the other components. It initializes the `ToolManager`, `PromptModuleManager`, and `IntentDetector`, and registers all the available tools.

**Key Responsibilities:**
- Initialize and hold references to the `ToolManager`, `PromptModuleManager`, and `IntentDetector`.
- Register all available tools.
- Assemble the initial system instructions.
- Handle incoming data from the client application (e.g., tool responses).

**Simplified Code Sample:**
```python
# assistant.py

class Assistant(Agent):
    def __init__(self, user_id: str = None):
        # Initialize managers
        self.tool_manager = ToolManager()
        self.module_manager = PromptModuleManager()
        self.intent_detector = IntentDetector()
        self.current_modules = ["navigation", "memory_recall"] # Default modules

        # Register tools
        self._register_tools()

        # Assemble initial instructions
        base_instructions = self.module_manager.assemble_instructions(
            modules=self.current_modules
        )

        # Initialize the agent with dynamic instructions and tools
        super().__init__(
            instructions=base_instructions,
            tools=self.tool_manager.get_all_tool_functions(),
        )
```

### 3. Intent Detection (`intent_detector.py`)

This module is responsible for determining the user's intent by analyzing their message. It uses a set of regular expression patterns to match keywords and phrases associated with different capabilities (or "modules"). This detection allows the system to dynamically load only the necessary context into the agent's prompt.

**Key Responsibilities:**
- Define patterns for different user intents (e.g., "read," "call," "remind").
- Analyze a user's message to find matching intents.
- Consider conversation history for better context.
- Return a list of modules required to handle the request.

**Simplified Code Sample:**
```python
# intent_detection/intent_detector.py

class IntentDetector:
    INTENT_PATTERNS = {
        "reading_ocr": [r"\b(read|document|text)\b"],
        "video_calling": [r"\b(call|video call|talk to)\b"],
        "medication_reminders": [r"\b(remind|medication|pills)\b"],
    }

    def detect(self, user_message: str) -> IntentResult:
        detected_modules = set()
        for module, patterns in self.compiled_patterns.items():
            if any(p.search(user_message) for p in patterns):
                detected_modules.add(module)
        return IntentResult(modules=list(detected_modules), ...)
```

### 4. Prompt Management (`prompt_module_manager.py`)

The `PromptModuleManager` is responsible for dynamically building the system instructions for the LLM. It starts with a `base.md` prompt (containing core instructions) and appends content from other module-specific markdown files (`.md`) based on the detected intent. This ensures the LLM receives a concise, relevant prompt for each task.

**Key Responsibilities:**
- Load a base prompt with core instructions.
- Load content from module-specific `.md` files.
- Assemble a final set of instructions by combining the base prompt with the content of the required modules.

**Simplified Code Sample:**
```python
# prompt_management/prompt_module_manager.py

class PromptModuleManager:
    def __init__(self, modules_dir: str = "prompt_modules"):
        self.modules_dir = Path(modules_dir)
        self.base_prompt = self._load_base_prompt() # Loads from base.md

    def load_module(self, module_name: str) -> str:
        # Loads content from a file like "reading_ocr.md"
        module_path = self.modules_dir / f"{module_name}.md"
        if module_path.exists():
            with open(module_path, 'r') as f:
                return f.read()
        return ""

    def assemble_instructions(self, modules: List[str]) -> str:
        # Combines the base prompt with the content of the requested modules
        full_instructions = self.base_prompt
        for module in modules:
            full_instructions += self.load_module(module)
        return full_instructions
```

### 5. Tool Management (`tool_manager.py`)

The `ToolManager` handles the registration and routing of all available tools. Tools represent the concrete actions the agent can take, such as navigating the client app, submitting a form, or starting a video call. Most of these tools are "server-side" representations of client-side functionality.

**Key Responsibilities:**
- Register and store all available tools.
- Provide the list of tool functions to the `Assistant`.
- Route responses from the client application back to the correct tool.

**Simplified Code Sample:**
```python
# tools/tool_manager.py

class ToolManager:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_functions: List = []

    def register_tool(self, tool: BaseTool):
        # Adds a tool to the manager
        self._tools[tool.tool_name] = tool
        self._tool_functions.extend(tool.get_tool_functions())

    def get_all_tool_functions(self) -> List:
        # Returns all tool functions for the agent to use
        return self._tool_functions

    def route_tool_response(self, response_data: Dict[str, Any]) -> bool:
        # Finds the right tool to handle a response from the client
        request_id = response_data.get("request_id")
        for tool in self._tools.values():
            if tool.can_handle_request(request_id):
                tool.handle_tool_response(response_data)
                return True
        return False
```

## Workflow Example: "Read this for me"

1.  **User Speaks:** The user says, "Can you read this for me?"
2.  **STT:** `LiveKit` transcribes the audio into the text "Can you read this for me?".
3.  **Intent Detection:** `agent.py` receives the message and passes it to the `IntentDetector`. The detector matches the word "read" to the `reading_ocr` module.
4.  **Prompt Assembly:** `agent.py` asks the `PromptModuleManager` to assemble instructions for the `["reading_ocr"]` module. The manager combines `base.md` and `reading_ocr.md`.
5.  **Instruction Update:** `agent.py` calls `assistant.update_instructions()` with the newly assembled prompt.
6.  **LLM Execution:** The `Assistant` now processes the user's request with the new, focused instructions. The LLM sees the `query_image_tool` is available (from the `reading_ocr` module) and decides to use it.
7.  **Tool Call:** The `Assistant` calls the `query_image_tool`. This tool sends a command to the client application, asking it to capture an image.
8.  **Client Action:** The client app receives the command, captures an image, and sends it back as a `tool_result`.
9.  **Response Handling:** The `ToolManager` receives the result and forwards it to the `query_image_tool`, which processes the image and returns the text to the LLM.
10. **Final Response:** The LLM generates a human-friendly response (e.g., "Of course, the text says..."), which is synthesized into speech by `LiveKit`'s TTS and spoken to the user.
