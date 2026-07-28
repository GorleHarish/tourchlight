# Changelog

## 2026-07-28

### Native AST Knowledge Graph Engine (`graph_engine.py` & `SEARCH_AST`)

- **Pure-Python AST Graph Engine**: Implemented `core/flashlight/graph_engine.py` — a zero-dependency knowledge graph engine replacing the Kùzu embedded database. Uses Python's `ast` module for Python files and regex fallback for JS/TS/Go/Rust/Java/C/C++/Ruby/C#/Kotlin. Stores graph at `.torchlight/graph.json` and generates `GRAPH_REPORT.md`.
- **Graph Traversal API**: `ProjectGraph` class provides `query()` (substring search), `find_path()` (BFS shortest path with depth limit), `get_subgraph()` (1-hop neighbor extraction), and `get_structure()` (project overview) — all with hard output caps to prevent context overflow.
- **SEARCH_AST Tool Integration**: Rewired `tool_search_ast_impl` to use native graph engine with actions: `search|path|subgraph|structure|update|summary`. Falls back to `rlm_optimized.repl_sandbox.semantic_search` when native search returns no results.
- **Flashlight Beam AST Relevance**: Added graph-aware relevance scoring in `beam.py` `_score()` with lazy-loaded read-only graph node cache (`_graph_nodes`). Graph is loaded once per `Flashlight` instance, never triggers `build()` during scoring.
- **Lazy Graph Invalidation**: Updated `feedback_loop.py` to invalidate cached graph via `_graphs.pop()` on file edits instead of eagerly rebuilding, deferring re-indexing to next query.
- **CLI Startup Initialization**: Added graph initialization to `context-manager-cli` startup in `main.py`.
- **System Prompt Update**: Updated `core/prompts/system.py` to prioritize graph-based `SEARCH_AST` navigation workflow.

### Kuzu AST Indexer Resilience & NumPy Compatibility Fixes (`ast_indexer.py` & `llamacpp_client.py`)

- **Catalog Binder Exception Fix**: Updated `init_db()` in `rlm_optimized/ast_indexer.py` to use `CREATE NODE TABLE IF NOT EXISTS` and `CREATE REL TABLE IF NOT EXISTS` combined with `MATCH (n) DETACH DELETE n` graph resets. Prevents `Binder exception: File already exists in catalog` when re-indexing existing project directories.
- **NumPy 2.0 PyTorch Compatibility**: Downgraded `numpy` from 2.0.2 to 1.26.4 (`numpy<2`) in `rlm_optimized/venv`, eliminating PyTorch `_ARRAY_API` initialization warnings and restoring `SentenceTransformer` vector embedding generation.
- **LLM Client HTTP 400 Error Body Extraction & Fallback**: Updated `LlamaCppClient` (`rlm_optimized/llamacpp_client.py`) to read and log response bodies on `HTTPError` exceptions, and auto-fallback to standard OpenAI schema payloads (stripping non-standard `grammar` and `repeat_penalty` fields) when `llama-server` returns HTTP 400 Bad Request.

### TurboQuant 12k Context Standardization & llama-server Error Diagnostics (`config.py`, `start_optimized_local.sh`, `llamacpp_client.py`)

- **Baseline 12,288 Token Context Window**: Standardized `CTX_SIZE` default to 12,288 tokens across `rlm_optimized/config.py` and `rlm_optimized/start_optimized_local.sh` for TurboQuant local setup (`llama-cpp`, `turbo`, `turboquant` providers), resolving context limit mismatches between python memory management and `llama-server`.
- **Exceed Context Size Error Detection**: Enhanced `LlamaCppClient` (`rlm_optimized/llamacpp_client.py`) to parse `exceed_context_size_error` returned in HTTP 400 Bad Request responses from `llama-server`. Provides actionable diagnostic error messages with explicit commands to restart `llama-server` with `-c 12288` or set `RLM_CTX_SIZE=8192`.
- **Automated Tests**: Added `test_llamacpp_client_context_size_error` in `core/tests/test_api.py`. Verified with full test suite passing (196/196 tests).

### Bug Audit & Context Overflow Hardening (6 Issues Fixed)

