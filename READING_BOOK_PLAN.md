# COMPLETE IMPLEMENTATION PLAN: Fix Book Reading to Read Verbatim (Not Summarize)

## 🎯 OBJECTIVE

Make the agent read book pages word-for-word like an audiobook narrator, instead of summarizing the content.

**Current Problem:**
```
User: "Read page 5"
Agent: "I've read page 5. It talks about photosynthesis..." ❌ WRONG (summarized)
```

**Desired Result:**
```
User: "Read page 5"
Agent: "Chapter 3: Photosynthesis. The process by which green plants..." ✅ CORRECT (reads full text)
```

---

## 📋 IMPLEMENTATION CHECKLIST

- [ ] **Step 1:** Add `session` property to Assistant class (5 min)
- [ ] **Step 2:** Set session reference in agent.py (5 min)
- [ ] **Step 3:** Update ReadBookTool to use session.say() (10 min)
- [ ] **Step 4:** Update book_reading.md prompt module (5 min)
- [ ] **Step 5:** Test the implementation (10 min)

**Total Time: 35 minutes**

---

## 🔧 STEP 1: Add Session Property to Assistant Class

### File: `assistant.py`

**What to do:** Add a `session` property to store the LiveKit session reference.

**Location:** In the `__init__` method of the `Assistant` class

**Code Change:**

```python
class Assistant(Agent):
    """AI Assistant with extensible tool management."""

    def __init__(self, user_id: str = None) -> None:
        # Existing code
        self.navigation_state = NavigationState()
        self.user_id = user_id
        self.firebase_client = FirebaseClient()
        
        # 🆕 ADD THIS LINE - Will be set when session starts
        self.session = None
        
        logger.info(f"Assistant initialized with user_id: {user_id}")

        # Rest of your existing code continues...
        self.tool_manager = ToolManager()
        self._register_tools()
        
        # Module manager code
        self.module_manager = PromptModuleManager()
        self.intent_detector = IntentDetector()
        self.current_modules = ["navigation", "memory_recall"]
        self.conversation_history = []
        
        # ... rest of __init__ continues unchanged
```

**Why:** This creates a placeholder that will be filled with the actual session object from agent.py.

---

## 🔧 STEP 2: Set Session Reference in agent.py

### File: `agent.py`

**What to do:** After creating the assistant, give it access to the session.

**Location:** In the `entrypoint` function, right after creating the Assistant

**Code Change:**

Find this section (around line 50-80):

```python
# Create agent session
session = AgentSession(
    stt=openai.STT(),
    llm=openai.LLM(model="gpt-4o-mini", temperature=0.2),
    tts=openai.TTS(voice=voice_preference),
    vad=ctx.proc.userdata["vad"],
)

logger.info(f"=== SESSION CREATED ===")

logger.info("=" * 50)
logger.info(f"🎯 Creating Assistant with user_id: {user_id}")
logger.info("=" * 50)

assistant = Assistant(user_id=user_id)

# 🆕 ADD THESE 2 LINES RIGHT HERE:
assistant.session = session
logger.info("✅ Session linked to assistant")

# Existing code continues...
async def _update_instructions_for_user_message(user_message: str):
    # ... rest of the code
```

**Complete section should look like:**

```python
session = AgentSession(
    stt=openai.STT(),
    llm=openai.LLM(model="gpt-4o-mini", temperature=0.2),
    tts=openai.TTS(voice=voice_preference),
    vad=ctx.proc.userdata["vad"],
)

logger.info(f"=== SESSION CREATED ===")

logger.info("=" * 50)
logger.info(f"🎯 Creating Assistant with user_id: {user_id}")
logger.info("=" * 50)

assistant = Assistant(user_id=user_id)

# 🆕 NEW: Link session to assistant
assistant.session = session
logger.info("✅ Session linked to assistant")

# 🆕 NEW: Define instruction update function
async def _update_instructions_for_user_message(user_message: str):
    # ... existing code continues unchanged
```

**Why:** This makes the session available to the assistant and all its tools via `self.agent.session`.

---

## 🔧 STEP 3: Update ReadBookTool to Use session.say()

### File: `tools/read_book_tool.py`

**What to do:** Replace the tool so it speaks content directly instead of returning it to the LLM.

