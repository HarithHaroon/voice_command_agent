# Voice Command Agent

A modular voice command agent with a wide range of capabilities, from managing reminders and reading books to handling health and safety features.

## Project Structure

```
├───agent.py                    # Main agent class
├───assistant.py                # Main assistant class
├───backlog/                    # Backlog management
├───clients/                    # Firebase and Pinecone clients
├───helpers/                    # Helper functions
├───intent_detection/           # Intent detection modules
├───models/                     # Data models
├───prompt_management/          # Prompt management modules
├───prompt_modules/             # Prompt modules for different features
├───services/                   # Services like embedding
├───tests/                      # Tests
├───tools/                      # Tools for various features
└───vector_stores/              # Vector stores for books and images
```

## Features

### Core Capabilities

- **Voice Interface**: Full speech-to-text and text-to-speech capabilities.
- **Intent Detection**: Modular intent detection using LLMs to understand user commands.
- **Tool Management**: A robust tool management system to extend the agent's functionality.
- **Prompt Management**: A modular system for managing prompts for different AI models and tasks.

### Main Features

- **AI Assistant**: General AI assistant capabilities.
- **Backlog & Reminders**:
    - Add, complete, delete, and list reminders.
    - View upcoming reminders.
    - Set custom days, recurrence, date, and time for reminders.
- **Book Reading**:
    - Read books.
    - RAG (Retrieval-Augmented Generation) on books to answer questions.
- **Face Recognition**: Recognizes faces.
- **Form Handling**:
    - Orchestrate, validate, and submit forms.
    - Interact with text fields within forms.
- **Health & Safety**:
    - Fall detection sensitivity settings (including for watchOS).
    - Toggle fall detection.
    - Emergency delay tool.
- **Location Services**:
    - Toggle location tracking.
    - Update location update interval.
    - Navigation tool.
- **Memory & History**:
    - Recall conversation history.
- **Media & Communication**:
    - Start video calls.
    - Query images.
- **OCR**:
    - Read text from images.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create environment file**:
   Create a `.env.local` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   LIVEKIT_URL=your_livekit_url
   LIVEKIT_API_KEY=your_livekit_api_key
   LIVEKIT_API_SECRET=your_livekit_api_secret
   # Add other necessary API keys for Firebase, Pinecone, etc.
   ```

3. **Run the assistant**:
   ```bash
   python agent.py
   ```

## Usage

The assistant responds to voice commands and can help with a wide variety of tasks. For example:

- "Add a reminder to take my medication at 8 am."
- "What's on my backlog for today?"
- "Read the first chapter of 'The Hobbit'."
- "Who is the main character in 'The Hobbit'?"
- "Start a video call with Jane."
- "Has my fall detection been enabled?"

## Development

### Adding New Tools

1. Create a new tool class in the `tools/` directory.
2. Inherit from the `BaseTool` class.
3. Add the tool to the `ToolManager` in `tools/tool_manager.py`.
4. If the tool requires a new prompt module, add it to the `prompt_modules/` directory and the `PromptModuleManager` in `prompt_management/prompt_module_manager.py`.
