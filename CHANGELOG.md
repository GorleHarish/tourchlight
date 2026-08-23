# Changelog

All notable changes to Torchlight will be documented in this file.

## [v3.0.0] - 2026-08-17

### Added & Improved
- **Plan Mode for Torchlight Agent (`ExecutionMode.PLAN`)**:
  - Added dedicated `ExecutionMode.PLAN` ("plan") to `ExecutionMode` enum in `core/memory/models.py`.
  - **Comprehensive `PLAN_PROMPT` in `core/prompts/system.py`**:
    - Mandates workspace discovery via read-only tools (`LIST_DIR`, `SEARCH_AST`, `GREP`, `READ_FILE`) to understand existing code and dependencies before creating a plan.
    - Default behavior: Brainstorms complete architecture, risks, edge cases, and steps, then writes/updates `implementation_plan.md` via `WRITE_FILE`/`EDIT_FILE` with structured sections: Problem Statement & Goal, Architecture & Design Decisions, Open Questions / User Review Required, Proposed Changes (`[MODIFY]`/`[NEW]` with atomic `- [ ]` checkboxes), and Verification Plan (automated tests + manual steps).
    - Enforces non-mutation of application source code during Plan Mode.
    - Emits `<FINAL_ANSWER>...</FINAL_ANSWER>` summarizing the plan upon completion.
  - **Engine & CLI Integration**:
    - `RLMEngineOptimized` and `StreamingChatSession` support `ExecutionMode.PLAN`.
    - Verification Gate permits `<FINAL_ANSWER>` with pending `- [ ]` tasks when `implementation_plan.md` exists, but rejects premature `<FINAL_ANSWER>` if `implementation_plan.md` was not created.
    - CLI `/mode plan`, `context plan "Feature title"`, and `--mode plan` flag.
    - TUI `SessionModePickerModal` and HUD support with interactive Plan Mode button, `MODE: PLAN` badge, and styling.
  - **Comprehensive Unit Testing**:
    - Added `core/tests/test_plan_mode.py` verifying state normalization, resilient phase detection, verification gate handling for both present and missing plans, and CLI streaming chat session execution.
    - Added Plan Mode tests to `context-manager-cli/tests/test_phase_detection.py`.

## [v2.9.0] - 2026-08-15


### Added & Improved
- **Modular Mode-Tailored System Prompt Templates (`core/prompts/system.py`)**:
  - Replaced monolithic prompt concatenation with 4 dedicated templates (`CHAT_PROMPT`, `PLAN_PROMPT`, `CODE_PROMPT`, `TROUBLESHOOT_PROMPT`) sharing unified core directives (`SHARED_BASE_DIRECTIVES`).
  - **`CHAT_PROMPT`**: Dedicated to conversational Q&A, conceptual discussions, and codebase exploration. Wraps direct answers in `<FINAL_ANSWER>...</FINAL_ANSWER>` and restricts tool use to read-only lookups (`SEARCH_AST`, `GREP`, `READ_FILE`, `WEB_SEARCH`). Completely stripped of file writing, `implementation_plan.md`, and write/test validation gates.
  - **`PLAN_PROMPT`**: Mandates workspace discovery first (`LIST_DIR`, `SEARCH_AST`, `GREP`) before authoring checkbox tasks (`- [ ]`) in `implementation_plan.md`.
  - **`CODE_PROMPT`**: Enforces surgical edits via `EDIT_FILE`, write gate validation, and test verification loops.
  - **`TROUBLESHOOT_PROMPT`**: Guides un-truncated traceback analysis, AST caller/callee tracing, and root-cause repair.
  - Dynamic template injection via `get_phase_system_prompt(phase)` with active tool syntax appending.
- **Chat Mode Isolation & Resilience**:
  - **Phase Detection Guard**: `_detect_phase()` in both `RLMEngineOptimized` and `StreamingChatSession` explicitly preserves `phase="chat"` when `execution_mode == ExecutionMode.CHAT` or `mode == "chat"`, preventing keyword triggers like `"error"`, `"fix"`, `"write"`, or `".py"` from flipping Q&A sessions into Code or Troubleshoot mode.
  - **L0 Working Memory Scratchpad Filtering (`core/memory/manager.py`)**: `format_l0_scratchpad()` suppresses disk task matrix injection (`get_compact_task_matrix()`) in Chat Mode, preventing leftover tasks from `implementation_plan.md` or `.torchlight/tasks.md` from bleeding into the LLM's active scratchpad.
  - **Verification Gate Bypass (`rlm_optimized/rlm_engine_optimized.py`)**: Engine's Verification Gate now bypasses pending task completion checks and zero-tool rejection in Chat Mode, allowing direct `<FINAL_ANSWER>` responses to be delivered immediately.
