# Voice Agent Test Framework

A simple, powerful testing framework for your LiveKit voice agent. Test your agent's intelligence without writing complex code.

---

## What Does It Do?

Tests your voice agent end-to-end:
- ✅ Does it understand what users want? (Intent detection)
- ✅ Does it call the right tools? (Tool selection)
- ✅ Does it extract information correctly? (Parameter parsing)

**No audio needed** - Tests text-to-text, making it fast and cheap.

---

## Quick Start

### 1. Generate Test Variations

Create one example (seed), generate many variations automatically:

```bash
python3 -m tests.cli.commands generate \
  --module backlog \
  --seed-file tests/seeds/backlog_seeds.json \
  --count 10
```

**Input:** 1 seed test
**Output:** 11 total tests (1 seed + 10 AI-generated variations)

### 2. Run Tests

```bash
# Test with mock mode (fast, free)
python3 -m tests.cli.commands test --module backlog --mode mock

# Test with real mode (slow, validates actual agent)
python3 -m tests.cli.commands test --module backlog --mode real
```

### 3. Read Results

Check the generated report:
```bash
cat tests/results/backlog_real_report.md
```

---

## How It Works

```
┌─────────────────────────────────────────────────┐
│  1. Create Seed Test (You)                     │
│     "remind me to call mom at 3pm"             │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  2. Generate Variations (AI)                    │
│     - "set a reminder to ring mom at 3"        │
│     - "don't let me forget to call mom at 3pm" │
│     - "I need to call my mother at 3 o'clock"  │
│     ... (7 more)                                │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  3. Run Tests (Framework)                       │
│     For each test:                              │
│     - Send text to agent                        │
│     - Check if correct tool called              │
│     - Verify parameters extracted               │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  4. Get Report                                  │
│     ✅ Passed: 10/11 (90.9%)                    │
│     ❌ Failed: 1 test (show details)            │
│     📊 Performance: 5.5s avg per test           │
└─────────────────────────────────────────────────┘
```

---

## File Structure

```
tests/
├── seeds/                    # Your example tests
│   └── backlog_seeds.json   # 1-3 hand-written examples
│
├── variations/               # AI-generated tests
│   └── backlog_variations.json  # 10-20 variations per seed
│
├── results/                  # Test reports
│   └── backlog_real_report.md   # Easy-to-read results
│
├── cli/
│   └── commands.py          # Main commands (test, generate)
│
├── adapters/                # Connects to your agent
│   └── livekit_adapter.py  # LiveKit integration
│
└── config.yaml              # Framework settings
```

---

## Creating Seed Tests

Seed tests are JSON files with expected behavior:

**File:** `tests/seeds/backlog_seeds.json`

```json
[
  {
    "id": "seed_001",
    "input": "remind me to call mom at 3pm",
    "category": "basic_reminders",
    "expected": {
      "intent": {
        "modules": ["backlog"],
        "confidence": 0.7
      },
      "tool": "add_reminder",
      "params": {
        "title": "call mom",
        "scheduled_time": "15:00"
      }
    },
    "metadata": {
      "description": "Basic reminder with specific time"
    }
  }
]
```

**What each field means:**
- `input`: What the user says
- `category`: Group similar tests
- `expected.intent.modules`: Which modules should activate
- `expected.tool`: Which tool should be called
- `expected.params`: What information should be extracted

---

## Configuration

**File:** `tests/config.yaml`

```yaml
# Which agent to test
adapter:
  type: livekit
  user_id: test_user_123
  use_llm_intent: true  # Use AI for intent detection

# Test generation settings
generation:
  llm_strategy:
    model: gpt-4o-mini
    temperature: 0.7
    variations_per_request: 10

# Test execution settings
execution:
  mock_mode:
    enabled: true
    
  real_mode:
    enabled: true
    model: gpt-4o-mini
    temperature: 0.2
    timeout: 30
```

---

## Test Modes

### Mock Mode (Fast & Free)
- Tests intent detection only
- No actual LLM calls to your agent
- Uses expected values from test file
- **Speed:** ~100ms per test
- **Cost:** Free

```bash
python3 -m tests.cli.commands test --module backlog --mode mock
```

### Real Mode (Slow & Validates Everything)
- Tests full agent pipeline
- Actually calls your agent's LLM
- Tests tool selection and parameters
- **Speed:** ~5000ms per test
- **Cost:** ~$0.003 per test

```bash
python3 -m tests.cli.commands test --module backlog --mode real
```

**When to use which:**
- **Mock:** Daily development, quick checks
- **Real:** Before deploying, validating prompts

---

## Understanding Results

### Report Structure

