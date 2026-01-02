
# Multi-Agent Voice Assistant Test Framework

A comprehensive testing framework for the multi-agent voice assistant system. Tests agent routing, tool selection, handoffs, and end-to-end conversation flows.


## 🎯 Features

- ✅ **Test Generation**: AI-powered test variation generation from seed cases
- ✅ **Mock Mode**: Fast, free testing using expected values
- ✅ **Real Mode**: Full pipeline testing with actual LLM calls
- ✅ **Multi-Agent Testing**: Tests orchestrator routing, specialist agents, and handoffs
- ✅ **Component Testing**: Individual testers for tools, routing, and handoffs
- ✅ **Markdown Reports**: Auto-generated, human-readable test reports
- ✅ **CSV/JSON Support**: Easy test data management for non-technical users

---

## 📁 Directory Structure

```
tests/
├── seed_data/              # Hand-written seed test cases (CSV)
│   ├── health_seeds.csv
│   ├── backlog_seeds.csv
│   ├── navigation_seeds.csv
│   ├── settings_seeds.csv
│   ├── books_seeds.csv
│   ├── image_seeds.csv
│   ├── form_seeds.csv
│   └── video_call_seeds.csv
│
├── generated_data/         # AI-generated test variations (JSON)
│   ├── health_tests.json (18 tests)
│   ├── backlog_tests.json (18 tests)
│   └── ... (144 total tests)
│
├── reports/                # Generated markdown reports
│   └── {agent}_{mode}_{timestamp}.md
│
├── core/                   # Framework core
│   ├── interfaces.py       # Test interfaces & data structures
│   ├── exceptions.py       # Custom exceptions
│   └── config.py          # Configuration manager
│
├── fixtures/               # Test setup
│   └── agent_adapter.py   # Multi-agent system adapter
│
├── storage/                # Test data storage
│   ├── json_storage.py
│   └── csv_storage.py
│
├── generation/             # Test generation
│   ├── generator.py       # Main generator
│   └── llm_strategy.py    # LLM-based variation strategy
│
├── execution/              # Test execution
│   ├── test_executor.py   # Main executor
│   └── modes/
│       ├── mock_mode.py
│       └── real_mode.py
│
├── evaluators/             # Component testers
│   ├── tool_tester.py     # Tool selection validation
│   ├── routing_tester.py  # Agent routing validation
│   └── handoff_tester.py  # Agent handoff validation
│
├── reporting/              # Report generation
│   └── markdown_formatter.py
│
├── cli/                    # Command-line interface
│   └── commands.py
│
├── config.yaml            # Framework configuration
└── README.md              # This file
```

---

## 🚀 Quick Start

### 1. Generate Test Variations

Generate test variations from seed cases:

```bash
# Estimate cost first
python -m tests.cli.commands generate \
  --agent health \
  --seed-file tests/seed_data/health_seeds.csv \
  --count 5 \
  --estimate-only

# Generate tests (~$0.01 per agent)
python -m tests.cli.commands generate \
  --agent health \
  --seed-file tests/seed_data/health_seeds.csv \
  --count 5
```

### 2. Run Tests

Run tests in mock mode (fast, free):

```bash
python -m tests.cli.commands test \
  --agent health \
  --mode mock
```

Run tests in real mode (slow, costs money):

```bash
python -m tests.cli.commands test \
  --agent health \
  --mode real
```

### 3. View Reports

```bash
cat tests/reports/health_mock_*.md
```

---

## 📊 Test Modes

### Mock Mode (Fast & Free)
- Uses expected values from test cases
- No LLM calls
- Speed: ~0-1ms per test
- Cost: $0
- Use for: Daily development, quick validation

```bash
python -m tests.cli.commands test --agent health --mode mock
```

### Real Mode (Comprehensive)
- Actual LLM calls through multi-agent system
- Tests full pipeline including routing, handoffs, tool calls
- Speed: ~3-5 seconds per test
- Cost: ~$0.003-0.01 per test
- Use for: Pre-deployment validation, regression testing

```bash
python -m tests.cli.commands test --agent health --mode real
```

---

## 🧪 What Gets Tested

### Agent Routing
- Does orchestrator route to correct specialist agent?
- Example: "What's my blood pressure?" → Routes to HealthAgent

### Tool Selection
- Does agent call the correct tool?
- Example: "What's my blood pressure?" → Calls `get_specific_metric`

### Agent Handoffs
- Do agent transitions work correctly?
- Example: Orchestrator → HealthAgent → Orchestrator

### Tool Parameters
- Are tool parameters extracted correctly?
- Example: `get_specific_metric(metric_type="bloodPressure", period="today")`

---

## 📝 Creating Seed Tests

Seed tests are CSV files with expected behaviors. Easy for non-technical users to edit!

**Example:** `tests/seed_data/health_seeds.csv`

```csv
id,agent,input,expected,metadata
health_seed_001,health,"How am I doing today?","{""tool"": ""get_health_summary"", ""params"": {""period"": ""today""}}","{""description"": ""Basic health summary request""}"
```

**CSV Format:**
- `id`: Unique test identifier
- `agent`: Which agent should handle (health, backlog, settings, etc.)
- `input`: User's spoken input
- `expected`: JSON with expected tool and parameters
- `metadata`: JSON with test description