- **Comprehensive Unit Testing**:
  - Added `test_chat_system_prompt_isolation` and `test_l0_scratchpad_suppresses_task_matrix_in_chat_mode` in `core/tests/test_prompts_and_memory.py`.
  - Added `test_chat_mode_phase_detection_resilience` and `test_chat_mode_verification_gate_bypassed` in `core/tests/test_session_modes.py`.
  - Added `test_detect_chat_mode_resilient` in `context-manager-cli/tests/test_phase_detection.py`.
  - All 534 core tests and 47 CLI tests passing.

## [v2.8.0] - 2026-08-10

### Fixed
- **Production-Ready GBNF Grammar v2.2 (`rlm_optimized/grammar.gbnf`)**: Fixed the post-v2.1 parser regression where the agent rambled prose instead of emitting tool calls, stalling the solve loop until the token budget was exhausted.
  - **Reasoning Rule Removed**: `reasoning ::= [^<\x00]+` accepted any prose, masking EOS tokens (`<|im_end>`, `</s>` contain `<`), so prose answers never reached `finish_reason: stop` and burned the full 2048-token budget. Reasoning now lives in `implementation_plan.md` (already mandated by the system prompt).
  - **Single-Action Root**: `root ::= step+` forced a second action after every valid tool call, so generation continued past a complete call and rambled. Now `root ::= action ws` — one action per response, chains driven by the engine loop.
  - **Tool Whitelist Parity**: Added `SET_PHASE`, `PLAY_AND_VERIFY_GAME`, `SELF_IMPROVE_GAME` to both `tool-name-val` and `tool-name-str`, matching the 22-tool registry (previously advertised but token-blocked).
  - All multi-line rule alternatives flattened to single-line (TurboQuant GBNF parser compatibility), unbounded wildcards replaced with bounded char classes, and `<ERROR>` retry tag retained.
- **Stop-Token Handling**: Added `</tool_call>`, `</WRITE_FILE>`, `</ERROR>` to the llama-server stop list in `rlm_optimized/llamacpp_client.py` and to `_STOP_TAG_PAIRS` in `rlm_optimized/rlm_engine_optimized.py`, so `_repair_stop_tokens` re-appends stripped closing tags for the parser.
- **RFC 8259 JSON Examples (`rlm_optimized/prompts.py`)**: Converted all single-quoted `<tool_call>` JSON examples to double quotes (with correct f-string escaping), fixing invalid JSON in the injected system prompt.

### Added
- **Regression Tests (`rlm_optimized/test_grammar_parse.py`)**: Whitelist↔registry parity test (against `core/tools/schemas.py` `TOOL_SCHEMAS`), no-reasoning-rule guard, single-action-root guard, and live probe asserting a well-formed `<tool_call>` with `finish_reason == "stop"`.
- **Chat Phase Prompt Directive (`core/prompts/system.py`)**: `PHASE_PROMPTS["chat"]` now instructs the model to wrap conversational answers in `<FINAL_ANSWER>...</FINAL_ANSWER>` to satisfy the single-action grammar.

### Notes
- Session summarization intentionally bypasses grammar (`use_grammar=False`).
- Added `web` extra (`playwright>=1.60.0`) to `core/pyproject.toml`; installed into system Python 3.9 matching the already-cached Chromium 1223 revision. This resolves the previously environmental-only failures in `core/tests/test_game_self_improver.py` (all 459 core tests now pass).

## [v2.7.0] - 2026-08-04

