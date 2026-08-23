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
│   ├── web_inspector.py     # Ephemeral 3-tiered Playwright/JSDOM web outcome inspector
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
- Dynamic L0 Working Memory Scratchpad: adaptive, ~150-1200 tokens (headroom-scaled via `ContextBudget`; expands to surface more memory when context is idle, shrinks under pressure)
- Tool syntax & skill schemas: ~300 tokens
- Flashlight beam (2 files × 75 lines AST): ~600-750 tokens
- Feedback loop & test traceback: ~400 tokens
- **Available for conversation & active file pins: ~10,338 tokens (~84% headroom, minus any expanded L0)**

#### 2. 4k Model Fallback (4,096 Tokens)
- System prompt: ~250 tokens
- Tool syntax suffix: ~80 tokens
- Flashlight beam (1 file × 25 lines AST): ~250 tokens
- Dynamic L0 Scratchpad: adaptive, shrinks toward ~150 tokens under pressure
- **Available for conversation: ~3,316 tokens**

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
- **Modular Mode-Tailored System Prompt Templates**: Core architecture in `core/prompts/system.py` uses 4 dedicated templates (`CHAT_PROMPT`, `PLAN_PROMPT`, `CODE_PROMPT`, `TROUBLESHOOT_PROMPT`) sharing unified core directives (`SHARED_BASE_DIRECTIVES`). `CHAT_PROMPT` enforces pure conversational answers wrapped in `<FINAL_ANSWER>...</FINAL_ANSWER>` with read-only lookup tools (`SEARCH_AST`, `GREP`, `READ_FILE`, `WEB_SEARCH`), stripped of file modifications, `implementation_plan.md` mandatory creation, and write/test validation gates.
- **Chat Mode Working Memory & Verification Gate Isolation**: In `ExecutionMode.CHAT`, `TieredMemory.format_l0_scratchpad()` suppresses disk task matrix injection (`get_compact_task_matrix()`) to prevent leftover workspace plans from bleeding into Q&A context. Engine's Verification Gate bypasses pending task checks in Chat Mode, allowing direct final answers without forcing tool execution. `_detect_phase()` in both CLI and TUI frontends guards against keyword triggers to keep Chat Mode persistent.
- **Dynamic L0 Working Memory Scratchpad**: Renders active goal, modified files, active errors, failing tests, key decisions, and `tried_and_failed` anti-looping strategy logs into system context on every turn. Budget is **headroom-adaptive** (`core/memory/budget.py::ContextBudget`): expands up to ~1200 tokens to surface more entries when context is idle, shrinks to ~150 tokens under pressure; priority-ordered so the highest-value state always survives.
- **Active Model Memory & Dynamic Task Re-Planning**: `SAVE_MEMORY` tool enables explicit logging of facts/decisions/failed strategies; `UPDATE_TASK_GRAPH` tool enables dynamic mid-trajectory task insertions (`add_subtask`), task skips (`skip_task`), and status mutations in `.torchlight/goal_spec.json`.
- **AST-Driven Inter-Task Symbol Handoffs**: Automatically extracts newly created or modified function/class signatures via `SymbolIndex` upon task completion, enriching task output summaries for downstream epoch handoffs.
- **Anti-Symptom-Patching Directives**: Hardcoded directives in `SYSTEM_PROMPT` forbidding masking symptoms, swallowing exceptions, returning dummy fallbacks, or deleting assertions.
- **Native AST Graph Engine**: Zero-dependency `graph_engine.py` replaces Kùzu DB. Stores graph at `.torchlight/graph.json` (never loaded into LLM context). Provides `query()` (enriched with line-level code previews), `find_path()`, `get_subgraph()`, `get_structure()` with hard output caps to prevent context overflow
- **Lazy graph invalidation**: File edits invalidate the graph cache (`_graphs.pop()`), rebuilding only on next `SEARCH_AST` query — never eagerly during editing
- **24-Hour Autonomous Harness**: Continuous micro-epoch runner (`AutonomousHarness`) driving file-backed goal specs (`.torchlight/goal_spec.json` & `.torchlight/tasks.md`), resetting conversation context (`L0`) between sub-tasks, and applying test-driven local Git checkpoints & auto-reverts (`git checkout -- .` + `git clean -fd`)
- **Zero-Config Local Git Provisioning**: `AutonomousHarness` checks target project roots and automatically executes `git init` locally if missing
- **Tiered memory**: Recent 3 messages full detail, older summarized
- **Active file pinning**: Recently-read files pinned in separate FIFO buffer (max 2), survives compression
- **12k context (8GB & TurboQuant base)**: Default CTX_SIZE=12288 across config and start scripts, KV cache ~0.3GB, override via `RLM_CTX_SIZE`
- **85% context budget**: Headroom for system/tools/beam
- **Phase-based inference**: code (temp=0.1), troubleshoot (temp=0.3), chat (temp=0.7)
- **Surgical file reading**: SEARCH_AST (returns signatures + 5-line previews) → GREP → READ_SYMBOLS → READ_FILE(range/symbol)
- **Inline code interception**: Code in chat → auto-WRITE_FILE
- **Lazy skill loading**: AST scan at startup, import on first execute
- **Context-scaled tool output**: READ_FILE caps at ~20% of window; SEARCH_AST caps subgraph at 40 edges, structure at 20 files, query output at 40 total lines
- **Zero-Context Harness Quality Engine**: Deterministic post-save code formatting (`ruff`, `black`, `prettier`, `gofmt`, `rustfmt`), POSIX whitespace normalization (preserving Makefile/Go tabs), multi-language syntax validation (Python AST, JSON, JS bracket balance), and stub detector operating in the Python harness layer with 0 LLM context overhead.
- **Autonomous Playwright Web Outcome Inspection**: Ephemeral 3-tiered rendering (Playwright Chromium → Node JSDOM → Static HTML Parser) capturing DOM snapshots, Accessibility Trees (`ax_tree`), console errors, 404s, layout overflow warnings, and interactive action sequences with <300 token Markdown summaries for non-vision models (e.g., Qwen 2.5 Coder).
- **Enhanced Web Browsing & Stealth Anti-Blocking Engine**: Multi-tier web retrieval (Jina Reader API → Stealth HTTP GET with `sec-ch-ua` browser headers → Remote Headless Playwright Chromium engine for 403/429/Cloudflare/JS SPAs), structure-preserving HTML parser (`StructurePreservingHTMLParser` preserving `<pre><code>` & `<table>` formatting), and version-locked query augmentation (`pyproject.toml` / `package.json` manifest inspector).
- **Non-Verbose Code Output (3-Tier Output Discipline)**: Never dump raw code in assistant text. Code modifications occur via `WRITE_FILE`/`EDIT_FILE` tool payloads while chat responses state action, file path, line numbers range or function scope (e.g. `src/main.py:L10-L25`), and description. UI collapses tool payload args into status badges featuring target path with line number ranges (e.g. `✓ ✏ EDIT_FILE src/main.py:L10-L25`), reducing edit turn token usage by ~85% and preventing screen buffer overflow.
- **Fault-Tolerant Tool Execution & Auto-Fallback**: `_parse_diff_block()` handles non-canonical diffs (missing `=======` dividers), and `EDIT_FILE` automatically delegates full `content` payloads or non-existent target files to `WRITE_FILE` to prevent unnecessary trajectory failures.
- **Explicit Session Modes (`💬 Chat Mode` vs `📋 Plan Mode` vs `🎯 Goal Mode`)**: Core support for `ExecutionMode` enum (`CHAT`, `PLAN`, `GOAL`). Chat Mode suppresses `.torchlight/goal_spec.json` & `tasks.md` creation for clean Q&A sessions. Plan Mode inspects codebase files via read-only tools (`SEARCH_AST`, `GREP`, `READ_FILE`, `LIST_DIR`), brainstorms complete architecture/steps/process, and maintains/writes `implementation_plan.md` via `WRITE_FILE`/`EDIT_FILE` without modifying application source code. Goal Mode lazily initializes task graphs on demand; in Goal Mode, the agent first inspects available workspace files (`LIST_DIR`, `SEARCH_AST`, graphify) to understand codebase context before writing `implementation_plan.md` and autonomously executing tasks. `ensure_project_initialized()` auto-patches `.gitignore` to include `.torchlight/`. CLI (`--mode`, `context plan`, `context goal`, `/mode`) and TUI (`SessionModePickerModal`, `Ctrl+G`, `/mode`) provide interactive selection with Rich/Textual tooltips.