---

## 🤖 Generating Variations

The framework uses LLMs to generate realistic variations:

```bash
python -m tests.cli.commands generate \
  --agent health \
  --seed-file tests/seed_data/health_seeds.csv \
  --count 10
```

**Input:** 3 seed tests  
**Output:** 33 total tests (3 seeds + 30 variations)  
**Cost:** ~$0.03

**Generated variations include:**
- Different phrasings ("How am I?" vs "How's my health?")
- Casual vs formal language
- Elderly user speech patterns
- Speech recognition errors
- Edge cases

---

## 📈 Understanding Reports

Reports include:

### Summary Statistics
- Total tests, passed, failed
- Success rate, average score
- Performance metrics

### Failed Test Details
- Which tester failed (tool, routing, handoff)
- Expected vs actual values
- Error messages

### Performance Metrics
- Total duration, average per test
- Slowest and fastest tests

**Example Report:** `tests/reports/health_mock_2025-12-18.md`

---

## 💰 Cost Management

### Generation Costs
- ~$0.001 per variation
- 10 variations per seed = ~$0.01
- 8 agents × 3 seeds × 10 variations = ~$0.24 total

### Execution Costs

| Mode | Cost per Test | 100 Tests | 1000 Tests |
|------|---------------|-----------|------------|
| **Mock** | $0 | $0 | $0 |
| **Real** | ~$0.005 | ~$0.50 | ~$5.00 |

### Cost Limits

Set in `tests/config.yaml`:

```yaml
generation:
  cost_limits:
    max_cost_per_run: 5.00  # dollars
    warn_threshold: 2.00
```

---

## 🔧 Configuration

**File:** `tests/config.yaml`

```yaml
# Test execution modes
execution:
  mock_mode:
    enabled: true
  real_mode:
    enabled: true
    model: gpt-4o-mini
    temperature: 0.2

# Test generation
generation:
  llm_strategy:
    model: gpt-4o-mini
    temperature: 0.7
    variations_per_seed: 10

# Reporting
reporting:
  markdown:
    enabled: true
    show_passed_tests: false  # Only show failures
```

---

## 🎯 Best Practices

### 1. Start with Mock Mode
```bash
# Daily development
python -m tests.cli.commands test --agent health --mode mock
```

### 2. Test Critical Paths in Real Mode
```bash
# Before deployment
python -m tests.cli.commands test --agent health --mode real
```

### 3. Keep Seed Tests Simple
- 2-3 seeds per agent
- Cover common use cases
- Generate variations for edge cases

### 4. Update Tests Continuously
- Add failing user queries as new seeds
- Regenerate variations after prompt changes
- Track success rates over time

---

## 📚 Available Agents

| Agent | Tests | Description |
|-------|-------|-------------|
| **health** | 18 | Health data queries, morning summaries |
| **backlog** | 18 | Reminder management (view, complete, delete) |
| **navigation** | 18 | Screen navigation commands |
| **settings** | 18 | Device settings (fall detection, location) |
| **books** | 18 | Book reading, content Q&A |
| **image** | 18 | Photo search and retrieval |
| **form** | 18 | Reminder creation via forms |
| **video_call** | 18 | Video call initiation |

**Total:** 144 tests across 8 agents

---

## 🔄 Workflow Examples

### Daily Development
```bash
# Fast validation (free)
python -m tests.cli.commands test --agent health --mode mock
```

### Before Deployment
```bash
# Test all agents in mock mode (fast)
for agent in health backlog navigation settings books image form video_call; do
  python -m tests.cli.commands test --agent $agent --mode mock
done

# Test critical agents in real mode
python -m tests.cli.commands test --agent health --mode real
python -m tests.cli.commands test --agent backlog --mode real
```

### After Prompt Changes
```bash
# Regenerate and test
python -m tests.cli.commands generate --agent health --seed-file tests/seed_data/health_seeds.csv --count 10 --regenerate
python -m tests.cli.commands test --agent health --mode real
```

---

## 🐛 Troubleshooting

### Test file not found
```bash
# Generate tests first
python -m tests.cli.commands generate --agent health --seed-file tests/seed_data/health_seeds.csv
```

### Agent initialization fails
```bash
# Check environment variables
echo $OPENAI_API_KEY
echo $AWS_ACCESS_KEY_ID
```

### All tests pass but they shouldn't
- You're in mock mode (uses expected values)
- Switch to real mode to test actual behavior

---

## 📖 Further Reading

- **Test Generation:** See `tests/generation/llm_strategy.py`
- **Component Testers:** See `tests/evaluators/`
- **Custom Metrics:** Extend `ITester` interface
- **Report Formats:** Extend `IReportFormatter` interface

---

## 🤝 Contributing

To add a new agent test suite:

1. Create seed file: `tests/seed_data/{agent}_seeds.csv`
2. Generate variations: `python -m tests.cli.commands generate --agent {agent}`
3. Run tests: `python -m tests.cli.commands test --agent {agent} --mode mock`

To add a new tester:

1. Implement `ITester` interface in `tests/evaluators/`
2. Add to `test_executor.py`
3. Update reports to show new tester results

*Built for AI Entourage elderly care voice assistant*
