# LiveKit AI Assistant

A modular AI assistant built with LiveKit that provides weather information, time utilities, calculations, and user preference management.

## Project Structure

```
├── main.py                 # Main entry point
├── assistant.py           # Main assistant class
├── tools/                 # Tool modules
│   ├── __init__.py       # Package initialization
│   ├── weather.py        # Weather lookup functionality
│   ├── time_utils.py     # Time utilities
│   ├── calculator.py     # Mathematical calculations
│   └── preferences.py    # User preferences management
├── requirements.txt      # Python dependencies
├── .env.local           # Environment variables (create this)
└── README.md            # This file
```

## Features

- **Weather Lookup**: Get current weather information for any location
- **Time Utilities**: Get current time in different timezones
- **Calculator**: Perform safe mathematical calculations
- **User Preferences**: Save and retrieve user preferences across conversations
- **Voice Interface**: Full speech-to-text and text-to-speech capabilities

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
   ```

3. **Run the assistant**:
   ```bash
   python main.py
   ```

## Usage

The assistant responds to voice commands and can help with:

- Weather queries: "What's the weather in London?"
- Time requests: "What time is it in EST?"
- Calculations: "What's 15 times 23?"
- Preferences: "Remember that my favorite color is blue"

## Development

### Adding New Tools

1. Create a new tool class in the `tools/` directory
2. Inherit from a base class and use the `@function_tool()` decorator
3. Add the tool to `tools/__init__.py`
4. Import and inherit from the tool in `assistant.py`

### Example Tool Structure

```python
from livekit.agents import RunContext, ToolError, function_tool

class MyTool:
    @function_tool()
    async def my_function(self, context: RunContext, param: str) -> str:
        """Tool description."""
        try:
            # Tool logic here
            return result
        except Exception as e:
            raise ToolError("Error message") from e
```

## Notes

- The weather tool currently uses mock data. Replace with a real weather API for production use.
- The time tool uses local system time. Consider using proper timezone libraries for accurate timezone conversion.
- The calculator uses `eval()` with restricted builtins for safety, but consider using a proper math expression parser for production.