- **Structured errors**: 7 types with `RecoveryEngine` escalation ladder
- **Fallback imports**: Frontends use `try/except ImportError` for backward compat

### Tool Risk Tiers
- **AUTO**: READ_FILE, GREP (ripgrep-powered), SEARCH_AST, WEB_*, DOC_*, SAVE_MEMORY, UPDATE_TASK_GRAPH, GIT (read ops: status/diff/log/show/branch/blame), safe shell commands
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

## Codebase Exploration & Token Optimization Hard Rules
- **MANDATORY Graphify-First Search & Relationship Analysis**: For understanding codebase architecture, module relationships, dependencies, call paths, or finding specific components, ALWAYS use `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` (or `query_graph` MCP tool) before reading raw source files line by line or running mass grep scans.
- **Dependency & Relationship Tracing**: Use `graphify path` to trace dependencies between components and `graphify explain` to analyze callers, callees, and structural links with minimal token overhead.
- **Token Conservation**: Rely on targeted graph queries and scoped subgraphs to save context tokens while preserving high analytical quality and accuracy.
- **Keep Graph Current**: After modifying code files in a session, run `graphify update .` to keep the knowledge graph up to date.
- **TUI Performance & Design Rules (MANDATORY for all UI changes)**: Whenever creating or modifying UI components, widgets, modals, layouts, or CSS, ALWAYS strictly follow [.agents/rules/tui_design_and_performance.md](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/.agents/rules/tui_design_and_performance.md) (solid borders, 100% opaque backdrops, `RichLog.write()`, 2.0s telemetry TTL cache, and TPS-adaptive throttling).

