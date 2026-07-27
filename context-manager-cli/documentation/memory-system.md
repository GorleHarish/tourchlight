# Memory System Deep Dive

Detailed technical documentation for Torchlight's context memory architecture.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Classes](#core-classes)
3. [Data Flow](#data-flow)
4. [Memory Tiers](#memory-tiers)
5. [Token Budget](#token-budget)
6. [Compression System](#compression-system)
7. [Retrieval System](#retrieval-system)
8. [Persistence](#persistence)
9. [Schema Reference](#schema-reference)
10. [Auto-tuning](#auto-tuning)
11. [Execution Feedback Loop](#execution-feedback-loop)
12. [Resource-Adaptive Configuration](#resource-adaptive-configuration)
13. [Improvement Recommendations by Resource Tier](#improvement-recommendations-by-resource-tier)
14. [Quick Wins (Zero Resource Cost)](#quick-wins-zero-resource-cost)
15. [Future Improvements](#future-improvements)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LLM API Request                              │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TieredMemory.get_context_for_llm()                                 │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │ System      │  │ Flashlight  │  │ Memory                     │  │
│  │ Prompt      │  │ Beam        │  │ ├─ Recent Messages         │  │
│  │ (~800 tok)  │  │ (~500 tok)  │  │ ├─ Tool Results           │  │
│  │             │  │             │  │ ├─ State Summary          │  │
│  │             │  │             │  │ └─ Retrieved Memory       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LM Studio / Ollama                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Response Processing                                                  │
│                                                                     │
│  add_user_message()      → TieredMemory.messages                     │
│  add_assistant_message() → TieredMemory.messages                     │
│  add_tool_result()       → TieredMemory.messages                     │
│                                                                     │
│  _update_state_from_message() → SessionState extraction             │
│  _capture_memory_artifacts()  → MemoryObjects + NeedleLedger         │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Compression (when threshold exceeded)                               │
│                                                                     │
│  Older messages → DevSessionSummarizer.rule_based()                  │
│                 → LLMStateExtractor.extract_and_merge() (parallel)    │
│                 → MemoryObject (compressed)                           │
│                 → System message with summary                         │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Persistence (session save)                                          │
│                                                                     │
│  SessionPersistence.save_session() → ~/.context-manager/sessions/      │
│  ProjectMemory.persist_session_state() → .context-memory.json         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Classes

### TieredMemory (`manager.py`)

The central memory manager that orchestrates all memory operations.

| Attribute | Type | Purpose |
|-----------|------|---------|
| `config` | `MemoryConfig` | Tunable thresholds |
| `messages` | `_EvictingDeque` | Ring buffer of Messages (max 1000) |
| `state` | `SessionState` | Extracted session state |
| `tokenizer` | `TokenCounter` | Token counting |
| `_embedder` | `Embedder` | Semantic embeddings |
| `_embedding_cache` | `dict` | LRU cache for embeddings (max 50) |
| `_llm_extractor` | `LLMStateExtractor` | LLM-powered state extraction |
| `_compression_cooldown` | `int` | Messages before next compression allowed |

#### Key Methods

| Method | Purpose |
|--------|---------|
| `add_user_message()` | Add user input to memory |
| `add_assistant_message()` | Add LLM response to memory |
| `add_tool_result()` | Add tool output to memory |
| `build_critical_context()` | Get errors/tests/tried for every prompt |
| `get_intent_for_retrieval()` | Get project intent for beam selection |
| `predict_next_tools()` | Predict likely next tools based on state |
| `get_active_file_hint()` | Get priority hint for active file |
| `should_compress()` | Check if compression needed (with cooldown) |
| `needs_summary()` | Check if summary needed (with cooldown) |
| `get_context_for_llm()` | Build message list for API |
| `build_working_set()` | Build context with metadata |
| `should_compress()` | Check if compression needed |
| `compress_recent_async()` | Compress older messages |
| `get_snapshot()` | Get memory statistics |

### MemoryConfig (`manager.py`)

Auto-tuning configuration for different context sizes.

```python
@dataclass
class MemoryConfig:
    max_tokens: int = 8000           # History budget (not total window)
    recent_window: int = 3           # Messages kept verbatim
    recent_tokens: int = 2000        # Token budget for recent
    compression_threshold: float = 0.7  # When to start compressing
    summary_trigger_tokens: int = 6000  # When to trigger full compression
    message_compact_threshold: int = 500  # Per-message truncate limit
    tool_result_budget_fraction: float = 0.35  # % of budget for tool results
    summary_budget_fraction: float = 0.20  # % of budget for summaries
```

### Message (`models.py`)

Single message unit stored in memory.

```python
@dataclass
class Message:
    role: MessageRole           # USER | ASSISTANT | SYSTEM | TOOL_RESULT
    content: str                # Message text
    timestamp: datetime         # When created
    token_count: int           # Cached token count
    content_chunks: list        # Structured content pieces
    metadata: dict             # Tool name, etc.
```

### SessionState (`models.py`)

Extracted session state that survives compression.

```python
@dataclass
class SessionState:
    # Core
    intent: str                 # Project goal
    current_task: str           # Current task description
    next_steps: list[str]      # Pending actions

    # File tracking
    files_modified: list[str]  # Files written
    files_read: list[str]      # Files accessed

    # Decisions
    decisions: list[str]        # General decisions
    arch_decisions: list[str]  # Architectural decisions (high value)

    # Dev-session specific
    tech_stack: list[str]       # Detected languages/frameworks
    failing_tests: list[str]    # Currently failing tests
    errors_seen: list[str]      # Error signatures
    dependencies_added: list[str]  # Packages installed
    tried_and_failed: list[str]   # Failed approaches
    active_file: str            # Current file being edited
    current_blocker: str        # Current blocker description

    # Long-term memory
    semantic_context: list[str]  # Project rules
    needle_ledger: list[MemoryNeedle]  # Exact values (files, symbols)
    memory_objects: list[MemoryObject]  # Compressed summaries
```

### MemoryNeedle (`models.py`)

Exact-value entries that survive compression.

```python
@dataclass
class MemoryNeedle:
    kind: str           # "file" | "symbol" | "command" | "error"
    value: str         # The exact value
    source: str        # Where it came from
    weight: float      # Relevance weight (errors = 1.1, files = 1.0)
    timestamp: datetime
```

### MemoryObject (`models.py`)

Compressed message summary for retrieval.

```python
@dataclass
class MemoryObject:
    kind: str               # "tool" | "dialogue" | "summary"
    summary: str           # Short summary (320 chars)
    source: str            # Tool name or role
    file_paths: list[str] # Extracted file paths
    symbols: list[str]     # Extracted function/class names
    commands: list[str]    # Extracted commands
    errors: list[str]      # Extracted errors
    text: str              # Full text (1200 chars)
    score: float           # Relevance score
    embedding: list[float] # Semantic embedding
    timestamp: datetime
```

---

## Data Flow

### 1. Message Ingestion

```
User sends message
        │
        ▼
add_user_message(content)
        │
        ├──► _compact_content(content)  ← Truncate if > message_compact_threshold
        │
        ├──► Message(role=USER, content=..., token_count=...)
        │
        ├──► messages.append()  ← _EvictingDeque
        │
        ├──► _total_tokens += token_count
        │
        └──► _update_state_from_message(msg)
                    │
                    ├──► Extract tech_stack from content
                    ├──► Extract current_blocker from content
                    ├──► Extract tried_and_failed from content
                    └──► _capture_memory_artifacts(msg)
                                │
                                ├──► _append_needle("file", path)
                                ├──► _append_needle("symbol", name)
                                ├──► _append_needle("command", cmd)
                                └──► _append_needle("error", error)
```

### 2. Context Assembly for LLM

```
get_context_for_llm(query)
        │
        ▼
build_working_set(query)
        │
        ├──► Loop messages in reverse (newest first)
        │         │
        │         └──► If total + msg.token_count > budget: STOP
        │             │
        │             └──► truncated = True
        │
        ├──► If truncated: add state summary
        │         │
        │         └──► _build_state_summary()
        │                    │
        │                    └──► GOAL: X | STACK: Y | ERRORS: ...
        │
        └──► Build retrieval memory
                  │
                  └──► _build_retrieval_memory_details(query)
                            │
                            ├──► _rank_memory_objects(query)  ← Hybrid scoring
                            ├──► _rank_needles(query)          ← Lexical scoring
                            └──► project_memory.hybrid_search() ← Disk retrieval
```

### 3. Tool Result Processing

```
add_tool_result(content, tool_name)
        │
        ├──► Calculate hard cap based on context size
        │    (≤4k: 400, ≤8k: 700, >8k: 1200)
        │
        ├──► Apply tool_result_budget_fraction (35% of budget)
        │
        ├──► min(hard_cap, fraction) = max_tool_tokens
        │
        ├──► compress_with_budget(content, max_tool_tokens)
        │
        ├──► Message(role=TOOL_RESULT, metadata={tool_name})
        │
        └──► _update_state_from_message()
                    │
                    ├──► If READ_FILE: extract file paths, set active_file
                    ├──► If WRITE_FILE: extract file paths
                    └──► If RUN_COMMAND:
                              ├──► Extract failing_tests
                              ├──► Extract errors_seen
                              ├──► Extract dependencies_added
                              └──► Extract tech_stack
```

### 4. Message Format for LLM

Tool results are converted from `tool_result` role to `user` role with compact format:

```python
# Before (removed):
"""
⚙️ [SYSTEM NOTIFICATION - TOOL RESULT]:
READ_FILE returned the following data:
---
file contents
---
Please analyze this result and proceed.
"""

# After (~8 tokens overhead):
"[READ_FILE]\nfile contents"
```

### 5. Critical Context Injection

Every system prompt includes critical context when present:

```python
def build_critical_context(self) -> str:
    """Returns errors, failing tests, and tried-and-failed approaches."""
    parts = []
    
    if s.failing_tests:
        parts.append("CRITICAL - FAILING TESTS:")
        for t in s.failing_tests[:3]:
            parts.append(f"  - {t}")
        parts.append("These tests MUST pass after your changes.")
    
    if s.errors_seen:
        parts.append("ACTIVE ERRORS:")
        for e in s.errors_seen[-3:]:
            parts.append(f"  - {e}")
    
    if s.tried_and_failed:
        parts.append("DO NOT RE-SUGGEST:")
        for t in s.tried_and_failed[-4:]:
            parts.append(f"  - {t}")
    
    return "\n".join(parts)
```

**Output format:**
```
═══════════════════════════════════════════════════════
CRITICAL - FAILING TESTS:
  - test_auth_token_expired
  - test_refresh_token
These tests MUST pass after your changes.
ACTIVE ERRORS:
  - ImportError: No module named requests
DO NOT RE-SUGGEST:
  - Tried using JWT directly
  - Tried bcrypt for passwords
═══════════════════════════════════════════════════════
```

### 6. Intent-Aware Beam Selection

Beam query combines project intent + active file + current blocker:

```python
def get_intent_for_retrieval(self) -> str:
    parts = []
    if self.state.intent:
        parts.append(self.state.intent)
    if self.state.active_file:
        parts.append(f"current: {self.state.active_file}")
    if self.state.current_blocker:
        parts.append(f"blocked: {self.state.current_blocker}")
    return " | ".join(parts)
```

**Example query:** `"Build auth | current: auth.py | blocked: token validation"`

### 7. Tool Prediction

Predicts likely next tools based on session state:

```python
def predict_next_tools(self) -> list[str]:
    predictions = []
    
    if s.failing_tests:
        predictions.extend(["RUN_COMMAND", "READ_FILE"])
    elif s.errors_seen:
        predictions.extend(["GREP", "READ_FILE"])
    elif s.current_blocker:
        predictions.extend(["GREP", "READ_FILE"])
    
    if not s.files_read:
        predictions.append("READ_FILE")
    elif s.active_file:
        predictions.append("READ_FILE")
        predictions.append("WRITE_FILE")
    
    # Dedupe, return first 3
    return result[:3]
```

**Example output in system prompt:** `Likely next tools: RUN_COMMAND, READ_FILE`

---

## Memory Tiers

### In-Memory Tiers (TieredMemory.messages)

```
TieredMemory.messages (_EvictingDeque, maxlen=1000)
│
├─ [L1] Recent Buffer (config.recent_window messages)
│   └─ Full fidelity, verbatim
│   └─ Examples: last 2-3 messages
│
├─ [L2] Older Messages (compressed at threshold)
│   └─ [Earlier conversation summarized]
│   └─ Structured summary with:
│       • GOAL
│       • TECH STACK
│       • ARCH DECISIONS
│       • FAILING TESTS
│       • ERRORS SEEN
│       • TRIED & FAILED
│       • FILES MODIFIED
│
└─ [Evicted] Messages removed from deque
    └─ Persisted to ProjectMemory on session save
```

### Session State Tiers

```
SessionState (in-memory, survives compression)
│
├─ Scalars (single values)
│   ├─ intent
│   ├─ active_file
│   └─ current_blocker
│
├─ Lists (bounded, regex-extracted)
│   ├─ tech_stack (unbounded unique)
│   ├─ arch_decisions (capped at 20)
│   ├─ tried_and_failed (capped at 20)
│   ├─ errors_seen (capped at 10)
│   ├─ failing_tests (capped at 10)
│   ├─ dependencies_added (capped at 20)
│   ├─ files_modified (capped at 20)
│   └─ files_read (capped at 20)
│
├─ NeedleLedger (exact values)
│   └─ MemoryNeedle items (capped at 240)
│       ├─ file paths (weight: 1.0)
│       ├─ symbols (weight: 0.9)
│       ├─ commands (weight: 0.8)
│       └─ errors (weight: 1.1)
│
└─ MemoryObjects (compressed summaries)
    └─ MemoryObject items (capped at 120)
        └─ Hybrid scoring: lexical + semantic + recency
```

### Disk Tiers (ProjectMemory)

```
.context-memory.json (project root)
│
├─ facts (legacy format, backward compat)
├─ arch_decisions (unique merge)
├─ tried_and_failed (unique merge)
├─ tech_stack (unique merge)
├─ needle_ledger (last 300)
├─ memory_objects (last 160)
└─ last_updated

~/.context-manager/sessions/*.json (session files)
│
├─ name
├─ created
├─ project_path
├─ state (SessionState snapshot)
├─ messages (Message list)
└─ total_tokens
```

---

## Execution Feedback Loop

The execution feedback loop closes the critical gap between code changes and test verification.

### Why This Matters

```
Without feedback loops:
├── Model writes code
├── Doesn't know if tests pass or fail
├── Re-suggests broken approaches
└── No runtime feedback

With feedback loops:
├── Code change detected
├── Tests auto-run
├── Failures injected into context
└── Model sees exactly what broke
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Execution Feedback Loop                           │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐ │
│  │ WorkingMemory │    │  TestRunner  │    │ ExecutionFeedback   │ │
│  │              │    │              │    │      Loop           │ │
│  │ ├─ file_chg  │    │ ├─ pytest   │    │                    │ │
│  │ ├─ test_runs │    │ ├─ npm       │    │ on_tool_executed() │ │
│  │ └─ pending    │    │ ├─ cargo     │    │ build_feedback()   │ │
│  │              │    │ └─ detect()  │    │                    │ │
│  └──────────────┘    └──────────────┘    └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Components

#### TestRunner
Detects and runs tests for multiple frameworks:

| Framework | Command | Detection |
|-----------|---------|-----------|
| pytest | `pytest -v --tb=short` | `pyproject.toml`, `tests/` dir |
| npm | `npm test` | `package.json` |
| cargo | `cargo test` | `Cargo.toml` |

#### WorkingMemory
Tracks changes and test results across the session:

```python
class WorkingMemory:
    file_changes: list[FileChange]      # Files modified
    test_runs: list[TestRunResult]      # Test execution history
    pending_fixes: list[str]           # Unresolved failures
```

#### ExecutionFeedbackLoop
Orchestrates the feedback flow:

```python
# 1. Tool executed (WRITE_FILE, EDIT_FILE)
# 2. File change tracked
# 3. Related test file found
# 4. Tests run automatically
# 5. Results parsed and stored
# 6. Failure context injected into next prompt
```

### Test Result Format

```python
@dataclass
class TestResult:
    name: str                    # "test_auth_token_expired"
    status: TestStatus          # PASS, FAIL, ERROR, SKIP
    duration_ms: float
    error_message: Optional[str]  # "AssertionError: ..."
    file_path: Optional[str]     # "tests/test_auth.py"
    line_number: Optional[int]    # 42

@dataclass
class TestRunResult:
    command: str
    return_code: int
    duration_ms: float
    results: list[TestResult]
    
    @property
    def all_passed(self) -> bool
    @property
    def passed(self) -> int
    @property
    def failed(self) -> int
```

### Context Injection

After each code change, if tests fail:

```
==================================================
TEST RESULTS:
==================================================
✗ 1 FAILED, 0 ERRORS, 2 PASSED

FAILING TESTS:
  - test_auth_token_expired
    Error: AssertionError: assert token == None
    File: tests/test_auth.py
    Line: 42

RECENT CHANGES:
  - modified: src/auth.py
==================================================
```

### CLI Integration

The feedback loop is automatically initialized in `StreamingChatSession`:

```python
class StreamingChatSession:
    def __init__(self, ...):
        self._feedback_loop = ExecutionFeedbackLoop(
            project_root=self.project_path,
            enabled=True,
            auto_run=True,
            timeout=60,
        )
```

And hooked into all tool execution paths:

```python
async def _execute_tool_with_approval(...):
    # ... tool execution ...
    
    # Auto-run tests after code changes
    test_result = self._feedback_loop.on_tool_executed(
        name, params, result.output
    )
    
    if test_result and not test_result.all_passed:
        feedback = self._feedback_loop.build_feedback_context()
        self.memory.add_tool_result(feedback, tool_name="TEST_FEEDBACK")
```

### Resource Impact

| Component | RAM | CPU | Latency |
|-----------|-----|-----|---------|
| WorkingMemory | ~5MB | Negligible | 0 |
| TestRunner | 0 | Medium (test run) | 1-60s |
| Feedback injection | 0 | Negligible | 0 |

### Configuration

```python
# Default configuration
ExecutionFeedbackLoop(
    project_root=Path.cwd(),
    enabled=True,           # Can be disabled
    auto_run=True,          # Auto-run tests after WRITE_FILE
    timeout=60,            # Max test execution time
)
```

### Test Coverage

22 test cases covering:
- WorkingMemory operations
- TestRunner detection and parsing
- ExecutionFeedbackLoop flow
- Context building
- Edge cases (no framework, empty results, etc.)

---

## Token Budget

### Allocation for 4k Context

```
4096 total context window
│
├── System prompt (~800 tokens)
│   ├─ SYSTEM_PROMPT (~400 tokens)
│   ├─ PROTOCOL_PROMPT (~200 tokens)
│   └─ Tool instructions (~200 tokens)
│
├── Flashlight beam (~500 tokens)
│   └─ 1 file × 50 lines for ≤5k context
│
├── Safety margin (512 tokens)
│   └─ Headroom for response generation
│
└── Available for memory (~2284 tokens)
    │
    ├── recent_tokens (35% = ~800 tokens)
    │   └─ Last 2-3 messages verbatim
    │
    ├── summary_budget (20% = ~456 tokens)
    │   └─ Compressed summaries
    │
    └── retrieval_budget (12% = ~274 tokens)
        └─ Retrieved memory + needles
```

### Auto-tuned Budgets by Context Size

| Parameter | ≤2k | ≤4k | ≤8k | >8k |
|----------|-----|-----|-----|-----|
| Safety margin | 256 | 512 | 768 | 1024 |
| recent_window | 1 | 2 | 3 | 5 |
| recent_tokens | 40% | 35% | 25% | 20% |
| compression_threshold | 0.5 | 0.6 | 0.7 | 0.7 |
| summary_trigger_tokens | 40% | 50% | 75% | 75% |

---

## Compression System

### Trigger Conditions

```python
should_compress() → total_tokens > max_tokens * compression_threshold
# Example: 4096 * 0.6 = 2458 tokens triggers compression

needs_summary() → total_tokens > summary_trigger_tokens
# Example: 4096 * 0.5 = 2048 tokens triggers full summary
```

### Compression Flow

```
compress_recent_async()
        │
        ├──► Check: len(messages) > recent_window
        │
        ├──► Split messages:
        │    recent = last N messages (keep verbatim)
        │    older = all other messages
        │
        ├──► Parallel execution (asyncio.gather):
        │    │
        │    ├──► compress_fn(older)  ← DevSessionSummarizer.rule_based()
        │    │    │
        │    │    └──► Extract: GOAL, TECH STACK, ARCH DECISIONS,
        │    │              FAILING TESTS, ERRORS, TRIED & FAILED
        │    │
        │    └──► _llm_extractor.extract_and_merge()  ← LLM extraction
        │         │
        │         └──► 256 token JSON response with structured fields
        │
        ├──► _merge_summary_into_state()  ← Parse and merge
        │
        ├──► Create MemoryObject with summary
        │    └─ score = 1.4 (higher than normal)
        │
        ├──► Replace messages deque with:
        │    summary_msg (SYSTEM) + recent messages
        │
        └──► Update _total_tokens
```

### LLM State Extractor

Runs in parallel with summarization for richer state extraction.

```
Input: Conversation excerpt (3000 chars max)
Output: Structured JSON

JSON schema:
{
  "intent": "<goal>",
  "active_file": "<file>",
  "current_blocker": "<blocker>",
  "arch_decisions": ["..."],
  "tried_and_failed": ["..."],
  "errors_seen": ["..."],
  "failing_tests": ["..."],
  "dependencies_added": ["..."],
  "tech_stack": ["..."],
  "next_steps": ["..."]
}

Settings:
- Temperature: 0.0 (deterministic)
- Max tokens: 300
- Timeout: 30 seconds
```

### Summary Merge Logic

```
_merge_summary_into_state()
        │
        ├──► Parse structured summary text
        │
        ├──► Section headers detected:
        │    ├─ ARCH DECISIONS:
        │    ├─ TRIED & FAILED:
        │    ├─ ERRORS SEEN:
        │    ├─ FAILING TESTS:
        │    ├─ TECH STACK:
        │    └─ DEPS ADDED:
        │
        ├──► For list fields: additive merge (regex + LLM)
        │
        ├──► For scalar fields: LLM wins only if empty
        │
        └──► Cap all lists to prevent unbounded growth
```

---

## Retrieval System

### Hybrid Search

```
build_working_set(query)
        │
        ▼
_build_retrieval_memory_details(query)
        │
        ├──► Normalize query terms
        │
        ├──► _rank_memory_objects(query, top_k=4)
        │    │
        │    ├──► Get query embedding (cached)
        │    │
        │    ├──► For each MemoryObject:
        │    │    ├─ Lexical score: term matching in summary/text
        │    │    ├─ Semantic score: cosine similarity of embeddings
        │    │    └─ Final: lexical + (0.35 * semantic) + (0.05 * score)
        │    │
        │    └──► Return top 4
        │
        ├──► _rank_needles(query, top_k=8)
        │    │
        │    └──► Lexical score + weight bonus
        │
        └──► project_memory.hybrid_search(query, embedding)
             │
             ├──► memory_objects: hybrid scoring
             ├──► needle_ledger: lexical + weight
             └──► facts (legacy): lexical only
```

### Embedding Cache

LRU cache to avoid redundant embedding calls.

```python
_embedding_cache: dict[str, list[float]]  # Key: first 100 chars
_embedding_cache_max_size = 50
```

---

## Persistence

### Session Persistence

```
SessionPersistence.save_session()
        │
        ├──► Serialize messages
        │    └─ role, content, timestamp, token_count, metadata
        │
        ├──► Serialize SessionState
        │    └─ All fields including needle_ledger and memory_objects
        │
        └──► Write to ~/.context-manager/sessions/{name}.json
```

### Project Memory Persistence

```
ProjectMemory.persist_session_state(state)
        │
        ├──► Load existing .context-memory.json
        │
        ├──► Unique merge arch_decisions (set union)
        ├──► Unique merge tried_and_failed (set union)
        ├──► Unique merge tech_stack (set union)
        │
        ├──► Append new needles (last 200)
        │    └─ Skip duplicates
        │
        ├──► Append new memory_objects (last 120)
        │    └─ Skip duplicates
        │
        ├──► Cap arrays
        │    ├─ needle_ledger: 300
        │    └─ memory_objects: 160
        │
        └──► Save .context-memory.json
```

### Loading Session State

On `TieredMemory.__init__()`:

```python
if project_memory:
    pm = project_memory.load()
    
    state.arch_decisions = pm.get("arch_decisions", [])
    state.tried_and_failed = pm.get("tried_and_failed", [])
    state.tech_stack = pm.get("tech_stack", [])
    state.semantic_context = pm.get("facts", [])  # Legacy inject
    state.needle_ledger = [...]  # From needle_ledger
    state.memory_objects = [...]  # From memory_objects
```

---

## Schema Reference

### `.context-memory.json` Schema

```json
{
  "facts": [
    {
      "text": "android studio is already available in system",
      "embedding": [],
      "timestamp": "2026-03-22T19:40:47.989114"
    }
  ],
  "arch_decisions": [
    "Using SQLite for simplicity over PostgreSQL"
  ],
  "tried_and_failed": [
    "Tried to use Docker but it wasn't installed"
  ],
  "tech_stack": [
    "Python",
    "FastAPI",
    "pytest"
  ],
  "needle_ledger": [
    {
      "kind": "file",
      "value": "src/main.py",
      "source": "READ_FILE",
      "weight": 1.0,
      "timestamp": "2026-03-26T10:00:00"
    }
  ],
  "memory_objects": [
    {
      "kind": "tool",
      "summary": "files: main.py, utils.py | errors: ImportError",
      "source": "READ_FILE",
      "file_paths": ["src/main.py", "src/utils.py"],
      "symbols": ["main", "setup"],
      "commands": [],
      "errors": ["ImportError: No module named 'requests'"],
      "text": "...",
      "score": 1.2,
      "embedding": [],
      "timestamp": "2026-03-26T10:00:00"
    }
  ],
  "created": "2026-03-21T15:05:55",
  "last_updated": "2026-03-26T10:00:00"
}
```

### Session File Schema

```json
{
  "name": "20260326_143052",
  "created": "2026-03-26T14:30:52",
  "project_path": "/path/to/project",
  "state": {
    "intent": "Fix authentication bug",
    "current_task": "Debug JWT validation",
    "arch_decisions": [...],
    "tech_stack": [...],
    "needle_ledger": [...],
    "memory_objects": [...]
  },
  "messages": [
    {
      "role": "user",
      "content": "fix the auth bug",
      "timestamp": "2026-03-26T14:30:55",
      "token_count": 8,
      "metadata": {}
    }
  ],
  "total_tokens": 1523
}
```

---

## Auto-tuning

### MemoryConfig.auto_tune()

Called at session initialization with total context window size and expected metadata overhead.

```python
@classmethod
def auto_tune(cls, max_tokens: int, metadata_overhead: int = 0) -> "MemoryConfig":
    # Calculate safety margin based on context size
    if max_tokens <= 2000:
        safety_margin = 256
    elif max_tokens <= 5000:  # Covers 4k models
        safety_margin = 512
    elif max_tokens <= 10000:
        safety_margin = 768
    else:
        safety_margin = 1024
    
    # History budget is what remains after overhead and safety margin
    history_budget = max(500, max_tokens - metadata_overhead - safety_margin)
    
    # Return config tuned for this budget
    return cls(
        max_tokens=history_budget,
        recent_window=...,      # Scales with size
        recent_tokens=...,      # Percentage of budget
        compression_threshold=...,  # Lower for small contexts
        ...
    )
```

### CLI Integration

The CLI calculates metadata overhead before creating MemoryConfig:

```python
def _calculate_metadata_overhead(self) -> int:
    # System prompt + tool instructions
    base_tokens = tokenizer.count(DEFAULT_SYSTEM_PROMPT + cli_suffix)
    
    # Beam overhead based on context size
    if max_tokens <= 5000:
        overhead = base_tokens + 600  # 1 file × 50 lines
    elif max_tokens <= 9000:
        overhead = base_tokens + 1500  # 2 files × 80 lines
    else:
        overhead = base_tokens + 3000  # 3 files × 120 lines
    
    return overhead

# Then:
memory_config = MemoryConfig.auto_tune(max_tokens, metadata_overhead=overhead)
```

---

## File Locations

| Component | Path |
|-----------|------|
| TieredMemory | `context_manager/memory/manager.py` |
| Models | `context_manager/memory/models.py` |
| Persistence | `context_manager/memory/persistence.py` |
| LLM Extractor | `context_manager/memory/llm_extractor.py` |
| Token Counter | `context_manager/memory/token_counter.py` |
| Summarizer | `context_manager/compression/summarizer.py` |
| Execution Feedback | `context_manager/execution/feedback_loop.py` |
| CLI Assembly | `context_manager/cli/main.py` |
| Project Memory | `.context-memory.json` (project root) |
| Sessions | `~/.context-manager/sessions/*.json` |
| Feedback Loop Tests | `context-manager-cli/tests/` |
| Memory Tests | `context-manager-cli/tests/` |

---

## Resource-Adaptive Configuration

The system adapts behavior based on available RAM and context window size.

### Resource Tiers

| Tier | RAM | Context | Use Case |
|------|-----|---------|----------|
| **Minimal** | ≤8GB | ≤4k | M1 Pro, budget laptops |
| **Standard** | 8-16GB | 4k-8k | Most developers |
| **Generous** | 16-32GB | 8k-16k | Workstations |
| **Heavy** | 32GB+ | 16k+ | Servers, high-end |

### Resource-Adaptive Features

#### Embedding Cache
- **All tiers**: Enabled by default
- **Minimal**: Max 50 entries, saves ~500ms per repeated query
- **Generous+**: Can increase to 200 entries

```python
# MemoryConfig per tier
if tier == "minimal":
    embedding_cache_max = 50
elif tier == "standard":
    embedding_cache_max = 100
else:
    embedding_cache_max = 200
```

#### LLM State Extraction
- **Minimal/Standard**: Disabled (regex-only extraction)
- **Generous+**: Enabled (parallel LLM call at compression)

```python
# LLM extractor enabled only on large contexts
enabled = max_tokens > 8000  # Only for 8k+
```

#### Compression Cooldown
- **Minimal**: 5 messages cooldown, prevents over-compression
- **Standard**: 3 messages cooldown
- **Generous**: No cooldown needed (larger context)

```python
# During cooldown, compression only triggers at 90% threshold
if self._compression_cooldown > 0:
    return self._total_tokens > self.config.max_tokens * 0.9
```

#### Tool Result Budget
- **Minimal**: 250-400 tokens per tool result
- **Standard**: 400-700 tokens per tool result
- **Generous**: 700-1200 tokens per tool result

```python
if max_tokens <= 2000:   _hard_cap = 250
elif max_tokens <= 4000: _hard_cap = 400
elif max_tokens <= 8000: _hard_cap = 700
else:                    _hard_cap = 1200
```

---

## Improvement Recommendations by Resource Tier

### Minimal (8GB RAM, 4k context)

**Goals:**
1. Maximize effective context usage
2. Prevent over-compression
3. Surface critical context (errors, tests) always

**Recommended Features:**
| Feature | Priority | Tokens Saved | Risk |
|---------|----------|--------------|------|
| Critical context injection | HIGH | ~100 | None |
| Intent-aware beam | HIGH | ~50 | Low |
| Tool prediction | MEDIUM | ~30 | None |
| Compression cooldown | HIGH | Prevents waste | Low |
| Embedding cache | HIGH | Latency | None |

**Avoid:**
- LLM state extraction (extra inference)
- Self-reflection loops (2-3x latency)
- Large embedding caches (RAM waste)
- Parallel compression (memory pressure)

**Configuration:**
```python
MemoryConfig(
    max_tokens=1800,          # 4k - 1024 overhead - 512 safety - 700 buffer
    recent_window=2,
    compression_threshold=0.6,
    tool_result_budget_fraction=0.25,
    embedding_backend="hybrid",  # Keep embeddings
)
# LLM Extractor: DISABLED
```

### Standard (8-16GB RAM, 4k-8k context)

**Goals:**
1. Balance between features and resource usage
2. Enable more aggressive retrieval
3. Better compression with LLM assistance

**Recommended Features:**
| Feature | Priority | Tokens Saved | Risk |
|---------|----------|--------------|------|
| All Minimal features | HIGH | - | - |
| LLM state extraction | MEDIUM | ~200 (better recall) | Medium |
| Active file priority | HIGH | ~50 | Low |
| Semantic hybrid search | MEDIUM | ~100 | Low |

**Avoid:**
- Self-reflection (still too expensive)
- Very large beam windows (diminishing returns)

**Configuration:**
```python
MemoryConfig(
    max_tokens=4000,          # 8k - 1500 overhead - 768 safety
    recent_window=3,
    compression_threshold=0.7,
    tool_result_budget_fraction=0.35,
    embedding_backend="hybrid",
)
# LLM Extractor: ENABLED for 8k+
```

### Generous (16-32GB RAM, 8k-16k context)

**Goals:**
1. Maximize accuracy through richer context
2. Enable advanced features
3. Larger beam windows

**Recommended Features:**
| Feature | Priority | Tokens Saved | Risk |
|---------|----------|--------------|------|
| All Standard features | HIGH | - | - |
| LLM state extraction | HIGH | ~500 | Low |
| Larger beam windows | MEDIUM | ~200 | None |
| Decision chains | LOW | ~100 | Low |
| Dependency graph | LOW | ~200 | Medium |

**Configuration:**
```python
MemoryConfig(
    max_tokens=8000,          # 16k - 2500 overhead - 1024 safety
    recent_window=5,
    compression_threshold=0.75,
    tool_result_budget_fraction=0.40,
    embedding_backend="semantic",
)
# LLM Extractor: ENABLED
```

### Heavy (32GB+ RAM, 16k+ context)

**Goals:**
1. Claude-level accuracy
2. Full feature set
3. Maximum context utilization

**All Features Enabled:**
- Self-reflection verification
- Parallel LLM extraction
- Full semantic search
- Micro-contexts
- Decision chains

**Configuration:**
```python
MemoryConfig(
    max_tokens=12000,         # Leave headroom
    recent_window=8,
    compression_threshold=0.8,
    tool_result_budget_fraction=0.45,
    embedding_backend="semantic",
    summary_budget_fraction=0.25,
)
# All advanced features ENABLED
```

---

## Quick Wins (Zero Resource Cost)

These improvements provide the highest impact with zero resource cost:

| Technique | Tokens Saved | Impact | Resource Tier |
|-----------|-------------|--------|---------------|
| Critical context injection | ~100 | HIGH | All |
| Compact tool format | ~50/total | HIGH | All |
| Safety margin reduction | ~500 | VERY HIGH | Minimal |
| Intent-aware beam | ~50 | MEDIUM | All |
| Embedding cache | ~500ms latency | HIGH | All |
| Tool prediction | ~30 | MEDIUM | All |
| Compression cooldown | Prevents waste | HIGH | Minimal |
| Active file priority | ~50 | MEDIUM | All |

---

## Future Improvements

### Phase 1: Quick Wins (Done ✓)
- Critical context injection
- Intent-aware beam selection
- Tool prediction
- Compression cooldown
- Embedding cache
- Compact tool format

### Phase 2: Medium Effort
- LLM state extraction (for 8k+)
- Active file priority
- Semantic hybrid search improvements
- Decision chain preservation

### Phase 3: Advanced (Requires Resources)
- Self-reflection loops
- Dependency graph tracking
- Micro-context templates
- Multi-tier retrieval

### Phase 4: Claude-Level (Heavy Resources Only)
- Full self-verification
- Parallel LLM extraction at compression
- Advanced reasoning chains
- Comprehensive code understanding

---

## Configuration Commands

---

## Configuration Commands

```bash
# Check memory stats
/context stats

# Force compression
/compress

# Clear all memory
/clear

# Save session
/save [name]

# List sessions
/sessions list

# Count tokens in text
context count-tokens "text to count"
```