### Added & Improved
- **Production-Ready GBNF Grammar Schema v2.0 (`rlm_optimized/grammar.gbnf`)**:
  - **Multi-Step Agent Trajectory Support**: Fixed single-action root rule `root ::= reasoning (action | "")` to `root ::= step+ ws` (`step ::= reasoning? action ws`), enabling continuous multi-step tool execution sequences (`READ_FILE → EDIT_FILE → VERIFY → FINAL_ANSWER`) in a single generation pass.
  - **Closing-Tag Collision Elimination**: Replaced naive `any-char*` in `<WRITE_FILE>`, `<CODE>`, `<SUB_QUERY>`, `<FINAL_ANSWER>`, and `<ERROR>` content blocks with explicit character-by-character prefix exclusions (e.g. `write-file-unit`), preventing ambiguous sampler states at `<` characters.
  - **Reasoning Boundary Disambiguation**: Restricted reasoning prose (`reasoning ::= [^<\x00]+`) so bare `<` characters strictly mark action tag boundaries, preventing reasoning from consuming action tags.
  - **RFC 8259 JSON & Data-Type Compliance**:
    - Separated `null` into a distinct `null-val ::= "null"` type rather than grouping it under `bool-val`.
    - Added scientific notation support (`1e10`, `-2.5e-3`) to `number-val` and enforced RFC 8259 leading zero restrictions.
    - Supported flexible key ordering in `tool-call-json` (`{"name": "...", "arguments": {...}}` and `{"arguments": {...}, "name": "..."}`).
    - Added 4-hex-digit unicode escape validation (`\uXXXX`) and enumerated valid JSON string escape sequences.
  - **Sampler Performance Optimization**: Removed unbounded `any-char` wildcards (~65k valid tokens/step) across all rules, eliminating 10–50× constrained sampling overhead.
  - **Structured Tool Failure / Retry Tag (`<ERROR>`)**: Added `<ERROR>` action tag for direct integration with `RecoveryEngine`.

## [v2.6.0] - 2026-08-02

### Added & Improved
- **Headroom-Adaptive Context Budget Coordinator (`ContextBudget` in `core/memory/budget.py`)**: Replaces static reservation with a headroom-driven coordinator. L0 scratchpad scales 150→1200 tokens (~20% of idle headroom, computed against a 0.85 target utilization), scratchpad entry limits scale 60→240 chars, and section caps scale 3→8. Pinned-file budget shrinks under pressure but never exceeds the configured `base_pinned_tokens` (explicit user choice is a hard ceiling).
- **L0 Scratchpad Hygiene & Priority-Ordered Eviction (`core/memory/manager.py`)**: Per-entry 120-char truncation with whitespace/newline flattening, priority-ordered greedy assembly under a 1600-char cap, and low-priority section dropping under pressure so the highest-value state (active goal, modified files, active errors, failing tests) always survives.
- **Verification-Gate Prompt Parity (`core/prompts/system.py`)**: New `UNVERIFIED CHANGES` / `UNRESOLVED TEST FAILURES` directives — accepted final answers that mark pending changes as done are treated as failed turns (broken edits reverted, blocker reported with surgical traceback), and the engine re-verifies pending changes before accepting final answers.
- **CLI Runtime Core Activation Fix (`context-manager-cli/run.sh`)**: Added the repo root to `PYTHONPATH` (`$(pwd)/src:$(pwd)/..`) so the CLI's feedback-loop delegation actually resolves `ExecutionFeedbackLoop` etc. from `core` at runtime instead of silently using stale local fallback modules — Phases 2–3 verification-gate fixes are now active in the CLI.
- **Comprehensive Unit Testing**: Added `core/tests/test_context_budget.py` (7 tests covering L0 expansion/shrink, bounds, and explicit pinned-budget ceiling respect) plus scratchpad-hygiene and prompt gate-parity tests. Core suite: 348 tests passing; CLI suite: 46 tests passing with core delegation verified active.

## [v2.5.0] - 2026-07-30