## Deterministic Trajectory & SLM Reliability Hard Rules (99%+ Accuracy for Small Models)
- **Single-Path State Transitions**: All error recovery hints and loop gates must inject a single, unambiguous `<tool_call>` template rather than open-ended multi-bullet guidance, keeping 3B models strictly on-rails.
- **Anchor-Enforced Code Modifications**: Single-line edits (`s_l == e_l`) strictly require `old_text` to anchor replacements; unanchored 1-line overwrites are hard-rejected at the tool contract level to prevent typewriter stepping loops.
- **Block-Level Edit Discipline**: Function and module implementations must be written as full multi-line blocks (`EDIT_FILE` with $e_l - s_l \ge 1$) or full files (`WRITE_FILE`) in a single turn.
- **Sliding 1-Line Stepping Detection**: `TrajectoryLock` detects consecutive single-line edits (`L{k}-L{k}`) across turns and immediately blocks the crawl with a direct `WRITE_FILE` directive.
- **Auto-Interception of Markdown JSON**: When SLMs emit markdown code blocks (` ```json `) inside simulated walkthroughs, `_parse_response` extracts and executes the first balanced tool call on turn 1.
- **Deterministic New File Creation (Zero-Read Onboarding)**: For tasks marked `[NEW]` or targeting non-existent files, agents must immediately emit `WRITE_FILE` with complete initial code rather than probing with `READ_FILE` or `SEARCH_AST`.
- **Actionable Tool-Call Injection on Missing Files**: `READ_FILE`, `EDIT_FILE`, and `TrajectoryLock` on non-existent files must never recommend exploratory shell checks (`ls` / `find`). They must directly inject a concrete `<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "<path>", "content": "..."}}</tool_call>` template to guarantee single-path recovery.
- **Execution-Flow Tracing Protocol**: When debugging multi-component bugs, agentic loop stalls, or empty output cards, apply the 7-step forward execution trace (`.agents/skills/execution-trace-debug/SKILL.md`) from entry point to divergence before modifying code.