**REPLACE THE ENTIRE `read_book` METHOD** with this new version:

```python
from livekit.agents import function_tool
from tools.base_tool import BaseTool
import logging
import asyncio

logger = logging.getLogger(__name__)


class ReadBookTool(BaseTool):
    """Tool for reading book pages aloud verbatim (audiobook style)."""
    
    def __init__(self):
        super().__init__("read_book")
        logger.info("ReadBookTool initialized")
    
    @function_tool()
    async def read_book(
        self,
        book_name: str,
        page_number: int = None,
        pages_to_read: int = 1,
        continue_reading: bool = False,
    ) -> str:
        """
        Read pages from a book ALOUD verbatim (audiobook narrator style).
        
        This tool speaks the book content directly through TTS, bypassing
        LLM summarization. The agent will read word-for-word like an audiobook.
        
        Args:
            book_name: Name of the book to read
            page_number: Starting page number (optional if continuing)
            pages_to_read: Number of pages to read (default: 1)
            continue_reading: If True, resume from last saved position
        
        Returns:
            Short confirmation message (actual content is spoken via TTS)
        """
        try:
            logger.info(
                f"📖 read_book called | book: {book_name} | "
                f"page: {page_number} | pages: {pages_to_read} | "
                f"continue: {continue_reading}"
            )
            
            # Get book content using your existing logic
            # (This part stays the same - however you currently retrieve book text)
            book_content = self._get_book_content(
                book_name=book_name,
                page_number=page_number,
                pages_to_read=pages_to_read,
                continue_reading=continue_reading
            )
            
            if not book_content:
                logger.warning(f"No content found for {book_name} page {page_number}")
                return f"Could not find '{book_name}' or page {page_number}. Please check the book name and page number."
            
            # 🆕 NEW: Check if we have access to session
            if not self.agent:
                logger.error("Tool not linked to agent")
                return "Error: Tool not properly initialized. Please contact support."
            
            if not self.agent.session:
                logger.error("Session not available on agent")
                return "Error: Voice session not available. Please try again."
            
            # 🆕 NEW: Speak the content directly via TTS (bypasses LLM)
            # This is the KEY change - we use session.say() instead of returning content
            logger.info(f"🎤 Speaking {len(book_content)} characters via session.say()")
            
            await self.agent.session.say(
                text=book_content,
                allow_interruptions=True,  # User can interrupt by speaking
                add_to_chat_ctx=False  # Don't add to chat history (too long)
            )
            
            logger.info(f"✅ Finished speaking content from {book_name}")
            
            # Return a SHORT confirmation to the LLM
            # The LLM will receive this, not the book content
            return (
                f"Now reading from '{book_name}', starting at page {page_number}. "
                f"The content is being read aloud."
            )
            
        except Exception as e:
            logger.error(f"❌ Error in read_book: {e}", exc_info=True)
            return f"Error reading book: {str(e)}"
    
    def _get_book_content(
        self,
        book_name: str,
        page_number: int,
        pages_to_read: int,
        continue_reading: bool
    ) -> str:
        """
        Retrieve book content from your storage/database.
        
        IMPORTANT: Keep your existing implementation here.
        This method should return the actual text content to be read.
        
        Returns:
            The full text content to be read aloud (not summarized)
        """
        # 🔍 YOUR EXISTING IMPLEMENTATION GOES HERE
        # Don't change this part - however you currently get book content
        
        # Example structure (replace with your actual implementation):
        # - Query your database/storage for the book
        # - Get the specified page(s)
        # - Return the full text content
        
        # Placeholder - replace with your actual implementation
        logger.warning("Using placeholder _get_book_content - implement your book retrieval logic")
        return f"This is placeholder content for {book_name}, page {page_number}. Implement actual book retrieval."
```

**IMPORTANT NOTES:**

1. **Keep your existing `_get_book_content()` logic** - Don't change how you retrieve book text, just keep that part as-is.

2. **The key change** is using `await self.agent.session.say(book_content)` instead of `return book_content`.

3. **Why this works:**
   - `return book_content` → LLM receives it → LLM summarizes → Bad ❌
   - `session.say(book_content)` → Goes directly to TTS → Full reading → Good ✅

---

## 🔧 STEP 4: Update book_reading.md Prompt Module

### File: `prompt_modules/book_reading.md`

