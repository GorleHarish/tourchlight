# Torchlight — Terminal AI Coding Agent

Torchlight is a terminal-only AI coding agent with a shared `core/` library and two frontends: a CLI (Typer + Rich) and a TUI (Textual). It solves **context rot** through tiered memory, structured error handling, surgical file reading, and deterministic tool routing. Runs entirely in your terminal against local or cloud LLMs.

No GUI. No browser. No WebSocket server. Just your terminal and a local model.

---

## Quick Start

```bash
# CLI frontend
cd context-manager-cli
./run.sh

# Or after pip install -e .
context chat --max-tokens 4096

# TUI frontend
cd rlm_optimized
python tui_app.py
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Frontends                            │
│  ┌─────────────────────┐  ┌─────────────────────────┐   │
│  │  CLI (Typer + Rich) │  │  TUI (Textual IDE)      │   │
│  │  main.py            │  │  tui_app.py             │   │
│  │  dashboard.py       │  │  rlm_engine_optimized.py│   │
│  │  skills/unified.py  │  │  repl_sandbox.py        │   │
│  └─────────┬───────────┘  └──────────┬──────────────┘   │
│            │  try: from core import   │                   │
│            │  except: local fallback  │                   │
├────────────┼──────────────────────────┼──────────────────┤
│            └──────────┬───────────────┘                   │
│                       ▼                                   │
│  ┌────────────────────────────────────────────────────┐  │
│  │  core/ — Shared Library                            │  │
│  │                                                    │  │
│  │  tools/         API clients     Memory             │  │
│  │  ├─ registry.py ├─ base.py     ├─ manager.py       │  │
│  │  ├─ schemas.py  ├─ factory.py  ├─ models.py        │  │
│  │  └─ impl.py     └─ lmstudio.py ├─ persistence.py   │  │
│  │                                 ├─ token_counter.py │  │
│  │  Errors          Compression     ├─ embeddings.py   │  │
│  │  ├─ types.py     ├─ compact.py   └─ selective.py    │  │
│  │  └─ recovery.py  └─ summarizer.py                   │  │
│  │                                                    │  │
│  │  Flashlight      Execution          Prompts          │  │
│  │  ├─ index.py     ├─ feedback.py     └─ system.py     │  │
│  │  └─ beam.py      ├─ harness.py                       │  │
│  │                 └─ run_harness.py                    │  │
│  └────────────────────────────────────────────────────┘  │
│                       │                                   │
│                       ▼                                   │
│  ┌────────────────────────────────────────────────────┐  │
│  │  LLM Provider                                      │  │
│  │  LM Studio / Ollama / Groq / Together / OpenAI     │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

Both frontends import from `core/` with a `try/except ImportError` fallback to local modules, so each frontend remains standalone if `core/` is not installed.

---

## Core Flow

1. **Query** — User sends a message from the terminal
2. **Phase Detection** — Runtime classifies intent as `plan`, `code`, `troubleshoot`, or `chat`
3. **Build Messages** — Assembles system prompt, flashlight beam, memory state, and conversation history within the token budget
4. **Stream** — Sends the assembled prompt to the LLM and streams tokens back in real time
5. **Parse Tools** — Extracts tool calls from the response (`<tool_call>` tags, inline code fences)
6. **Execute** — Runs approved tools with tiered approval (AUTO/CONFIRM/REVIEW)
7. **Recovery** — On failure, RecoveryEngine applies RETRY → COMPRESS_AND_RETRY → SKIP → ABORT
8. **Feedback** — Auto-runs tests after code edits, feeds results back into the next turn

---

## Key Features

- **Shared Core Library** — `core/` package with tools, API, memory, errors, compression, flashlight, execution, and prompts — reusable across frontends
- **24-Hour Autonomous Goal Harness** — `AutonomousHarness` continuous micro-epoch daemon with disk task tracking (`.torchlight/tasks.md`), conversation context flushing between sub-tasks, test-driven Git save points, and auto-revert gates
- **Zero-Config Local Git Provisioning** — Auto-checks target project roots and executes `git init` locally if absent
- **Zero-Context Harness Quality Engine** — Deterministic post-save formatting (`ruff`/`black`, `prettier`, `gofmt`, `rustfmt`), multi-language syntax validation (Python AST, JSON, JS bracket balance), POSIX whitespace normalization, and stub detection operating with 0 LLM context overhead
- **Structured Error Handling** — 7 error types (`ToolError`, `ParseError`, `ContextOverflowError`, `ConnectionError`, `SecurityError`, `ToolValidationError`, `TorchlightError`) with `RecoveryEngine` escalation ladder

- **Tiered Memory** — L0-L3 hierarchy: active prompt → recent messages → compressed older turns → project memory
- **Selective Compression** — Four levels (FULL / COMPACT / SUMMARY / HINT) with needle preservation and context-aware selection
- **Phase-Based Inference** — Temperature and sampling tuned per task: code (temp=0.1), troubleshoot (temp=0.3), chat (temp=0.7)
- **Unified Tool Registry** — 17 tools with schema validation, alias resolution, and AUTO/CONFIRM/REVIEW risk tiers
- **Surgical File Reading** — GREP → READ_SYMBOLS → READ_FILE(range/symbol) keeps tool output small and relevant
- **Flashlight Code Index** — Symbol-aware codebase retrieval with context-scaled beam size
- **Execution Feedback Loop** — Auto-detects and runs tests (pytest/npm/cargo) after file edits
- **Multi-Backend API** — `create_client()` factory supports LM Studio, llama.cpp, Ollama, Groq, Together, OpenRouter, OpenAI, Gemini
- **InferenceParams Presets** — Phase-based sampling presets (code/plan/troubleshoot/chat) with streaming support
- **Trust Pipeline** — Validates file writes with syntax check, compile check, and automatic one-pass repair

---

## Module Structure

```
core/
├── api/
│   ├── base.py              # LLMClient protocol, InferenceParams with presets
│   ├── factory.py           # create_client() for 8+ backends
│   └── lmstudio.py          # LM Studio REST client
├── tools/
│   ├── registry.py          # Unified ToolRegistry (17 tools, alias resolution)
│   ├── schemas.py           # TOOL_SCHEMAS, validate_tool_call()
│   └── implementations.py   # All tool implementations
├── memory/
│   ├── manager.py           # TieredMemory (L0-L3 hierarchy)
│   ├── models.py            # Message, SessionState, ContextSnapshot
│   ├── persistence.py       # Session save/load, ProjectMemory
│   ├── token_counter.py     # tiktoken with fallback estimation
│   ├── embeddings.py        # Hybrid embedding support
│   ├── llm_extractor.py     # LLM state extraction at compression
│   └── selective_compression.py  # 4-level progressive compression
├── errors/
│   ├── types.py             # TorchlightError, ToolError, ParseError, etc.
│   └── recovery.py          # RecoveryEngine + get_recovery_hint()
├── compression/
│   ├── compact.py           # VerbatimCompactor
│   └── summarizer.py        # ConversationSummarizer
├── flashlight/
│   ├── index.py             # SymbolIndex (Python/JS/TS/Go/Rust)
│   └── beam.py              # Flashlight beam retrieval
├── execution/
│   └── feedback_loop.py     # Auto-run tests after code changes
├── prompts/
│   └── system.py            # Unified system prompt
└── __init__.py

