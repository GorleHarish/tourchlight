## Commands

```bash
cd context-manager-cli
./run.sh                      # Start chat session
context chat                  # Start via installed CLI
context chat --max-tokens 4096  # Match your model's context
```

## Architecture

**Torchlight Agent** — Terminal-only LLM agent with intelligent context management.

### Module Structure
```
core/                          # Shared library (standalone package)
├── api/
│   ├── base.py              # LLMClient protocol, InferenceParams
│   ├── factory.py           # create_client() for 8+ backends
│   └── lmstudio.py          # LM Studio REST client
├── tools/
│   ├── registry.py          # Unified ToolRegistry (18 tools)
│   ├── schemas.py           # TOOL_SCHEMAS, validate_tool_call()
│   ├── classification.py    # AUTO/CONFIRM/REVIEW risk tiers
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
│   ├── types.py             # 7 structured error types
│   └── recovery.py          # RecoveryEngine + get_recovery_hint()
├── compression/
│   ├── compact.py           # VerbatimCompactor
│   └── summarizer.py        # ConversationSummarizer
├── flashlight/
│   ├── index.py             # SymbolIndex (Python/JS/TS/Go/Rust)
│   ├── beam.py              # Flashlight beam retrieval (+ AST graph scoring)
│   └── graph_engine.py      # Native AST Knowledge Graph (pure Python)
├── execution/
│   ├── feedback_loop.py     # Auto-run tests + lazy graph invalidation
│   ├── autonomous_harness.py # 24h continuous goal harness & micro-epoch runner
│   └── run_harness.py       # CLI entry point for continuous runner
└── prompts/
    └── system.py            # Unified system prompt

context-manager-cli/src/context_manager/   # CLI frontend
├── cli/main.py              # Typer + Rich CLI, phase detection, graph init
├── cli/dashboard.py         # Live stats + ActionTracker
├── skills/                  # Skill system (TDD, custom skills)
│   ├── unified.py, base.py, discovery.py, tdd.py
└── [re-exports from core/]

rlm_optimized/                              # TUI frontend
├── tui_app.py               # Textual IDE TUI
├── rlm_engine_optimized.py  # Async agentic engine
├── repl_sandbox.py          # Sandboxed Python execution
└── [re-exports from core/]
```

### Context Budget Breakdown

#### 1. 12k Context (TurboQuant Base — 12,288 Tokens)
- System prompt + Phase instructions: ~300 tokens
- Dynamic L0 Working Memory Scratchpad: ~200 tokens
- Tool syntax & skill schemas: ~300 tokens
- Flashlight beam (3 files × 120 lines AST): ~1,500 tokens
- Feedback loop & test traceback: ~400 tokens
- **Available for conversation & active file pins: ~9,588 tokens (~78% headroom)**

#### 2. 4k Model Fallback (4,096 Tokens)
- System prompt: ~250 tokens
- Tool syntax suffix: ~80 tokens
- Flashlight beam (1 file × 50 lines AST): ~500 tokens
- Dynamic L0 Scratchpad: ~200 tokens
- **Available for conversation: ~3,066 tokens**

### Agentic Loop
1. `_detect_phase()` → plan|code|troubleshoot|chat
2. Load `InferenceParams` preset & inject phase-tailored system prompt (`get_phase_system_prompt(phase)`)
3. Inject dynamic L0 Working Memory Scratchpad (`format_l0_scratchpad()`) into system context
4. Stream response via LM Studio
5. Parse tool calls (`<tool_call>` tags)
6. Execute with tiered approval (AUTO/CONFIRM/REVIEW)
7. RecoveryEngine on failure (RETRY → COMPRESS → SKIP → ABORT)
8. Auto-run tests after code changes
9. Continue chain (max 10 deep)