- **Critical Fix: Beam Scoring O(n²) Rebuild**: `_score()` called `get_project_graph()` on every file scored, triggering full AST rebuilds per file. Fixed with instance-level `_graph_nodes` cache.
- **Critical Fix: Eager Rebuild on Every Edit**: `feedback_loop.py` called `graph.build()` on every `WRITE_FILE`/`EDIT_FILE`. Changed to lazy cache invalidation.
- **Bug Fix: Unbounded BFS**: `find_path()` had no depth limit and used `list.pop(0)` (O(n)). Added `max_depth=10` and switched to `collections.deque.popleft()`.
- **Bug Fix: Empty Target Crash**: `find_path("name", "")` matched every node. Added explicit empty-string guard.
- **Context Overflow Fix: Unbounded Output**: `get_subgraph()`, `get_structure()`, and `query()` could produce massive outputs. Added caps: `_MAX_SUBGRAPH_EDGES=40`, `_MAX_STRUCTURE_FILES=20`, `_MAX_FUNCS_PER_FILE=5`, docstring truncation at 80 chars.
- **Minor Fix: Short-Circuit Logic**: Replaced fragile `self.load() or self.build()` with explicit `if not self.load(): self.build()`.
- **Automated Tests**: Added `core/tests/test_graph_engine.py` (3 test cases). All 148 core unit tests pass cleanly.

## 2026-07-27

### Ephemeral Web Outcome Inspection Subsystem (`WebOutcomeInspector` & `INSPECT_WEB`)

- **3-Tier Zero-Persistent-Memory Inspection**: Implemented `WebOutcomeInspector` (`core/execution/web_inspector.py`) to inspect the runtime outcome of generated HTML, CSS, JavaScript, and HTML5 Canvas games/apps.
- **Ephemeral Headless Playwright Execution**: Launches on-demand headless browser execution to capture `console.error`, unhandled rejections, 404 missing resources, canvas status, DOM snapshots, and screenshots (`.torchlight/screenshots`), terminating the browser immediately (`browser.close()`) to maintain 0MB persistent RAM usage.
- **Multi-Tier Fallbacks**: Gracefully degrades to Node JSDOM (Tier 3) and Python `HTMLParser` static validation (Tier 1) when Playwright binaries are unavailable.
- **Tool Registry Integration**: Registered `INSPECT_WEB` (icon `🕸️`, `AUTO` risk tier) in `schemas.py`, `classification.py`, `implementations.py`, and `registry.py`.
- **Auto-Feedback Loop Integration**: Updated `ExecutionFeedbackLoop` (`core/execution/feedback_loop.py`) to auto-detect frontend projects, automatically run `WebOutcomeInspector` when web files are modified, and inject feedback into prompt context with consume-on-read context protection.

### Performance & Accuracy Optimization Suite

- **Parallel & Batch Tool Execution**: Implemented `execute_batch()` in `ToolRegistry` (`core/tools/registry.py`) to execute read-only `AUTO` tool calls concurrently via `ThreadPoolExecutor` (3x–5x speedup during exploration).
- **Symbol Index `mtime` Caching**: Updated `SymbolIndex.build()` (`core/flashlight/indexer.py`) to cache symbol structures using file modification timestamps (`mtime`), enabling sub-5ms incremental scans.
- **Blank Canvas Pixel & Render Precision**: Enhanced `WebOutcomeInspector` with client-side canvas `getImageData` pixel array evaluation to detect transparent/blank canvas draw loops (`BLANK_CANVAS` warning).
- **Fast Inline Syntax Guardrails**: Added `_check_syntax()` to `tool_write_file_impl` and `tool_edit_file_impl` (`core/tools/implementations.py`) to validate Python syntax (`ast.parse`) inline and return instant line-numbered warnings before CLI test runs.
- **Automated Tests**: Added `core/tests/test_web_inspector.py` and `core/tests/test_optimizations.py`. All 145 core unit tests pass cleanly across `core/tests/`.


### Inter-Task Context Pipeline & File Collision Guard (`AutonomousHarness`)