### Added & Improved
- **Autonomous Playwright Web Outcome Inspection & Verification**:
  - **Multi-Tiered Web Inspection Engine**: Extended `WebOutcomeInspector` in `core/execution/web_inspector.py` to capture Accessibility Tree (`ax_tree`) snapshots, DOM layout overflow warnings (`overflow_warnings`), interactive component counts (`buttons`, `inputs`, `links`), and HTML5 canvas pixel diagnostics (`BLANK_CANVAS`).
  - **Interactive UI Action Sequences**: Added support for multi-step UI testing (`click`, `fill`, `type`, `key_press`, `hover`, `wait_for_selector`) in `_inspect_playwright()`.
  - **Direct HTTP/HTTPS URL Inspection**: Enabled testing active dev servers (e.g., `http://localhost:5173`) alongside local static `.html` files.
  - **Automated Feedback Loop Triggering**: Updated `ExecutionFeedbackLoop` in `core/execution/feedback_loop.py` to watch `.jsx`, `.tsx`, `.vue`, `.svelte`, `.css`, and `.js` files, with vendor directory exclusions (`node_modules`, `.venv`, `dist`, `build`, `.git`, `.torchlight`, `coverage`, `.next`).
  - **Non-Vision Model Strategy (Qwen 2.5 Coder)**: Serialized visual, DOM, accessibility, and console signals into compact Markdown text (<300 tokens), enabling text-only models to inspect web execution outputs and self-correct autonomously.
  - **Schema & Tool Registration**: Updated `INSPECT_WEB` schema in `core/tools/schemas.py` and `tool_inspect_web_impl()` in `core/tools/implementations.py` to expose interactive action steps.
- **Engine Feedback Message Assembly Fix**: Fixed variable overwrite bug in `rlm_optimized/rlm_engine_optimized.py` so auto-test and `INSPECT_WEB` results are cleanly appended to the assistant feedback context instead of being discarded.
- **Read-Only Tool Exemptions**: Added `INSPECT_WEB`, `SEARCH_AST`, and `UPDATE_TASK_GRAPH` to `_READ_ONLY_TOOLS` in `rlm_optimized/rlm_engine_optimized.py`, eliminating false duplicate tool call warnings.
- **Engine Performance & Latency Optimization**: Set `enable_debate: bool = False` by default in `RLMEngineOptimized.__init__`, bypassing the redundant 2nd LLM critique pass per turn to double tool execution speed for local models while preserving empirical Playwright & test verification.
- **CLI & Feedback Loop Memory Sync**: Updated `context-manager-cli/src/context_manager/cli/main.py` and `core/execution/feedback_loop.py` to reliably consume test/web feedback and reset `_last_test_result` to prevent stale output repetition.

## [v2.4.0] - 2026-07-30

### Added & Improved
- **Explicit Session Modes (`💬 Chat Mode` vs `🎯 Goal Mode`)**:
  - **Core Model & Memory Control**: Added `ExecutionMode` enum (`CHAT`, `GOAL`) in `core/memory/models.py` attached to `SessionState` and `ContextSnapshot`.
  - **Lazy Task Memory Initialization**: Chat Mode suppresses `.torchlight/goal_spec.json` and `.torchlight/tasks.md` creation for clean, uncluttered Q&A sessions. Goal Mode explicitly creates disk task tracking files on demand.
  - **Zero-Config `.gitignore` Auto-Patching**: `ensure_project_initialized()` in `core/memory/persistence.py` automatically appends `.torchlight/` to the project `.gitignore` to prevent dirty working trees.
- **CLI Mode Selection & Slash Commands**:
  - **`--mode` Option**: Added `--mode` (`-m`) option to `context chat` (`context chat --mode chat` vs `context chat --mode goal`).
  - **`context goal` Subcommand**: Added `context goal "<title>"` subcommand to launch directly into Goal Mode.
  - **Runtime `/mode` Slash Command**: Added `/mode` slash command in interactive CLI sessions (`/mode chat`, `/mode goal`, `/mode`).
  - **Interactive Rich Tooltips**: Formatted launcher and CLI help text with rich UX tooltips explaining Chat Mode vs Goal Mode.
- **TUI Mode Picker Modal & Shortcut Controls**:
  - **`SessionModePickerModal`**: Added interactive modal dialog in `rlm_optimized/tui_app.py` featuring mode options and inline explanatory tooltips.
  - **Shortcut & Command Integration**: Added `Ctrl+G` shortcut binding and `/mode` slash command handler in TUI.
- **Comprehensive Unit Testing**:
  - Added `core/tests/test_session_modes.py` verifying mode isolation, suppression of task files in Chat Mode, initialization of task files in Goal Mode, and `.gitignore` patching (222 core tests + 46 CLI tests passing).

## [v2.3.0] - 2026-07-30


### Added & Improved
- **Unified Workspace Task Extraction Helper (`get_workspace_pending_tasks`)**:
  - Added `core/tools/task_helpers.py` to extract pending tasks (`[ ]`, `[/]`, `[-]`, `[~]`, `pending`, `in_progress`) across `implementation_plan.md`, `.torchlight/tasks.md`, and `.torchlight/goal_spec.json`.