**What to do:** Update the instructions to clarify that read_book speaks automatically.

**REPLACE THE ENTIRE FILE** with this content:

```markdown
## BOOK READING CAPABILITY

Help users listen to books being read aloud (audiobook style).

### How It Works

When the user asks to read a book, the `read_book` tool:
1. Retrieves the book content
2. **Automatically reads it aloud verbatim** via TTS
3. Returns a confirmation message to you

**CRITICAL:** You do NOT read the book content yourself. The tool handles it.

### Tool: read_book

```
read_book(book_name, page_number, pages_to_read, continue_reading)
```

**Parameters:**
- `book_name` (string): Name of the book
- `page_number` (int, optional): Starting page number
- `pages_to_read` (int, default=1): Number of pages to read
- `continue_reading` (bool, default=False): Resume from last position

### Your Role

When the tool is called, you will receive a confirmation message like:
"Now reading from 'Harry Potter', starting at page 5."

Your job is to:
1. ✅ Acknowledge the user naturally: "Okay, starting the book now" or "Here we go"
2. ✅ Stay quiet while the tool reads (don't interrupt)
3. ✅ After reading completes, ask: "Would you like me to continue reading?"

**DO NOT:**
- ❌ Try to read the book yourself
- ❌ Summarize the content
- ❌ Say things like "I'll read it now" and then speak the content
- ❌ Repeat what the tool is already reading

### User Intent Patterns

Users might say:
- "Read my book"
- "Continue reading [book name]"
- "Read page [number] from [book]"
- "Read chapter [number]"
- "Start the book"
- "Keep reading"

### Response Patterns

**When user asks to start reading:**
```
User: "Read Harry Potter page 5"
You: "Starting Harry Potter at page 5 for you."
[Tool automatically reads the content aloud]
```

**When reading completes:**
```
[Tool finishes reading]
You: "Would you like me to continue reading, or is there anything else I can help with?"
```

**If user interrupts:**
```
User: "Stop reading"
You: "Stopped. We were at page 7. Let me know if you'd like to continue later."
```

### Examples

**Example 1: Starting a book**
```
User: "Read my Harry Potter book"
Assistant: "Opening Harry Potter for you now."
[read_book tool speaks: "Chapter 1: The Boy Who Lived. Mr. and Mrs. Dursley..."]
[After reading completes]
Assistant: "Would you like me to continue to the next page?"
```

**Example 2: Continuing reading**
```
User: "Continue reading"
Assistant: "Continuing where we left off."
[read_book tool speaks the next section]
```

**Example 3: Specific page**
```
User: "Read page 42"
Assistant: "Going to page 42."
[read_book tool speaks page 42 content]
```

### Important Notes

- The `read_book` tool uses TTS to speak the book content directly
- You will NOT see the book content in your context
- You will only receive a confirmation message
- The reading happens automatically - you just confirm and wait
- User can interrupt at any time by speaking

### Comparison with rag_books_tool

- **read_book**: Reads pages aloud verbatim (audiobook mode)
- **rag_books_tool**: Searches book content to answer questions

Use `read_book` when user wants to **listen to the book**.
Use `rag_books_tool` when user wants to **search or ask questions** about the book.
```

**Why:** This clarifies for the LLM that it should NOT try to read the content itself.

---

## 🔧 STEP 5: Test the Implementation

### Test 1: Start Agent and Check Logs

```bash
python agent.py
```

**Expected logs on startup:**
```
=== SESSION CREATED ===
🎯 Creating Assistant with user_id: user_...
✅ Session linked to assistant
Assistant ready | Active modules: ['navigation', 'memory_recall']
```

✅ **Verify:** You see "Session linked to assistant" in the logs.

---

### Test 2: Request Book Reading

**In your app, say or type:**
```
"Read page 5 from Harry Potter"
```

**Expected logs:**
```
💾 Conversation item: user - Read page 5 from Harry Potter
🎯 Intent Detection | Result: Detected: book_reading
🔄 Module Change Detected | To: ['book_reading', 'navigation']
✅ Instructions Updated Successfully
📖 read_book called | book: Harry Potter | page: 5
🎤 Speaking 2847 characters via session.say()
✅ Finished speaking content from Harry Potter
```