- **Task Dependency Graph & Execution Resolution**: Added `depends_on: list[str]` and `outputs_summary: Optional[str]` to `TaskSpec` and `GoalSpec`. Enforced task dependency order in `_get_runnable_pending_tasks()`, keeping tasks in queue until prerequisite tasks reach `TaskStatus.VERIFIED`.
- **Inter-Task Memory Pipeline**: Added `_get_prior_verified_summaries()` to summarize prior task outputs (`outputs_summary`) and inject them into downstream micro-epoch prompts, preserving key symbol exports and interface contracts across `memory.clear()` resets.
- **Target File Collision Guard**: Added `_validate_file_collisions()` to detect overlapping target files across active/failed sub-tasks, preventing accidental file overwrites.
- **Automated Tests**: Added `core/tests/test_autonomous_harness_pipeline.py`.

### Strict Context Budget Scaling & Pinned File Accounting

- **Dynamic Tool Output Scaling**: Automatically invoke `set_ctx_window(max_tokens)` upon `AutonomousHarness` and `RLMEngine` initialization so `READ_FILE` tool output budgets scale dynamically to ~20% of context window size.
- **Pinned File Token Accounting**: Updated `TieredMemory.total_tokens` in `core/memory/manager.py` to count `msg_tokens + pinned_tokens`, ensuring compression thresholds accurately trigger before pinned files push the payload over context limits.
- **Session Summary Overflow Protection**: Pruned `summary_messages` in `rlm_engine_optimized.py` to system prompt + recent turns when history length > 4, preventing session summary generation from overflowing context limits at task completion.
- **Automated Tests**: Added `core/tests/test_context_budget_overflow.py`. All 135 core unit tests pass cleanly across `core/tests/`.

### Automatic Project & Persistent Memory File Initialization

- **Automatic Persistent Memory Provisioning & Edge-Case Self-Healing**: Enhanced `ensure_project_initialized()` and `ProjectMemory` in `core/memory/persistence.py` and CLI persistence to automatically create `.context-memory.json` on project load, and self-heal on disk if deleted manually, corrupted (invalid JSON), or created as a directory.
- **Git Auto-Provisioning & On-Demand Repository Repair**: Implemented `ensure_git_repository(project_path, force_init=False)` to idempotently initialize local Git repositories and configure fallback credentials (`torchlight@local.dev`). Integrated pre-command auto-repair hooks into `AutonomousHarness` (`_git_commit` / `_git_revert`) and Git tool implementations (`core/tools/implementations.py`) to auto-provision `.git` seamlessly if deleted mid-run.
- **Selective Git Auto-Provisioning (`init_new_project`)**: Refined Git repository auto-initialization (`git init`) to run specifically during new target project initialization (`init_new_project` / `create_git=True` in `AutonomousHarness`), avoiding unwanted `git init` calls on existing host directories.
- **Frontend Integration**: Updated `ProjectMemory`, `StreamingChatSession` (CLI), and `RLMEngineOptimized` (TUI `__init__` and `set_project_root()`) to ensure project initialization cleanly handles memory state and project paths.
- **Automated Tests**: Updated `core/tests/test_project_init.py` with 4 new edge-case tests (`test_corrupt_memory_file_self_heals`, `test_directory_memory_file_self_heals`, `test_manual_deletion_context_memory_self_heals`, `test_manual_deletion_git_repo_self_heals`). All 130 core unit tests pass cleanly across `core/tests/`.

### 24-Hour Continuous Autonomous Goal Harness (`AutonomousHarness`)