### Key Design Decisions
- **Shared core library**: `core/` is standalone with `pyproject.toml`, both frontends import from it
- **Phase-Tailored System Prompting**: Dynamically injects phase-specific instructions for `plan`, `code`, `troubleshoot`, and `chat` alongside temperature presets.
- **Dynamic L0 Working Memory Scratchpad**: Renders active goal, modified files, active errors, failing tests, and key decisions into system context on every turn.
- **Anti-Symptom-Patching Directives**: Hardcoded directives in `SYSTEM_PROMPT` forbidding masking symptoms, swallowing exceptions, returning dummy fallbacks, or deleting assertions.
- **Native AST Graph Engine**: Zero-dependency `graph_engine.py` replaces Kùzu DB. Stores graph at `.torchlight/graph.json` (never loaded into LLM context). Provides `query()`, `find_path()`, `get_subgraph()`, `get_structure()` with hard output caps to prevent context overflow
- **Lazy graph invalidation**: File edits invalidate the graph cache (`_graphs.pop()`), rebuilding only on next `SEARCH_AST` query — never eagerly during editing
- **24-Hour Autonomous Harness**: Continuous micro-epoch runner (`AutonomousHarness`) driving file-backed goal specs (`.torchlight/goal_spec.json` & `.torchlight/tasks.md`), resetting conversation context (`L0`) between sub-tasks, and applying test-driven local Git checkpoints & auto-reverts (`git checkout -- .` + `git clean -fd`)
- **Zero-Config Local Git Provisioning**: `AutonomousHarness` checks target project roots and automatically executes `git init` locally if missing
- **Tiered memory**: Recent 3 messages full detail, older summarized
- **Active file pinning**: Recently-read files pinned in separate FIFO buffer (max 2), survives compression
- **12k context (8GB & TurboQuant base)**: Default CTX_SIZE=12288 across config and start scripts, KV cache ~0.3GB, override via `RLM_CTX_SIZE`
- **85% context budget**: Headroom for system/tools/beam
- **Phase-based inference**: code (temp=0.1), troubleshoot (temp=0.3), chat (temp=0.7)
- **Surgical file reading**: SEARCH_AST → GREP → READ_SYMBOLS → READ_FILE(range/symbol)
- **Inline code interception**: Code in chat → auto-WRITE_FILE
- **Lazy skill loading**: AST scan at startup, import on first execute
- **Context-scaled tool output**: READ_FILE caps at ~20% of window; SEARCH_AST caps subgraph at 40 edges, structure at 20 files
- **Non-Verbose Code Output (3-Tier Output Discipline)**: Never dump raw code in assistant text. Code modifications occur via `WRITE_FILE`/`EDIT_FILE` tool payloads while chat responses state action, file path, line/function scope, and description. UI collapses tool payload args into clean status badges (`✓ ✏ Writing src/main.py`), reducing edit turn token usage by ~85% and preventing terminal screen buffer overflow.
- **Structured errors**: 7 types with `RecoveryEngine` escalation ladder
- **Fallback imports**: Frontends use `try/except ImportError` for backward compat

### Tool Risk Tiers
- **AUTO**: READ_FILE, GREP (ripgrep-powered), SEARCH_AST, WEB_*, DOC_*, SAVE_MEMORY, GIT (read ops: status/diff/log/show/branch/blame), safe shell commands
- **CONFIRM**: WRITE_FILE, EDIT_FILE, GIT (write ops: commit/add/restore/stash), pip/npm install, scripts
- **REVIEW**: rm, git push/reset/rebase/merge/clean, sudo, destructive ops

## Development

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
cd core && pip install -e ".[dev]" && cd ..

# Run tests (all)
pytest core/tests/
cd context-manager-cli && pytest

# Lint
ruff check core/ context-manager-cli/src/
```

## Memory Files
- Sessions: `~/.context-manager/sessions/<name>.json`
- Project memory: `<project>/.context-memory.json`
- AST graph: `<project>/.torchlight/graph.json`
- Graph report: `<project>/.torchlight/GRAPH_REPORT.md`