- **`implementation_plan.md` Plan Execution & Verification Gate Enforcement**:
  - Updated Verification Gate in `rlm_optimized/rlm_engine_optimized.py` to inspect `implementation_plan.md` via `get_workspace_pending_tasks()` and reject `<FINAL_ANSWER>` calls if open tasks exist.
  - Enhanced rule #7 response parser (`is_planning_cot`) to classify `implementation_plan.md` references as `thinking`, preventing plain-text plan summaries from auto-converting to `<FINAL_ANSWER>`.
- **System Scratchpad Task Visibility**:
  - Updated `format_l0_scratchpad()` in `core/memory/manager.py` to inject `- Pending Tasks: ...` into `[L0 WORKING MEMORY SCRATCHPAD]` system prompt context when open tasks exist in `implementation_plan.md`.
- **System Prompt Directives**:
  - Updated `core/prompts/system.py` (`SYSTEM_PROMPT` & `PHASE_PROMPTS["plan"]`) and `rlm_optimized/prompts.py` to explicitly forbid delivering `<FINAL_ANSWER>` right after creating `implementation_plan.md`.
- **Unit & Integration Test Coverage**:
  - Added `core/tests/test_plan_execution_loop.py` verifying task parsing, scratchpad formatting, and Verification Gate rejections (218 core tests passing).

## [v2.2.0] - 2026-07-30

### Added & Improved
- **Dynamic L0 Working Memory Scratchpad Enhancements**:
  - **Anti-Looping `tried_and_failed` Buffer**: Updated `format_l0_scratchpad()` in `core/memory/manager.py` to render `tried_and_failed[-3:]` entries directly in system prompt context, preventing local LLMs from repeating failed strategies or bad tool calls.
  - **Memory Persistence Method**: Added `TieredMemory.record_memory()` to dynamically record facts, decisions, and failed strategies into active session state and sync with `.context-memory.json`.
- **Model Memory Control Tool (`SAVE_MEMORY`)**:
  - **Active Session Sync**: Enhanced `tool_save_memory_impl` in `core/tools/implementations.py` to accept `entry` parameter aliases and immediately update active `TieredMemory` state in addition to disk persistence.
- **Dynamic Task Graph Updates (`UPDATE_TASK_GRAPH`)**:
  - **Mid-Trajectory Re-Planning**: Added `UPDATE_TASK_GRAPH` tool (`tool_update_task_graph_impl`) enabling agents to dynamically add sub-tasks (`add_subtask`), skip tasks (`skip_task`), or modify statuses in `.torchlight/goal_spec.json`.
  - **Schema & Risk Classification**: Registered `UPDATE_TASK_GRAPH` schema in `core/tools/schemas.py` and classified it under `AUTO` risk tier in `core/tools/classification.py`.
- **AST-Driven Inter-Task Symbol Handoffs**:
  - **Automatic Symbol Extraction**: Integrated `SymbolIndex` from `core.flashlight.indexer` into `AutonomousHarness.run_micro_epoch()` to automatically extract function/class signatures from target files upon task completion, enriching `TaskSpec.outputs_summary` for downstream epoch handoffs.
- **Comprehensive Unit Test Coverage**:
  - Added unit test suite `core/tests/test_scratchpad_enhancements.py` verifying scratchpad formatting, memory recording, `SAVE_MEMORY`, `UPDATE_TASK_GRAPH`, and AST symbol handoffs (213 core tests passing).

## [v2.1.0] - 2026-07-29

### Added & Improved
- **Multi-Line Prompt Support in TUI**:
  - **Textual `TextArea` Integration**: Upgraded `#user-input` prompt widget from single-line `Input` to multi-line `TextArea` in `tui_app.py`, enabling pasting and editing multi-line prompts seamlessly without newline stripping.
  - **Smart Key Handling**: Intercepts `Enter` to submit the prompt and supports `Shift+Enter` for line breaks within multi-line prompts.
  - **Dynamic Input Auto-Sizing**: Refactored `tui_app.tcss` `#user-input` and `#input-row` styles to support responsive auto-height (min 3 lines, max 6 lines).
  - **Help Modal & Shortcut Documentation**: Updated the shortcuts help modal (`ShortcutsHelpModal`) to explicitly document `Enter` and `Shift+Enter` input behavior.