- **Autonomous Harness Module**: Implemented `AutonomousHarness` (`core/execution/autonomous_harness.py`), enabling continuous, multi-epoch execution of long-running coding goals (up to 24+ hours) without context window overflow.
- **Disk-Backed Working Memory**: Persists goal and sub-task status to disk (`.torchlight/goal_spec.json` and `.torchlight/tasks.md`), enabling persistent progress tracking across sessions.
- **Micro-Epoch Context Window Flushing**: Resets active conversation message history (`L0`) between sub-tasks while retaining long-term project memory (`.context-memory.json`) and AST file pins, capping context usage at ~500–1000 tokens per epoch.
- **Verification & Local Git Checkpoints**: Auto-runs test suites via `ExecutionFeedbackLoop`. Passing sub-tasks trigger atomic local Git commits (`git commit -m "feat(torchlight-auto): ..."`). Unverified failing sub-tasks log failure tracebacks, retry up to `max_attempts`, and auto-revert dirty state (`git checkout -- .` + `git clean -fd`).
- **Target Project Local Git Auto-Provisioning**: `AutonomousHarness` automatically checks for `.git` on target project roots and runs local `git init` if missing, providing zero-config local checkpointing without remote setup.
- **CLI Runner Script**: Added `core/execution/run_harness.py` to launch 24-hour daemon sessions from the terminal.
- **Automated Tests**: Added `core/tests/test_autonomous_harness.py`. All 120 unit tests pass cleanly across `core/tests/`.

## 2026-07-26


### Functional Out-of-Band Debate & Self-Critique Verification Pass

- **Out-of-Band Verification Architecture**: Integrated `DebateVerifier` (`core/debate/verifier.py`) into `context-manager-cli` (`main.py`) and `rlm_optimized` (`rlm_engine_optimized.py`). Critic (`critique()`) and Refiner (`refine()`) passes run via isolated, out-of-band LLM calls using `InferenceParams.for_critic()` (temp=0.2) and `InferenceParams.for_refine()` (temp=0.1).
- **Zero Context Window Bloat**: Neither the Critic system prompts nor raw JSON critique responses are appended to `TieredMemory` or `SessionState`. Memory context overhead remains strictly 0 tokens.
- **Multi-Turn Tool Chain Support**: Wired verification into both initial user prompt generation and multi-step tool chain iterations in `main.py`, automatically evaluating high-risk tools (`WRITE_FILE`, `EDIT_FILE`, `RUN_COMMAND`) and planning phases.
- **Rich CLI Telemetry & Visual Badges**: Added `print_critique_start()` and `print_refined()` to `context-manager-cli/src/context_manager/cli/dashboard.py`, outputting clean 1-line terminal badges (`✨ Refined Proposal (Fixed: ...)`) highlighting identified flaws.
- **TUI State & Banner Rendering**: Added `"CRITIQUING"` and `"REFINED"` badges to `update_status_bar()` in `rlm_optimized/tui_app.py`, mounting subtle notification widgets directly above refined code responses.
- **Automated Tests**: Updated `core/tests/test_debate.py` and CLI tests. All 159 tests pass across core (115/115) and CLI (44/44).

## 2026-07-24

### Search/Replace Diff Blocks (Approach B) & Dynamic JIT Context Pinning (Approach C)

- **Aider-Style Diff Block Parser**: Added `_parse_diff_block` to `core/tools/implementations.py` to extract `search` and `replace` segments from raw markdown blocks (`<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE`).
- **Resilient `EDIT_FILE` Execution**: Updated `tool_edit_file_impl` to automatically accept Search/Replace blocks from `diff`, `old_text`, `content`, or raw text input, piping extracted text directly into the 6-tier matching engine.
- **Schema Alignment**: Updated `EDIT_FILE` schema in `core/tools/schemas.py` to accept optional `diff` parameter and `search_replace` aliases.
- **Dynamic Context-Aware Pinned Budget**: Scaled `pinned_token_budget` in `MemoryConfig.auto_tune()` based on context window size:
  - `max_tokens <= 4000`: 300 tokens (reclaims ~1,700 tokens on 4k context models)
  - `max_tokens <= 8000`: 600 tokens
  - `max_tokens > 8000`: 1000 tokens
- **Line-Boundary Truncation**: Added line-aware truncation in `pin_file()` (`core/memory/manager.py`) to guarantee pinned file slices never overflow context limits.
- **System Prompt Updates**: Updated `core/prompts/system.py` and `rlm_optimized/prompts.py` to document Search/Replace diff block format.
- **Automated Tests**: Added unit test suite `core/tests/test_diff_edit.py` (6 new test cases). All 141 tests pass across core and CLI.


### Kùzu Graph DB Connection Pooling & Shared `SEARCH_AST` Tool