context-manager-cli/src/context_manager/
├── api/lmstudio.py          # Re-exports from core.api
├── cli/
│   ├── main.py              # CLI entry, phase detection, /params
│   └── dashboard.py         # Rich live panels + ActionTracker
├── skills/                  # Skill system (CLI-only)
│   ├── base.py, unified.py, discovery.py, tdd.py
├── tools/core.py            # Re-exports from core.tools
├── flashlight/              # Re-exports from core.flashlight
├── memory/                  # Re-exports from core.memory
├── compression/             # Re-exports from core.compression
├── execution/               # Re-exports from core.execution
└── prompts.py               # Re-exports from core.prompts

rlm_optimized/
├── tui_app.py               # Textual IDE TUI
├── rlm_engine_optimized.py  # Async agentic engine
├── tool_schemas.py          # Re-exports from core.tools
├── repl_sandbox.py          # Sandboxed Python execution
└── llm_client.py            # LLM clients (SSE, llama.cpp)
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show context statistics (tokens, messages, memory state) |
| `/stream` | Toggle streaming mode on/off |
| `/compress`, `/compact` | Manually trigger memory compression |
| `/clear` | Clear all context from the current session |
| `/tokens` | Show current token usage breakdown |
| `/save [name]` | Save the current session to disk |
| `/params` | Show or set inference parameters |
| `/reindex` | Rebuild the Flashlight symbol index for the workspace |
| `/beam [query]` | Run a Flashlight beam search and display results |
| `/files` | List recently accessed and modified files |

---

## Development

```bash
# Set up shared core library
python3 -m venv venv && source venv/bin/activate
cd core && pip install -e ".[dev]" && cd ..

# Run CLI
cd context-manager-cli
./run.sh

# Run TUI
cd rlm_optimized
python tui_app.py

# Run all tests (core + CLI)
pytest core/tests/
cd context-manager-cli && pytest

# Lint
ruff check core/ context-manager-cli/src/
```

---

## Memory Files

| File | Description |
|------|-------------|
| `~/.context-manager/sessions/<name>.json` | Persisted session transcripts and state |
| `<project>/.context-memory.json` | Long-term project memory (facts, decisions, tech stack, needles) |

---

## Error Handling

The `core/errors/` module provides structured error types and a `RecoveryEngine` with an escalation ladder:

| Error Type | Recovery Action |
|-----------|----------------|
| `ToolError` | Skip tool, report to LLM, continue |
| `ParseError` | RETRY → skip, log details |
| `ContextOverflowError` | COMPRESS_AND_RETRY → summarize + retry |
| `ConnectionError` | RETRY with backoff → ABORT after 3 |
| `SecurityError` | ABORT immediately |
| `ToolValidationError` | Skip tool with suggestion |
| `TorchlightError` | Base class — log and continue |