- **Natural Language Code Interception Guard**:
  - **Multi-Layer Validation**: Implemented a 3-layer guard preventing natural language prose/reasoning containing backticks from being parsed and executed as Python code in the REPL sandbox (`_parse_response` AST check + `solve_async` dispatch validation + `REPLSandbox` prose heuristic).

## [v2.0.0] - 2026-07-29

### Added & Improved
- **Fault-Tolerant Diff Block Parsing**:
  - **Missing Divider Auto-Recovery**: Enhanced `_parse_diff_block` in `core/tools/implementations.py` to recognize diff blocks where the model omitted the `=======` divider line between `<<<<<<< SEARCH` and `>>>>>>> REPLACE` tags.
- **Graceful `EDIT_FILE` to `WRITE_FILE` Auto-Fallback**:
  - **Full-Content Auto-Routing**: Automatically forwards `EDIT_FILE` calls passing full `content` or `code` arguments without `old_text` to `tool_write_file_impl`.
  - **Non-Existent File Creation**: Automatically creates non-existent target files via `WRITE_FILE` when `EDIT_FILE` is called with new content or code instead of failing with `File not found`.
- **Unit Test Coverage**:
  - Added unit test cases (`test_parse_diff_block_missing_divider`, `test_edit_file_auto_fallback_to_write`) in `core/tests/test_diff_edit.py` verifying fault-tolerant parsing and auto-fallback routing (201 core tests passing).

## [v1.9.1] - 2026-07-29

### Fixed & Improved
- **Robust Reasoning & Answer Tag Parsing**:
  - **Server Stop-Token Truncation Handling**: Fixed tag regexes in `_parse_response` (`(?:</TAG>|$)`) to handle local llama.cpp / Ollama / API server stop-token behavior where closing tags like `</FINAL_ANSWER>` or `</TOOL>` are omitted by the server upon hitting stop sequences.
  - **Explicit `<think>` Block Extraction**: Isolated `<think>...</think>` and `<thought>...</thought>` reasoning tags emitted by reasoning models (Qwen 2.5, DeepSeek R1, Gemma) into the Reasoning UI block instead of leaking them into answer output.
  - **Mid-Sentence Tag Split Prevention**: Fixed an issue in `_parse_response` where `<FINAL_ANSWER>` tags mentioned mid-sentence (e.g., `"I will use <FINAL_ANSWER> to..."`) caused reasoning text to be truncated mid-sentence and sentence fragments assigned to the Final Answer panel.
  - **Direct Plain-Text Answer Support**: Non-tool conversational responses without explicit `<FINAL_ANSWER>` tags are now cleanly extracted as final answers, eliminating infinite thinking loop degradation and unnecessary prompt nudges.
  - **Template Placeholder Filtering**: Added filtering for template artifact tags like `<FINAL_ANSWER>your answer</FINAL_ANSWER>` copied from prompt examples.
  - **Unit Test Coverage**: Added comprehensive test cases in `core/tests/test_rlm_engine.py` covering reasoning extraction, mid-sentence tag prevention, stop-token truncation, and direct text answer parsing (245 tests passing).

## [v1.9.0] - 2026-07-29

### Added & Improved
- **Enhanced Web Browsing & Stealth Anti-Blocking Engine**:
  - **Structure-Preserving HTML Parser (`StructurePreservingHTMLParser`)**: Isolates `<pre><code>` blocks, parameter tables, lists, and headings while stripping navigation bars, sidebars, footers, and script noise. Uses depth tracking (`code_depth`, `skip_depth`) to cleanly render nested `<pre><code>` tags without duplicate backtick fences.
  - **Stealth Browser Request Headers (`_get_browser_headers`)**: Passes realistic browser fingerprints (`Sec-Ch-Ua`, `Sec-Fetch-Dest`, `Accept-Language`) and HTTP/2 headers to prevent generic scraper blocks.
  - **Remote Headless Playwright Fallback (`_fetch_remote_playwright`)**: Tier-2 fallback engine routing remote URLs through Playwright when HTTP GET returns 403, 429, Cloudflare anti-bot challenges, or empty JavaScript SPAs.
  - **Indirect Prompt Injection Sanitization**: Automatically escapes `<tool_call>` tags in fetched web page content to prevent poisoned web pages from injecting unauthorized tool calls into LLM conversation history.
  - **Version-Aware Dependency Query Augmentation (`_augment_query_with_project_deps`)**: Auto-inspects `pyproject.toml` (Poetry & PEP 621 array syntax) and `package.json` in project root to lock `DOC_SEARCH` queries to active library versions (e.g. `pydantic v2`, `react v19`).
  - **Unified System Prompt Alignment**: Declared `WEB_FETCH`, `DOC_SEARCH`, `WEB_SEARCH`, and `WEB_VERIFY` explicitly in `[TOOL PIPELINE]` across core system prompts (`core/prompts/system.py`), CLI prompts (`prompts.py`), and small-context prompts (`prompts_minimal.py`).
  - **Web Tool Unit Tests (`test_enhanced_web_tools.py`)**: Unit test suite verifying structure-preserving HTML parsing, depth tracking, header generation, version query augmentation, prompt injection sanitization, and web tool execution (198 tests passing).