```markdown
# Test Report: backlog

## Summary
- Total: 11 tests
- Passed: 10 ✅
- Failed: 1 ❌
- Success Rate: 90.9%

## Failed Tests
Test #1: "I should call my mom at 3-ish"
- Expected tool: add_reminder
- Actual tool: start_video_call
- Issue: Ambiguous phrasing confused agent
```

### What to do with failures:

1. **Real bug?** Fix your agent's prompt or logic
2. **Test too strict?** Update expected values
3. **Ambiguous input?** Both answers valid? Update test to accept either

---

## Common Workflows

### Daily Development
```bash
# Quick check before committing code
python3 -m tests.cli.commands test --module backlog --mode mock
```

### Before Deployment
```bash
# Full validation
python3 -m tests.cli.commands test --module backlog --mode real
python3 -m tests.cli.commands test --module navigation --mode real
```

### Testing New Prompts
```bash
# 1. Edit your prompt
nano prompt_modules/backlog.md

# 2. Test immediately
python3 -m tests.cli.commands test --module backlog --mode real

# 3. Check results
cat tests/results/backlog_real_report.md
```

### Adding New Test Coverage
```bash
# 1. Create seed file
nano tests/seeds/navigation_seeds.json

# 2. Generate variations
python3 -m tests.cli.commands generate \
  --module navigation \
  --seed-file tests/seeds/navigation_seeds.json \
  --count 10

# 3. Run tests
python3 -m tests.cli.commands test --module navigation --mode real
```

---

## Cost & Performance

### Test Generation
- **Cost:** ~$0.001 per variation
- **Speed:** ~2 seconds for 10 variations
- **10 tests = $0.01**

### Test Execution (Real Mode)
- **Cost:** ~$0.003 per test
- **Speed:** ~5 seconds per test
- **100 tests = $0.30**

### Tips to Save Money
1. Use mock mode during development
2. Generate variations once, run tests many times
3. Start with 5-10 tests per module

---

## Troubleshooting

### "No tool was called"
**Problem:** Agent didn't call any tool
**Fix:** Check if tools are registered in your agent

### "Intent detection failed"
**Problem:** Wrong modules detected
**Fix:** 
- Check `intent_detection/module_definitions.py`
- Update module descriptions
- Check `prompt_modules/` for clarity

### "Tests taking too long"
**Problem:** Real mode is slow
**Fix:** 
- Use mock mode for quick checks
- Reduce number of tests
- Run tests in parallel (future feature)

### "Import errors"
**Problem:** Can't find test modules
**Fix:** Run from repo root: `python3 -m tests.cli.commands ...`

---

## Advanced Features

### Custom Test Expectations

Test for multiple valid tools:
```json
{
  "expected": {
    "tool": ["add_reminder", "start_video_call"]
  }
}
```

Test for partial parameter match:
```json
{
  "expected": {
    "params": {
      "title": "call"  // Matches "call mom", "call dad", etc.
    }
  }
}
```

### Filtering Tests

Run specific test by ID:
```bash
python3 -m tests.cli.commands test --module backlog --test-id seed_001
```

### Custom Report Formats

Add to `config.yaml`:
```yaml
reporting:
  markdown:
    enabled: true
    show_passed_tests: false  # Hide passing tests
```

---

## Best Practices

### 1. Start Small
- 2-3 seed tests per module
- Generate 5-10 variations each
- Expand coverage gradually

### 2. Test Edge Cases
Include in your seeds:
- Typos: "remnd me"
- Vague times: "later", "soon"
- Ambiguous: "call mom" (video call or reminder?)
- Edge times: "midnight", "noon"

### 3. Keep Tests Updated
- Add failing user queries as new tests
- Update expectations when agent improves
- Delete obsolete tests

### 4. Use Descriptive Categories
```json
{
  "category": "basic_reminders",  // ✅ Good
  "category": "test1",            // ❌ Bad
}
```

---

## Getting Help

### Check Logs
```bash
tail -f tests/test_framework.log
```

### Debug Mode
```bash
python3 -m tests.cli.commands test --module backlog --mode real --verbose
```

### Common Issues
- Module not found? Check `tests/__init__.py` exists
- Agent not initializing? Check `tests/config.yaml` settings
- Tools not loading? Check `tests/adapters/livekit_adapter.py`

---

## What's Next?

Your framework is production-ready! Consider:

1. **More coverage:** Test navigation, video calls, settings
2. **CI/CD:** Run tests automatically on code changes
3. **LLM Judge:** Evaluate response quality with AI
4. **Hybrid mode:** 90% mock + 10% real = fast & accurate

---

## Summary

```bash
# Generate tests (once)
python3 -m tests.cli.commands generate --module backlog --seed-file tests/seeds/backlog_seeds.json --count 10

# Run tests (many times)
python3 -m tests.cli.commands test --module backlog --mode real

# Check results
cat tests/results/backlog_real_report.md
```