**Expected behavior:**
1. Agent confirms: "Starting Harry Potter at page 5 for you."
2. Agent's voice reads the FULL page content word-for-word
3. After reading, agent asks: "Would you like me to continue?"

✅ **Verify:** 
- Agent reads the FULL content (not a summary)
- Voice is the same as normal agent voice
- User can interrupt by speaking

---

### Test 3: Verify No Summarization

**What to listen for:**

❌ **WRONG (Old behavior):**
```
Agent: "I've read page 5 for you. It talks about Harry living with his aunt and uncle..."
```

✅ **CORRECT (New behavior):**
```
Agent: "Starting Harry Potter at page 5."
[Pause]
Agent voice reads: "Mr. and Mrs. Dursley of number four, Privet Drive, were proud to say that they were perfectly normal, thank you very much. They were the last people you'd expect to be involved in anything strange or mysterious, because they just didn't hold with such nonsense..." 
[Continues reading full page]
```

---

### Test 4: Test Continue Reading

**Say:**
```
"Continue reading"
```

**Expected:**
- Agent says: "Continuing where we left off."
- Agent reads the next section

---

### Test 5: Test Interruption

**While agent is reading, say:**
```
"Stop"
```

**Expected:**
- Reading stops immediately
- Agent acknowledges: "Stopped. Let me know if you'd like to continue."

---

## 🐛 TROUBLESHOOTING

### Problem: "Tool not linked to agent" error

**Logs show:**
```
❌ Error: Tool not linked to agent
```

**Solution:**
Verify your `assistant.py` has the `on_enter` method that links tools:

```python
async def on_enter(self):
    """Called when agent enters the room/session."""
    logger.info("Assistant entered the room")
    
    # Link all tools to this agent
    for tool_name, tool_instance in self.tool_manager.tools.items():
        if hasattr(tool_instance, 'link_to_agent'):
            tool_instance.link_to_agent(self)
    
    # Set user_id for all tools
    self.tool_manager.set_user_id_for_all_tools(self.user_id)
    
    # ... rest of method
```

---

### Problem: "Session not available" error

**Logs show:**
```
❌ Error: Session not available on agent
```

**Solution:**
Check that `agent.py` has this line after creating the assistant:

```python
assistant = Assistant(user_id=user_id)
assistant.session = session  # ← This line must be present
```

---

### Problem: Agent still summarizes instead of reading

**Agent says:**
```
"I've read the page. It discusses..."
```

**Solution:**

1. Check that `book_reading.md` module is loaded:
   ```bash
   # Look for this in logs:
   Loaded module: book_reading
   ```

2. Check that intent detection picks up book reading:
   ```bash
   # Look for this in logs:
   🎯 Intent: Detected: book_reading
   ```

3. If intent detection fails, strengthen patterns in `intent_detector.py`:
   ```python
   "book_reading": [
       r"\b(book|chapter|page|continue reading|audiobook|novel|story)\b",
       r"\bread (the |my )?book\b",
       r"\bkeep reading\b",
       r"\bwhere (was|were) (I|we)\b.*\bread",
       r"\bstart (reading|the book)\b",  # ADD THIS
       r"\bopen (the )?book\b",  # ADD THIS
   ],
   ```

---

### Problem: Voice sounds different when reading

**Check your TTS configuration in `agent.py`:**

```python
session = AgentSession(
    stt=openai.STT(),
    llm=openai.LLM(model="gpt-4o-mini", temperature=0.2),
    tts=openai.TTS(voice=voice_preference),  # Same voice for all speech
    vad=ctx.proc.userdata["vad"],
)
```

The voice should be consistent because `session.say()` uses the same TTS configured in the session.

---

## 📊 EXPECTED RESULTS

### Before Implementation

| Metric | Value |
|--------|-------|
| Reading behavior | Summarizes |
| Words spoken | ~50-100 words (summary) |
| Reading time | 10-15 seconds |
| User experience | Frustrating - not getting full content |

### After Implementation

| Metric | Value |
|--------|-------|
| Reading behavior | Reads verbatim |
| Words spoken | Full page (500-2000+ words) |
| Reading time | 2-5 minutes per page |
| User experience | Excellent - true audiobook experience |

---

## 🎯 VERIFICATION CHECKLIST

After implementing all steps, verify:

- [ ] `assistant.session` is set in agent.py
- [ ] Agent startup shows "Session linked to assistant"
- [ ] Asking to read triggers book_reading module load
- [ ] Logs show "Speaking X characters via session.say()"
- [ ] Agent reads FULL content (not summary)
- [ ] Voice is consistent with normal agent voice
- [ ] User can interrupt reading by speaking
- [ ] "Continue reading" works correctly

---

## 📝 FILES MODIFIED SUMMARY

1. **assistant.py** - Added `self.session = None` in `__init__`
2. **agent.py** - Added `assistant.session = session` after creating assistant
3. **tools/read_book_tool.py** - Changed to use `await self.agent.session.say()`
4. **prompt_modules/book_reading.md** - Updated instructions to clarify tool speaks automatically

**Total files modified:** 4
**Total lines changed:** ~50 lines
**Implementation time:** 35 minutes

---

## 🚀 NEXT STEPS (Optional Enhancements)

### Enhancement 1: Add Reading Speed Control

```python
# In agent.py, modify TTS configuration:
tts=openai.TTS(
    voice=voice_preference,
    speed=0.9  # Slightly slower for comfortable listening (0.25-4.0)
)
```

### Enhancement 2: Chunk Very Long Content

```python
# In read_book_tool.py
def _chunk_content(self, content: str, max_chars: int = 2000) -> list:
    """Split long content into chunks at paragraph boundaries."""
    paragraphs = content.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) < max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

# Then in read_book:
chunks = self._chunk_content(book_content)
for chunk in chunks:
    await self.agent.session.say(chunk, allow_interruptions=True)
    await asyncio.sleep(0.5)  # Brief pause between chunks
```

### Enhancement 3: Track Reading Position

```python
# Store position in Firebase or memory
class ReadBookTool(BaseTool):
    def __init__(self):
        super().__init__("read_book")
        self.reading_positions = {}  # user_id -> (book, page, position)
    
    async def read_book(self, ..., continue_reading=False):
        if continue_reading:
            position = self.reading_positions.get(self.user_id)
            if position:
                book_name, page, char_offset = position
                # Resume from this position
        
        # After reading, save position
        self.reading_positions[self.user_id] = (book_name, page, len(book_content))
```

---

## ✅ SUCCESS CRITERIA

Your implementation is successful when:

1. ✅ Agent reads book pages word-for-word (no summarization)
2. ✅ Full page content is spoken aloud (not truncated)
3. ✅ Voice remains consistent (same as agent's normal voice)
4. ✅ User can interrupt reading at any time
5. ✅ "Continue reading" resumes from correct position
6. ✅ No errors in logs related to session access
7. ✅ Reading experience feels like an audiobook narrator

---

## 🎓 HOW IT WORKS

### The Key Difference

**OLD (Broken) Flow:**
```
User: "Read page 5"
    ↓
Tool returns book content (2000 words)
    ↓
LLM receives: "Here's the book content: [2000 words]"
    ↓
LLM thinks: "That's too long, I'll summarize"
    ↓
LLM outputs: "I've read page 5. It discusses..." (50 words)
    ↓
TTS speaks the summary
    ↓
User hears: Summary only ❌
```

**NEW (Fixed) Flow:**
```
User: "Read page 5"
    ↓
Tool gets book content (2000 words)
    ↓
Tool calls: await session.say(book_content)
    ↓
Content bypasses LLM completely
    ↓
Goes directly to TTS
    ↓
TTS speaks all 2000 words verbatim
    ↓
User hears: Full content ✅
    ↓
Tool returns to LLM: "Reading page 5" (short confirmation)
    ↓
LLM just acknowledges
```

### Why session.say() Works

- `session.say(text)` sends text **directly to TTS**
- It **bypasses the LLM** completely
- LLM never sees the book content (so can't summarize it)
- Same TTS voice as normal agent speech
- Can be interrupted just like normal speech

---

## 📞 SUPPORT

If you encounter issues:

1. Check logs for error messages
2. Verify all 5 steps completed
3. Review troubleshooting section
4. Ensure tools are linked correctly
5. Test with a short book passage first

---

**Good luck with your implementation!** 📚🎤

You're building an excellent audiobook feature for your elderly care app. This will greatly enhance the user experience!