## [v1.8.0] - 2026-07-29

### Added & Improved
- **Zero-Context Code Quality Harness**: Deterministic post-processing, formatting, and multi-language validation engine operating inside the Python harness layer without consuming LLM context tokens:
  - **Format-on-Save (`_format_code_on_save`)**: Automatically runs local code formatters (`ruff format`/`black` for Python, `prettier` for JS/TS/JSON/CSS/HTML, `gofmt` for Go, `rustfmt` for Rust) on file write/edit tool execution with a 2-second timeout.
  - **Multi-Language Syntax & Bracket Validator (`_check_syntax`)**: Inline AST/JSON/JS bracket parsing validating Python syntax, JSON structural integrity, and JS/TS/C bracket balancing (stripping string literals and comments).
  - **Stub & Placeholder Detector (`_detect_stubs`)**: Scans written code for lazy LLM placeholder comments (`# TODO: implement`, `// ... existing code`, `pass # stub`) and appends warning notes to tool output to ensure complete implementation.
  - **POSIX Whitespace & Tab Normalizer (`_normalize_whitespace`)**: Converts mixed tabs to 4 spaces, strips trailing line whitespace, and guarantees trailing newlines (strictly preserving tab indentation for `Makefile`, `Go`, `TSV`, and `.mk` files).
  - **Harness Test Suite (`test_code_quality_harness.py`)**: Unit tests covering format-on-save, syntax validation, stub detection, Makefile tab preservation, and fuzzy edit matching.

## [v1.7.0] - 2026-07-29

### Added
- **Manual Compact Button**: Added an explicit `🗜️ Compact` button to the TUI input header bar ([tui_app.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/tui_app.py)) next to the model selector and context progress badge, providing an immediate visual trigger for manual context compaction.
- **Phase-Tailored System Prompt Injection**: System prompt generator (`get_phase_system_prompt()`) appending phase-specific instructions for `plan`, `code`, `troubleshoot`, and `chat` modes.
- **Anti-Symptom-Patching Directives**: Hardcoded directives in `SYSTEM_PROMPT` prohibiting masking symptoms, swallowing exceptions, returning dummy fallbacks, or deleting failing unit tests.
- **Dynamic L0 Working Memory Scratchpad**: `format_l0_scratchpad()` in `TieredMemory` formatting active goal, modified files, active errors, failing tests, and key decisions into system context on every turn.
- **Context Headroom Calculation**: `get_available_headroom()` in `TieredMemory` for computing remaining token capacity prior to tool formatting.
- **Comprehensive Unit Testing**: Added `core/tests/test_prompts_and_memory.py` testing phase prompt generation, anti-patching rules, L0 scratchpad formatting, and headroom calculations.

### Fixed & Improved
- **Live Context Progress Bar UI Update**: Fixed UI context token percentage calculation in [tui_app.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/tui_app.py) (`_build_context_progress_text`) to use live memory token count (`mem.total_tokens`) rather than a static estimation heuristic, ensuring the progress bar and percentage immediately drop upon compaction.
- **12k TurboQuant Context Budget Calibration**: Formally documented the 12,288 token context budget breakdown in `AGENTS.md` and `LEARNINGS.md`, detailing allocation for L0 scratchpad, full 3-file AST flashlight beam (~1.5k tokens), and ~9.6k tokens (~80%) conversation headroom.
- **CLI Phase Prompt Integration**: Front-end CLI loop now dynamically injects phase prompts based on task phase detection (`_detect_phase()`).