- **`_KuzuConnectionPool` Singleton**: Refactored `rlm_optimized/repl_sandbox.py` to manage persistent Kùzu DB connections per `project_root`, eliminating 256MB RAM re-allocations and file-lock contention on every graph query call.
- **Canonical Relative Pathing**: Updated `rlm_optimized/ast_indexer.py` and `repl_sandbox.py` to index and resolve canonical project-relative paths, guaranteeing 100% path resolution precision regardless of execution working directory.
- **`SEARCH_AST` Core Tool Integration**: Added `tool_search_ast_impl` in `core/tools/implementations.py`, registered `SEARCH_AST` in `core/tools/registry.py` and `schemas.py` (`AUTO` risk level), bridging AST vector search, class signatures, function source/AST dumps, and local subgraphs to both CLI and TUI frontends.
- **Tool Count: 16 → 17** (`READ_FILE`, `WRITE_FILE`, `EDIT_FILE`, `READ_SYMBOLS`, `LIST_DIR`, `GREP`, `RUN_COMMAND`, `WEB_SEARCH`, `WEB_FETCH`, `DOC_SEARCH`, `WEB_VERIFY`, `SAVE_MEMORY`, `FORMAT_CODE`, `VERIFY`, `ASK_USER`, `GIT`, `SEARCH_AST`).


### Streaming Timeout Fix (UI Hang)

- **60-second timeout on `queue.get()`** in `_stream_llm()`: if the LLM server stops responding mid-stream, the queue blocks forever and the UI freezes
- Root cause: llama.cpp HTTP stream drops connection without sending a final chunk → worker thread hangs on `next(iterator)` → sentinel never sent → `queue.get()` blocks forever
- Fix: `asyncio.wait_for(queue.get(), timeout=60.0)` raises `TimeoutError` → loop breaks → response returned with whatever was collected so far
- Located in `rlm_engine_optimized.py:182-192`

### Active File Pinning (Context Management Fix)

- **New `pin_file()` method on `TieredMemory`**: Keeps recently-read file content in a separate FIFO buffer (max 2 files) that survives compression
- When a file is READ_FILE'd, its content is pinned and injected as a system message right after the system prompt in every subsequent `get_context_for_llm()` call
- Solves the #1 failure mode on 8k context: model reads a file, content gets compressed away, then the model "forgets" exact text when producing EDIT_FILE
- Pinned buffer has a 2000-token budget per file; oldest pin evicted when a 3rd file is read (FIFO)
- `compress_recent()` does not touch pinned files — they're stored separately from messages
- `clear()` also clears pinned files
- Implemented in both `core/memory/manager.py` and `context-manager-cli/src/context_manager/memory/manager.py` (CLI fallback copy)
- Engine hooks in `rlm_engine_optimized.py` (line ~392) and `cli/main.py` (AUTO/CONFIRM/REVIEW tiers) call `memory.pin_file()` after successful READ_FILE

### Context Window: 8k → 12k (8GB Device)

- **`CTX_SIZE` default changed from 8192 → 12288** for `IS_8GB_DEVICE`
- Extra 4k tokens give the model ~50% more room for tool calls and conversation before compression kicks in
- KV cache RAM impact: ~0.2GB → ~0.3GB (still safe on 8GB)
- Auto-tune now falls into the `> 8000` tier: `recent_window=5` (was 3), `message_compact_threshold=800` (was 500)
- READ_FILE budget scales up: 150 lines / 6k chars (was 100 lines / 4k chars)
- Flashlight beam budget scales up: 3 files / 120 lines (was 2 files / 80 lines)
- Override via `RLM_CTX_SIZE` env var

### Unlimited Output Tokens (7B Model Fix)

- **`NUM_PREDICT` changed from 4096 → -1 (unlimited)**: 7B models were hitting the 4096 output token limit mid-code-generation, causing `<tool_call>` tags to never close → silent tool call drops → files not written
- Root cause: Full-file code generation (e.g., HTML+JS snake game ~3000 tokens) plus system prompt, thinking, and tool syntax exceeded the 4096 cap
- `-1` means generate until stop token, EOS, or context window full — no artificial output cap
- `cloud_client.py` updated to omit `max_tokens` field when `-1` (OpenAI API requires omission, not -1)
- `llamacpp_client.py` and `ollama_client.py` already treat `-1` as unlimited — no changes needed

### EDIT_FILE 6-Tier Fuzzy Matching (Core + CLI)

- **Tier 5 threshold lowered**: 75% → 60% similarity ratio, catches more 7B model typos
- **Window size expanded**: ±3 lines sliding window (was ±2) for better difflib search
- **Tier 6 added**: Character-level subsequence matching for typo-ridden input (e.g., `def move_ snake` → `def move_snake`)
- **Closest-match diagnostic**: When all 6 tiers fail, shows the closest matching block with % similarity and line number so the model can self-correct
- **READ_FILE nudge**: When EDIT_FILE fails, engine injects "READ_FILE first, then copy exact text" — directly addresses the #1 failure mode of small models skipping the read step
- CLI `tool_edit_file` upgraded from exact-match-only to 3-tier matching (exact → whitespace-agnostic → difflib 60%)

### GIT Tool (New — 12 Subcommands)

- Added `GIT` tool with operations: status, diff, log, show, branch, blame, commit, add, restore, stash, remote, shortlog
- Safety classification: read ops (status, diff, log, show, branch, blame, remote, shortlog) = AUTO; write ops (commit, add, restore, stash) = CONFIRM; destructive ops (push, reset, rebase, merge, clean) = blocked with REVIEW requirement
- `git commit` moved from REVIEW → CONFIRM in classification.py (common operation shouldn't require explicit approval)
- Schema with full alias support (subcommand/cmd/action, message/msg, files/path, flag/f/ref, count/n/limit)

### GREP Upgrade — Ripgrep Integration

- `tool_grep_impl` now uses `rg` (ripgrep) when available for 10-50x speed on large codebases
- ripgrep provides: `.gitignore` awareness, binary detection, Unicode support, parallel threads, memory-mapped I/O
- Falls back to pure Python grep when `rg` is not installed
- Output capped at 30 matches (was 20) with context lines
- Fixed `shlex.quote` bug that was double-quoting patterns and breaking ripgrep

### System Prompt Update

- Tool strategy updated to mention GIT and ripgrep capabilities
- Added GIT to the mandatory tool strategy workflow

### Tool Count: 15 → 16

```
Core:     READ_FILE, WRITE_FILE, EDIT_FILE, READ_SYMBOLS, LIST_DIR, GREP, RUN_COMMAND
Web:      WEB_SEARCH, WEB_FETCH, DOC_SEARCH, WEB_VERIFY
Memory:   SAVE_MEMORY
Debug:    FORMAT_CODE, VERIFY, ASK_USER
VCS:      GIT (NEW)
```

---

## 2026-07-23

### Unified Core Library (`core/`)

- Created standalone `core/` package with 28 Python files across 8 subpackages
- `core/tools/` — Unified ToolRegistry with 15 tools, schema validation, alias resolution, AUTO/CONFIRM/REVIEW risk tiers, context-budget-aware output
- `core/api/` — LLMClient protocol, InferenceParams with phase-based presets, `create_client()` factory for LM Studio, llama.cpp, Ollama, Groq, Together, OpenRouter, OpenAI, Gemini
- `core/memory/` — TieredMemory (L0-L3), SessionState, SessionPersistence, ProjectMemory, SelectiveCompressor (4-level), TokenCounter with tiktoken fallback
- `core/errors/` — 7 structured error types (TorchlightError, ToolError, ParseError, ContextOverflowError, ConnectionError, SecurityError, ToolValidationError) with RecoveryEngine escalation ladder (RETRY → COMPRESS_AND_RETRY → SKIP → ABORT) and get_recovery_hint()
- `core/compression/` — VerbatimCompactor with Head/Tail budget, ConversationSummarizer
- `core/flashlight/` — SymbolIndex (Python/JS/TS/Go/Rust), Flashlight beam retrieval with context-scaled config
- `core/execution/` — ExecutionFeedbackLoop with auto test detection (pytest/npm/cargo)
- `core/prompts/` — Unified system prompt with context-size-aware tool syntax instructions
- Wrote 89 tests in `core/tests/` — all passing
- Updated CLI and TUI frontends to import from `core/` with `try/except ImportError` fallback to local modules for backward compatibility

### TUI-Only Refactor

- Removed `frontend/` (React + Monaco + Tauri GUI), `backend/` (FastAPI + WebSocket server), `dev_tools/`
- Stripped GUI/backend code; project is now TUI-only terminal agent
- Rewrote all documentation for terminal-only architecture
- Wrote 44 core tests (models, token counter, tool registry, phase detection)
- Updated AGENTS.md, pyproject.toml, run.sh for TUI-only workflow
- Cleaned stale planning docs, orphaned artifacts, and stale .gitignore entries

### RLM Agent Context & Hallucination Fixes

- Enforced "Write-to-Disk" strategy for implementation plans in the system prompt (`prompts.py`) to prevent context loss from memory compression. The agent now saves plans to `implementation_plan.md` and reads them back on resume.
- Added **`EDIT_FILE` Tool (`rlm_optimized`)**: Implemented a surgical search-and-replace tool for the LLM agent to modify existing files without dumping the full file back out. This heavily optimizes output token usage (reducing context limit exhaustion). **(Update: Upgraded tool with whitespace-agnostic fuzzy matching to prevent exact-match failures caused by LLM indentation and spacing hallucinations).**
- Added **TUI Crash Fix**: Implemented `rich.markup.escape` in `tui_app.py` for API error exceptions to prevent silent crashes when the model hits the 400 Bad Request Context Overflow limit.
- Added **LLM Runaway Loop Prevention**: Added strict `stop` sequence arrays (`\nAction:`, `Action:`, `Observation:`) to `llamacpp_client.py`, `cloud_client.py`, and `ollama_client.py` to hard-kill runaway hallucinations instantly.
- Added **Persistent Project Memory (`.torchlight_memory.md`)**: Modified `prompts.py` to dynamically load a local `.torchlight_memory.md` file into the system prompt upon agent initialization. The agent is strictly instructed to use `WRITE_FILE` or `EDIT_FILE` to document project tech stack, architectures, and dependencies here so it no longer starts fresh or has to re-discover basic project context in subsequent loops.
- Added **Implementation Plan Formatting**: Enforced strict bulleted checklist formatting (`- [ ]`, `- [x]`) for `implementation_plan.md` in `prompts.py` to prevent verbose plan generation, and explicitly directed the agent to use `EDIT_FILE` to check off completed tasks to prevent unnecessary full-file overwrites.
- Added **Genuine Multiple Read Support**: Modified `rlm_engine_optimized.py` to clear the `_executed_tools` duplicate tracking history whenever a state-mutating action (`WRITE_FILE`, `EDIT_FILE`, `RUN_COMMAND`, `<CODE>`) succeeds. This prevents the harness from incorrectly blocking the LLM when it genuinely needs to re-read a file it just modified.
- Fixed **Duplicate Tool Check Loop**: Migrated `rlm_engine_optimized.py` to use the unified `core.tools.registry.ToolRegistry` instead of legacy local fallback implementations, ensuring semantic tool failures (`success=False`) correctly retain execution history and trigger the `duplicate` loop breaker instead of getting stuck in infinite silent failures.
- Added **Session Summarization & Continuous Context**: Implemented automatic session summarization in `rlm_engine_optimized.py`. At the end of every task (`final_answer`), the agent uses its SLM client to generate a concise summary of actions and learnings. This summary is appended to `.torchlight_history.log`, and `prompts.py` automatically injects the recent history into the system prompt for continuous context tracking across tasks.
### Key Improvements (Pre-Refactor)

- Execution feedback loop: auto-runs tests after file edits
- Execution policy: classifies user intent for direct tool routing
- Failure policy: structured retry with troubleshoot mode
- Response continuation: truncated response detection + overlap merge
- Trust pipeline: validates file writes with syntax check + compile + repair
- Selective memory compression: 4-level progressive (FULL/COMPACT/SUMMARY/HINT)
- State machine hardening: guaranteed terminal events, no stuck states
