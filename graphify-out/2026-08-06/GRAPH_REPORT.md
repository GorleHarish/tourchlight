# Graph Report - tourchlight v1_i6  (2026-08-06)

## Corpus Check
- 226 files · ~167,726 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3341 nodes · 5975 edges · 217 communities (176 shown, 41 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 283 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c572547c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- implementations.py
- datetime
- ProjectSnapshot
- SymbolIndex
- ToolRegistry
- BaseSkill
- LMStudioClient
- TokenCounter
- CloudClient
- ActionTracker
- test_resizer.py
- test_enhanced_web_tools.py
- test_errors.py
- test_implementations.py
- test_web_inspector.py
- Detailed Bug Reports & Resolutions
- TrajectoryLogger
- InferenceParams
- ensure_project_initialized
- repl_sandbox.py
- android_ref_build.md
- 🟡 Medium Difficulty
- test_tui_tool_cards.py
- PlanningSkill
- ContextDashboard
- DebateVerifier
- config.py
- StreamingChatSession
- Architectural Learnings & Engineering Principles
- LLMClient
- Changelog
- RLMEngineOptimized
- PyASTVisitor
- LlamaCppClient
- validate_tool_call
- android_ref_runtime.md
- VerbatimCompactor
- ContextBudget
- on
- core/memory/manager.py
- PaneResizer
- CenterEmptyState
- TDDSkill
- Top 20 Tool-Calling Issues — Ranked by Value Generation for Tool Quality Improvement
- android_ref_emulator.md
- test_phase_detection.py
- test_tui_transcript_widgets.py
- test_tui_file_tree.py
- VerbatimCompactor
- core/memory/models.py
- MessageRole
- test_tui_status_bar.py
- SkillResult
- Message
- main_optimized.py
- TorchlightApp
- Torchlight Architecture
- tool_edit_file_impl
- ProjectGraph
- test_enhanced_memory_retrieval.py
- test_tui_accessibility.py
- test_tui_trajectory_rail.py
- Bug Report Plan: Agent Writes Gibberish to Files Instead of Coding
- TDDSkill
- android_ref_adb.md
- Message
- tui_app.py
- 🦸‍♂️ Torchlight's Superpowers!
- Architecture
- ._handle_slash_command
- test_code_quality_harness.py
- prompts_minimal.py
- UI Improvements Plan — Industry-Standard Coding Agent UI
- android_ref_signing.md
- Prompt Templates for 7B Coder Models
- Torchlight Excellence Roadmap
- Checklist
- Memory System Deep Dive
- ProjectMemory
- Execution Feedback Loop
- start_optimized_local.sh
- Step
- setup_optimized.sh
- prompts/__init__.py
- run.sh
- start_mlx_server.sh
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- context-manager-cli
- torchlight-core
- ConnectionPill
- test_plan_execution_loop.py
- Context Manager CLI
- Torchlight — Terminal AI Coding Agent
- CommandPalette
- .agents/AGENTS.md
- .build
- Data Flow
- Core Classes
- autonomous_harness.py
- SymbolIndex
- dashboard.py
- test_tui_theme.py
- Resource-Adaptive Features
- HTMLParser
- rlm_engine_optimized.py
- rules/graphify.md
- workflows/graphify.md
- web_server.py
- Static
- TieredMemory
- Target Quality Tiers
- P1: Important Follow-On Work
- Compression System
- Future Improvements
- Improvement Recommendations by Resource Tier
- Torchlight Documentation
- TrajectoryLock
- test_tui_plan_panel.py
- Console
- Android Troubleshoot — Routing Layer
- Memory Tiers
- Persistence
- command_palette.py
- SelectiveCompressor
- Retrieval System
- ~350 tokens. Do NOT load other reference files in the same turn.
- Profile: Run -> Profile app -> Memory tab
- at android.app.Activity...          <- framework — ignore
- StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
- Context null in Fragment -> requireContext() (throws if detached, which is correct)
- implementation 'androidx.multidex:multidex:2.0.1'
- Never use StrictMode.allowThreadDiskReads() — it masks the bug
- cli/main.py
- AutonomousHarness
- iter_project_files
- ActionEntry
- context_manager/prompts.py
- Plan: Non-Security Improvements
- context_manager/memory/embeddings.py
- ToolCallCard
- Schema Reference
- test_tui_command_palette.py
- MyCustomSkill
- DirectiveTracker
- test_prompts_and_memory.py
- Flashlight
- ProjectMemory
- Plan: UI Improvements — Torchlight Codex IDE
- opencode.json
- classify_command
- graphify.js
- on
- HTMLGameSkill
- ExecutionFeedbackLoop
- .load
- ApprovalModal
- tool_write_file_impl
- ._build_messages
- discovery.py
- test_tools_core.py
- ._live_context_tokens
- test_tui_diff_view.py
- .compose
- TestApp
- PromptTextArea
- _HttpxLMStudioClient
- ConversationSummarizer
- App
- on
- Pressed
- Selected
- Step
- Submitted
- Container
- ._execute_tool_with_approval
- TestApp
- test_autonomous_harness_pipeline.py
- core/api/lmstudio.py
- context_manager/memory/persistence.py
- .solve_async
- TestApp
- ._parse_response
- tui_widgets/__init__.py
- tool_schemas.py
- MarkdownDocumentSkill
- ._stream_llm
- .compact_context
- .chat_stream
- Panel
- str
- FileEntry
- SymbolIndex
- MemoryObject
- Message
- MessageRole
- ComposeResult
- TokenCounter

## God Nodes (most connected - your core abstractions)
1. `TorchlightApp` - 141 edges
2. `TieredMemory` - 116 edges
3. `RLMEngineOptimized` - 66 edges
4. `AutonomousHarness` - 62 edges
5. `MemoryConfig` - 61 edges
6. `ExecutionFeedbackLoop` - 50 edges
7. `SkillResult` - 33 edges
8. `StreamingChatSession` - 32 edges
9. `tool_edit_file_impl()` - 32 edges
10. `Step` - 31 edges

## Surprising Connections (you probably didn't know these)
- `test_classify_destructive_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py
- `test_classify_empty_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py
- `test_classify_install_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py
- `test_classify_safe_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py
- `test_classify_unknown_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py

## Import Cycles
- None detected.

## Communities (217 total, 41 thin omitted)

### Community 0 - "implementations.py"
Cohesion: 0.07
Nodes (52): Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Th, test_set_ctx_window(), Unit tests for context budget overflow detection and fixes in TieredMemory, RLME, test_tool_context_window_scaling(), test_list_dir_impl(), _ddg_search(), _detect_doc_source(), _extract_identifiers() (+44 more)

### Community 1 - "datetime"
Cohesion: 0.17
Nodes (17): ContentChunk, ContentType, ContextSnapshot, MemoryNeedle, Enum, SessionState, WorkingSetSnapshot, test_content_chunk_custom() (+9 more)

### Community 2 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 3 - "SymbolIndex"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 4 - "ToolRegistry"
Cohesion: 0.07
Nodes (32): test_get_tool_registry(), test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_preview_dry_run(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command() (+24 more)

### Community 5 - "BaseSkill"
Cohesion: 0.08
Nodes (25): ABC, BaseSkill, CalculatorSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, Skills — external / plugin capabilities.  Skills are DIFFERENT from core tools: (+17 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.14
Nodes (8): _friendly_timeout_msg(), LMStudioClient, Synchronous streaming generator — yields tokens one-by-one.          Uses DEFAUL, Async streaming generator. Uses per-chunk read timeout (DEFAULT_TIMEOUT)., Simple synchronous query interface (LLMClient protocol compatibility)., Return a human-readable message explaining which part of the request timed out., Timeout, TimeoutException

### Community 7 - "TokenCounter"
Cohesion: 0.07
Nodes (32): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing. (+24 more)

### Community 8 - "CloudClient"
Cohesion: 0.17
Nodes (7): CloudClient, Sanitize message roles. Convert system role to user role for models (e.g. Gemma, Async implementation of chat protocol method required by LLMClient and DebateVer, Async streaming implementation required by LLMClient protocol., Return the ids of models the provider currently reports as available.         Us, Resolve requested self.model against live models to prevent 404 mismatches., _sanitize_messages_for_cloud()

### Community 9 - "ActionTracker"
Cohesion: 0.22
Nodes (5): ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex

### Community 10 - "test_resizer.py"
Cohesion: 0.26
Nodes (14): _build_app(), _click_resizer(), _drag_resizer(), Regression tests for the PaneResizer drag/click resizing in tui_app.py.  The Pan, No-op client so the engine never touches LM Studio / Ollama / cloud., Simulate a real drag: mouse_down -> captured MouseMove -> mouse_up., _resize_to(), _start_app() (+6 more)

### Community 11 - "test_enhanced_web_tools.py"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 12 - "test_errors.py"
Cohesion: 0.05
Nodes (57): get_recovery_hint(), inject_recovery_into_memory(), Any, Recovery engine for Torchlight errors.  Provides structured recovery strategies, Push recovery hint into memory state's tried_and_failed scratchpad list     to e, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type. (+49 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.08
Nodes (36): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_read_symbols_indented_methods_and_duplicate_names(), test_run_command_intercept_ast_functions(), test_search_ast_action_aliases(), test_search_ast_impl_fallback(), test_search_ast_schema_validation(), test_verify_compile_param(), test_edit_file_impl() (+28 more)

### Community 14 - "test_web_inspector.py"
Cohesion: 0.09
Nodes (21): EphemeralHTTPServer, Any, HTMLParser, Path, QuietHTTPRequestHandler, Web Outcome Inspector for Torchlight.  Provides low-memory, ephemeral runtime an, Spins up a lightweight local HTTP server for static file inspection., Tier 1: Static HTML syntax and asset path validator. (+13 more)

### Community 15 - "Detailed Bug Reports & Resolutions"
Cohesion: 0.11
Nodes (18): BUG-01: `_total_llm_calls` Counter Accumulation Across Sessions, BUG-02: Verification Gate Premature Answer Bypass via Rejection State, BUG-03: Autonomous Harness Daemon Infinite Loop on Exception, BUG-04: Consecutive Code Error Loop Unbounded Retries, BUG-05: Unimported `Path` Silently Disables Feedback Loop, BUG-06: Stale Verification Gate Gatekeeping on Test Failure Reset, BUG-07: Read-Only Tool Interleaving Counter Laundering, BUG-08: LLM Step Failure Overwritten by Passing Pre-Existing Tests (+10 more)

### Community 16 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 17 - "InferenceParams"
Cohesion: 0.09
Nodes (19): InferenceParams, Synthesis and refinement following critique. Deterministic., Send messages and return the full response., Sampling parameters forwarded to the LLM /chat/completions endpoint.     Only no, One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters., Reasoning through plans. Moderate creativity. Locks out WRITE_FILE to prevent ha (+11 more)

### Community 18 - "ensure_project_initialized"
Cohesion: 0.11
Nodes (24): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, Ensure target project directory exists and has a local Git repository initialize, Write a marker proving the harness itself initialized this git repo.      Only w, Ensure target project directory exists and has `.context-memory.json` persistent, Explicitly initialize a new project directory with both persistent memory files (+16 more)

### Community 19 - "repl_sandbox.py"
Cohesion: 0.16
Nodes (18): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+10 more)

### Community 20 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 21 - "🟡 Medium Difficulty"
Cohesion: 0.04
Nodes (47): 🔴 Hard Difficulty, Implementation Steps, Implementation Steps, Implementation Steps, Implementation Steps, Implementation Steps, Implementation Steps, Implementation Steps (+39 more)

### Community 22 - "test_tui_tool_cards.py"
Cohesion: 0.15
Nodes (19): anyio, Tests for Phase-2 tool call cards (risk badge, status, timing, sections)., The streamed <tool_call> mounts a pending card completed by the step., test_app_pending_card_wiring(), test_risk_for_tool(), test_summarize_args(), test_tool_card_complete_denied(), test_tool_card_complete_error_expands() (+11 more)

### Community 23 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 24 - "ContextDashboard"
Cohesion: 0.10
Nodes (7): ContextDashboard, Panel, Print sub-agent task progress to the console., Return a new ActionTracker bound to this dashboard's console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 25 - "DebateVerifier"
Cohesion: 0.10
Nodes (21): Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., CritiqueResult, DebateVerifier, DebateVerifier implementation: orchestrates adversarial critique and refinement, Synthesize refined output incorporating valid critiques using InferenceParams.fo, Full debate flow: evaluate should_debate, execute critique, and refine if flaws, Helper to extract JSON payload or XML tags from LLM response. (+13 more)

### Community 26 - "config.py"
Cohesion: 0.06
Nodes (47): test_list_available_models_includes_gemma4e4b(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), test_normalize_mlx_gemma_4_4e4b(), index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings. (+39 more)

### Community 27 - "StreamingChatSession"
Cohesion: 0.19
Nodes (5): /params                    — show current params         /params auto, Re-append closing tags and unclosed JSON braces that were consumed as stop token, Estimate tokens consumed by system prompt, tools, and flashlight beam., Run out-of-band DebateVerifier pass if candidate proposal needs verification., StreamingChatSession

### Community 28 - "Architectural Learnings & Engineering Principles"
Cohesion: 0.06
Nodes (32): 1. Context Engineering & Memory Architecture, 2. Prompt Engineering & Agent Steering, 3. Autonomous Execution & Verification, 4. Web Browsing, Anti-Blocking & Documentation Engineering, 5. Tool Call Resilience & Fault-Tolerant Parsing, 6. Adaptive Context Budgeting & Runtime Rollout, 7. GBNF Grammar Design & Constrained Decoding for SLMs, A. Context Overhead vs Available Headroom (+24 more)

### Community 29 - "LLMClient"
Cohesion: 0.13
Nodes (18): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client() (+10 more)

### Community 30 - "Changelog"
Cohesion: 0.07
Nodes (26): Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+18 more)

### Community 31 - "RLMEngineOptimized"
Cohesion: 0.12
Nodes (19): test_action_tag_braces_inside_string_values(), test_action_tag_no_json_args(), test_action_tag_unclosed_with_trailing_prose(), test_inline_interception_skips_plan_phase(), test_inline_interception_skips_plan_prose_blocks(), test_inline_interception_still_catches_real_code_and_file_header(), test_repair_stop_tokens_write_file(), test_rlm_engine_code_tag_and_backticks() (+11 more)

### Community 32 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 33 - "LlamaCppClient"
Cohesion: 0.05
Nodes (39): ConversationSummarizer, DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer (+31 more)

### Community 34 - "validate_tool_call"
Cohesion: 0.16
Nodes (17): test_get_openai_tools_schema(), test_get_schemas_for_phase(), test_validate_tool_call_alias(), test_validate_tool_call_coercion(), test_validate_tool_call_missing_required(), test_validate_tool_call_unknown_tool(), test_validate_tool_call_valid(), test_validate_tool_call_with_unwrapping_and_coercion() (+9 more)

### Community 35 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (8): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 37 - "ContextBudget"
Cohesion: 0.07
Nodes (18): _clamp(), ContextBudget, Token reserve kept for the recent-message window., Current fraction of the target window in use., Effective budget allocations for the current turn.      `used_tokens` is the liv, Token allowance for the L0 working memory scratchpad this turn., Max characters per scratchpad entry (longer when headroom is ample)., Max entries shown per state section (3 tight ... 8 rich). (+10 more)

### Community 38 - "on"
Cohesion: 0.07
Nodes (11): DirectorySelected, on, Pressed, FileActionModal, FolderPickerModal, Modal dialog for interactive visual folder selection across the entire computer., Modal dialog for selecting session execution mode (Chat vs Goal)., Modal dialog presenting OS options when a file is selected in the Explorer tree. (+3 more)

### Community 39 - "core/memory/manager.py"
Cohesion: 0.12
Nodes (15): Adaptive, headroom-driven context budget coordinator for Torchlight.  Static res, Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, Load persistent project memory (.context-memory.json) into L0 working state., Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length., _scratchpad_clean(), get_token_counter(), Token counting for Torchlight.  Uses tiktoken when available, falls back to a wo, TokenCounter (+7 more)

### Community 40 - "PaneResizer"
Cohesion: 0.16
Nodes (6): Click, MouseDown, MouseMove, MouseUp, PaneResizer, Interactive splitter bar to resize the left/right side panes.      Drag the bar

### Community 41 - "CenterEmptyState"
Cohesion: 0.18
Nodes (7): CenterEmptyState, Container, Pressed, CenterEmptyState — the welcome / idle screen shown in the editor pane.  Replaces, Switch displayed content based on connection state., Route chip buttons to app-level actions., Full-pane empty state widget for the editor / center area.      Mount this insid

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "Top 20 Tool-Calling Issues — Ranked by Value Generation for Tool Quality Improvement"
Cohesion: 0.05
Nodes (43): 🥉 #10 — Risk Tier Misclassification for Safe Commands, 🥉 #11 — Subtask Handover Context Loss Between Epochs, 🥉 #12 — Selective Compression Context Loss, #13 — Deep Trajectory Goal Drift Past Turn 8, #14 — Hallucinated Generic Tool Names, #15 — Lost-in-the-Middle Schema Confusion, #16 — Blind Retry Without Log Inspection, #17 — Forbidden Directory Drift (`cd` in Shell) (+35 more)

### Community 44 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 45 - "test_phase_detection.py"
Cohesion: 0.21
Nodes (13): _make_session(), Create a StreamingChatSession with mocked heavy dependencies., Troubleshoot wins over code when both signals are present., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., test_detect_chat_phase(), test_detect_code_phase(), test_detect_phase_empty_input() (+5 more)

### Community 46 - "test_tui_transcript_widgets.py"
Cohesion: 0.06
Nodes (33): Container, anyio, Tests for Phase-1 transcript widgets (message cards, streaming, thinking)., Smoke test: the real app mounts MessageCards and drives the streaming view., test_app_transcript_wiring(), test_card_meta_for(), test_estimate_token_count(), test_message_card_composes() (+25 more)

### Community 47 - "test_tui_file_tree.py"
Cohesion: 0.08
Nodes (29): _FakeProc, anyio, Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)., test_git_tree_decorates_file_labels(), test_normalize_status_code(), test_parse_git_status_porcelain_basic(), test_parse_git_status_porcelain_quoted_path(), test_parse_git_status_porcelain_rename_takes_destination() (+21 more)

### Community 48 - "VerbatimCompactor"
Cohesion: 0.14
Nodes (6): CompressionConfig, Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 49 - "core/memory/models.py"
Cohesion: 0.13
Nodes (29): Re-export TieredMemory and MemoryConfig from shared core library core.memory.man, Conversation Summarizer for Torchlight.  Extracts key information from conversat, ContentChunk, ContentType, ContextSnapshot, ExecutionMode, MemoryNeedle, MemoryObject (+21 more)

### Community 50 - "MessageRole"
Cohesion: 0.14
Nodes (12): _build_excerpt(), LLMStateExtractor, _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa (+4 more)

### Community 51 - "test_tui_status_bar.py"
Cohesion: 0.11
Nodes (22): anyio, Tests for Phase-4 consolidated status bar (gauge + segments widget)., test_build_status_segments_defaults(), test_build_status_segments_populated(), test_build_status_segments_running_no_tps_yet(), test_build_status_segments_server_offline_and_branch_escape(), test_gauge_markup_clamps_out_of_range(), test_gauge_markup_color_escalation() (+14 more)

### Community 52 - "SkillResult"
Cohesion: 0.16
Nodes (9): Any, ReproSkill, Any, Registry for external skills.      Does NOT contain core tools (READ_FILE, WRITE, Synchronous wrapper for use from non-async contexts., Trigger real load on first call, then delegate., SkillRegistry, SkillResult (+1 more)

### Community 53 - "Message"
Cohesion: 0.20
Nodes (7): MemoryObject, Message, SessionState, SessionPersistence, test_memory_object_defaults(), test_memory_object_full(), test_message_defaults()

### Community 54 - "main_optimized.py"
Cohesion: 0.29
Nodes (11): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Step (+3 more)

### Community 55 - "TorchlightApp"
Cohesion: 0.05
Nodes (16): App, ContextFileAttached, FileSelected, NodeSelected, Codex / Tiny-Brain 2 Style Agent IDE TUI., Extract text from the TextArea, clear it, and dispatch., Programmatic send — called by ctrl+enter binding., Append a line to the Output tab's RichLog.          severity: 'info' | 'tool' | (+8 more)

### Community 56 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 57 - "tool_edit_file_impl"
Cohesion: 0.12
Nodes (27): test_edit_file_blocks_broken_syntax(), test_tool_edit_file_integration(), Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_auto_fallback_to_write(), test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_line_bounded(), test_edit_file_line_bounded_without_old_text() (+19 more)

### Community 58 - "ProjectGraph"
Cohesion: 0.19
Nodes (16): get_project_graph(), ProjectGraph, Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Get or create the ProjectGraph instance for a given root directory., Incrementally update the AST graph for a single modified file., update_project_graph_file(), Unit tests for incremental O(1) AST graph delta updates. (+8 more)

### Community 59 - "test_enhanced_memory_retrieval.py"
Cohesion: 0.09
Nodes (30): build_embedder(), compute_tf_idf_score(), cosine_similarity(), Embedder, HybridEmbedder, HybridMemoryRetriever, _is_low_memory(), KeywordEmbedder (+22 more)

### Community 60 - "test_tui_accessibility.py"
Cohesion: 0.10
Nodes (28): _make_app(), anyio, Tests for Phase-6 accessibility and keyboard navigation.  Covers: - Tab bar keyb, Arrow navigation wraps around at the ends., Arrow keys don't do anything when no tabs are open., Verify :focus rules exist for tab items in the .tcss file., Verify responsive @media-equivalent class rules exist., Verify no #hex color values appear in the .tcss file. (+20 more)

### Community 61 - "test_tui_trajectory_rail.py"
Cohesion: 0.09
Nodes (16): anyio, Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)., The streamed <tool_call> adds a dot; the completing step flips it., test_app_pending_step_updates_rail(), test_rail_add_pending_and_complete_ok(), test_rail_clear_removes_dots(), test_rail_complete_error_and_denied(), test_rail_complete_without_pending_is_noop() (+8 more)

### Community 62 - "Bug Report Plan: Agent Writes Gibberish to Files Instead of Coding"
Cohesion: 0.20
Nodes (9): 1. Summary, 2. Reproduction Steps, 3. Hypothesis Areas (Root Cause Candidates), 4. Investigation Tasks, 5. Confirmed Root Cause, 6. Applied Fixes, 7. Acceptance Criteria, 8. Follow-up (+1 more)

### Community 63 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 64 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 65 - "Message"
Cohesion: 0.15
Nodes (8): Persist L0 working state to disk in .context-memory.json (debounced)., Remove all pinned files., Generic add_message method for role-based message addition., Compress older messages, preserving the first N messages., Async wrapper for compress_recent., Compact context between tasks while preserving continuous session state., Message, MessageRole

### Community 66 - "tui_app.py"
Cohesion: 0.11
Nodes (12): copy_to_clipboard(), CopySelectionModal, create_client(), load_last_state(), main(), ModelPickerModal, Torchlight Agent — Codex / Tiny-Brain 2 Style IDE TUI (Textual) Full-featured ID, Copy text to system clipboard across macOS, Linux, and Windows. (+4 more)

### Community 67 - "🦸‍♂️ Torchlight's Superpowers!"
Cohesion: 0.18
Nodes (10): 📊 Summary Table of Superpowers, 🗺️ Superpower 1: The Magic Code Map (Native AST Graph Engine), 🔫 Superpower 2: The Shrink Ray (8GB Memory Tricks), 🧠 Superpower 3: Tiny, Ultra-Smart Brains (Small Models), 🎭 Superpower 4: Changing Moods (Phase-Based Inference), 🔄 Superpower 5: The "Try Again" Loop (RLM), 🕵️‍♂️ Superpower 6: The Invisible Devil's Advocate (Out-of-Band Self-Critique), 🏃‍♂️ Superpower 7: The 24-Hour Non-Stop Marathon Engine (Autonomous Harness) (+2 more)

### Community 68 - "Architecture"
Cohesion: 0.15
Nodes (12): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Rules, Commands, Context Budget Breakdown, Development (+4 more)

### Community 69 - "._handle_slash_command"
Cohesion: 0.09
Nodes (10): Panel, _provider_runtime_info(), Return (port, externally_managed) for a given provider key.      externally_mana, Sync all connection-dependent UI elements.          Called on server status chan, Build the AST knowledge graph silently in background thread., Consolidated Phase-4 status bar (state · model · context gauge · tps · tokens ·, Repoint the file tree at the engine root and refresh git status., Manually trigger memory context compaction. (+2 more)

### Community 70 - "test_code_quality_harness.py"
Cohesion: 0.09
Nodes (38): Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_compile_gate_rejects_return_outside_function(), test_detect_stubs(), test_detect_symptom_patching() (+30 more)

### Community 71 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 72 - "UI Improvements Plan — Industry-Standard Coding Agent UI"
Cohesion: 0.10
Nodes (19): 1. Current State Audit, 2. Industry Benchmark, 3. Design Principles (non-negotiable), 4. Target Architecture (widget extraction), 5. Phased Roadmap, 6. Verification Strategy, 7. Non-Goals, 8. Effort & Sequencing (+11 more)

### Community 73 - "android_ref_signing.md"
Cohesion: 0.12
Nodes (16): ~200 tokens. Do NOT load other reference files in the same turn., Android Signing Reference — Keystore, Certificates, Google Play, app/build.gradle:, Common errors, Enroll: Play Console -> App -> Setup -> App signing, Generate a new debug keystore (if lost), Google manages the release key; you upload with a separate upload key, Google Play App Signing (recommended) (+8 more)

### Community 74 - "Prompt Templates for 7B Coder Models"
Cohesion: 0.13
Nodes (14): Breaking Complex Tasks into Chained Prompts, General Rules for 7B Models, Key Characteristics of 7B Models, Prompt Pattern: Chained Development, Prompt Templates for 7B Coder Models, Structure, Structure, Structure (+6 more)

### Community 75 - "Torchlight Excellence Roadmap"
Cohesion: 0.13
Nodes (15): 1. Execution Policy Router, 1. Smarter Retrieval, 2. Adaptive Prompt Compression, 2. Explicit Working-Set Builder, 3. Stronger Action Extraction, 4. Provider and Model Truth Model, 4. Terminal UX Polish, 5. Failure-Classified Retries (+7 more)

### Community 76 - "Checklist"
Cohesion: 0.15
Nodes (13): 1. Slash Command Verification, 2. Runtime Hardening, 3. Process Hygiene, 4. Provider and Model Verification, 5. Local-Model Efficiency, 6. Context-Rot and Memory Durability, 7. Retry And Cancel Semantics, Already Completed (+5 more)

### Community 77 - "Memory System Deep Dive"
Cohesion: 0.15
Nodes (12): Allocation for 4k Context, Architecture Overview, Auto-tuned Budgets by Context Size, Auto-tuning, CLI Integration, Configuration Commands, Configuration Commands, File Locations (+4 more)

### Community 78 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 79 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

### Community 81 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

### Community 82 - "Step"
Cohesion: 0.12
Nodes (18): A successful WRITE_FILE step mounts a DiffView card with real content., test_app_write_step_renders_diff_card(), anyio, Tests for Phase-5 tabbed editor split pane (open_file_tab, dirty marker, keyboar, test_close_file_tab_removes_from_open_tabs(), test_close_file_tab_switches_active_tab(), test_dirty_marker_not_set_for_non_tab_file(), test_dirty_marker_set_on_write_step() (+10 more)

### Community 83 - "setup_optimized.sh"
Cohesion: 0.60
Nodes (3): info(), ok(), setup_optimized.sh script

### Community 84 - "prompts/__init__.py"
Cohesion: 0.43
Nodes (5): build_tool_syntax_prompt(), get_tool_syntax_for_context_size(), Tool syntax instructions for Torchlight.  Generates the appropriate tool calling, Build the complete tool syntax prompt for the system message.      Args:, Return the tool calling syntax instructions appropriate for the model's context

### Community 85 - "run.sh"
Cohesion: 0.40
Nodes (4): COLORTERM, PYTHONPATH, run.sh script, TERM

### Community 87 - "tui.sh"
Cohesion: 0.40
Nodes (5): cleanup(), COLORTERM, PYTHONPATH, tui.sh script, TERM

### Community 104 - "ConnectionPill"
Cohesion: 0.18
Nodes (7): ConnectionPill, ComposeResult, Horizontal, Pressed, ConnectionPill — compact header widget showing live model/server status.  Replac, Compact connection status pill for the top HUD header.      Usage in compose()::, Update the pill's connected state and model name.

### Community 105 - "test_plan_execution_loop.py"
Cohesion: 0.25
Nodes (9): anyio, test_format_l0_scratchpad_includes_pending_tasks(), test_get_workspace_pending_tasks_goal_spec(), test_get_workspace_pending_tasks_md(), test_verification_gate_allows_final_answer_when_all_done(), test_verification_gate_rejects_premature_final_answer(), get_workspace_pending_tasks(), Unified Task Helper Module for Torchlight.  Extracts pending tasks from implemen (+1 more)

### Community 106 - "Context Manager CLI"
Cohesion: 0.20
Nodes (9): Architecture, CLI Options, Commands (in CLI), Context Manager CLI, Features, How It Works, Installation, Requirements (+1 more)

### Community 107 - "Torchlight — Terminal AI Coding Agent"
Cohesion: 0.18
Nodes (11): Architecture, CLI Commands, Core Flow, Development, Error Handling, Key Features, Memory Files, Module Structure (+3 more)

### Community 108 - "CommandPalette"
Cohesion: 0.14
Nodes (5): Changed, AttachContextModal, CommandPalette, Ctrl+P modal: fuzzy-search actions, slash commands, and files., Ctrl+O modal: fuzzy-search files to attach to the prompt.

### Community 110 - ".build"
Cohesion: 0.21
Nodes (6): Any, Path, Scan project files and construct the AST graph., Perform an incremental O(1) AST update for a single modified file., Remove all nodes and edges referencing a deleted file., Save graph data to JSON and markdown report.

### Community 111 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 112 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 113 - "autonomous_harness.py"
Cohesion: 0.09
Nodes (16): GoalSpec, Enum, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, Ensure a goal spec exists on disk in .torchlight, initializing a default workspa, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks., Construct inter-task memory prompt summarizing prior verified tasks and dependen, Run a single micro-epoch for a target task. (+8 more)

### Community 114 - "SymbolIndex"
Cohesion: 0.16
Nodes (8): Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build(), test_symbol_index_summary()

### Community 115 - "dashboard.py"
Cohesion: 0.33
Nodes (3): _ActionContext, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 116 - "test_tui_theme.py"
Cohesion: 0.18
Nodes (15): _make_app(), anyio, Tests for Phase-6 theme consistency and responsive layout classes.  Covers: - CS, Ensure CSS doesn't contain hardcoded hex colors., Ensure CSS uses theme variables like $background., Ensure CSS has rules for responsive terminal classes., Responsive classes are applied when terminal is narrow., Short-terminal class applied when height < 24. (+7 more)

### Community 117 - "Resource-Adaptive Features"
Cohesion: 0.29
Nodes (7): Compression Cooldown, Embedding Cache, LLM State Extraction, Resource-Adaptive Configuration, Resource-Adaptive Features, Resource Tiers, Tool Result Budget

### Community 119 - "rlm_engine_optimized.py"
Cohesion: 0.16
Nodes (23): Unit tests for core/tools/parser.py tolerant tool parser & fuzzy repair engine., test_extract_balanced_json_object(), test_parse_tool_call_payload(), test_repair_unclosed_tool_call_tag(), test_strip_interleaved_prose(), test_tolerant_json_repair(), test_unwrap_double_encoded_json(), clean_and_parse_json() (+15 more)

### Community 123 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 124 - "Static"
Cohesion: 0.14
Nodes (6): ComposeResult, AgentMemoryWidget, AgentStatusModal, Displays the live L0 Agent Brain Scratchpad., Modal dialog for complete visibility into background agent actions & status tele, Static

### Community 125 - "TieredMemory"
Cohesion: 0.08
Nodes (33): ContextSnapshot, MemoryConfig, Tiered memory system with L0-L3 hierarchy:     - L0: Active prompt (current cont, Return list of (path, content) for pinned files., Calculate remaining token budget headroom before reaching max_tokens threshold., Predict likely next tools based on current state., TieredMemory, test_tiered_memory_total_tokens_includes_pinned_files() (+25 more)

### Community 126 - "Target Quality Tiers"
Cohesion: 0.50
Nodes (4): Target Quality Tiers, Tier A: Constrained local mode, Tier B: Balanced local mode, Tier C: Strong local mode

### Community 127 - "P1: Important Follow-On Work"
Cohesion: 0.40
Nodes (5): 1. Runtime Presets for Small Models, 2. Richer Memory Inspection, 3. Better Verification Loops, 4. Better Activity Semantics, P1: Important Follow-On Work

### Community 128 - "Compression System"
Cohesion: 0.40
Nodes (5): Compression Flow, Compression System, LLM State Extractor, Summary Merge Logic, Trigger Conditions

### Community 129 - "Future Improvements"
Cohesion: 0.40
Nodes (5): Future Improvements, Phase 1: Quick Wins (Done ✓), Phase 2: Medium Effort, Phase 3: Advanced (Requires Resources), Phase 4: Claude-Level (Heavy Resources Only)

### Community 130 - "Improvement Recommendations by Resource Tier"
Cohesion: 0.40
Nodes (5): Generous (16-32GB RAM, 8k-16k context), Heavy (32GB+ RAM, 16k+ context), Improvement Recommendations by Resource Tier, Minimal (8GB RAM, 4k context), Standard (8-16GB RAM, 4k-8k context)

### Community 131 - "Torchlight Documentation"
Cohesion: 0.40
Nodes (5): Coverage, How To Use These Docs, Recent Runtime Progress, Recommended Reading Order For A New Contributor, Torchlight Documentation

### Community 132 - "TrajectoryLock"
Cohesion: 0.16
Nodes (15): Unit tests for core/tools/dedup.py argument normalization & TrajectoryLock., test_compute_payload_hash(), test_normalize_tool_args(), test_trajectory_lock(), compute_payload_hash(), normalize_tool_args(), Any, Anti-Looping Trajectory Lock and Tool Payload Signature Deduplication.  Provides (+7 more)

### Community 133 - "test_tui_plan_panel.py"
Cohesion: 0.11
Nodes (23): _build_plan_text(), _make_app(), anyio, Delegate to the real TUI plan-builder helper., Repeated checklist entries (summary + detailed sections) must not duplicate., test_build_plan_text_all_done(), test_build_plan_text_dedupes_duplicate_checkbox_lines(), test_build_plan_text_goal_spec_json() (+15 more)

### Community 134 - "Console"
Cohesion: 0.24
Nodes (7): Console, test_render_task_progress_empty(), test_render_task_progress_with_tasks(), test_action_entry_markup_safety(), test_action_tracker_print_action_safety(), test_escape_raw_brackets_and_json(), test_tui_markup_escaping_safety()

### Community 135 - "Android Troubleshoot — Routing Layer"
Cohesion: 0.50
Nodes (3): Android Troubleshoot — Routing Layer, Step 1 — Call the tool, Step 2 — Read ONE reference file only if deeper guidance is needed

### Community 136 - "Memory Tiers"
Cohesion: 0.50
Nodes (4): Disk Tiers (ProjectMemory), In-Memory Tiers (TieredMemory.messages), Memory Tiers, Session State Tiers

### Community 137 - "Persistence"
Cohesion: 0.50
Nodes (4): Loading Session State, Persistence, Project Memory Persistence, Session Persistence

### Community 138 - "command_palette.py"
Cohesion: 0.18
Nodes (9): test_fuzzy_filter_empty_query_and_no_match(), test_fuzzy_filter_prefix_beats_substring(), NamedTuple, fuzzy_filter(), _fuzzy_score(), PaletteResult, Command palette + slash-command autocomplete for the Torchlight TUI.  Phase 4: *, Rank ``query`` against ``label``; 0 means no match.      Prefix matches beat sub (+1 more)

### Community 139 - "SelectiveCompressor"
Cohesion: 0.16
Nodes (11): CompressionConfig, CompressionLevel, Enum, Pattern, Selective Memory Compression — Progressive context reduction for local LLMs.  4-, Progressive compression that preserves semantic meaning.      Strategy:     - Re, Compress a list of messages using progressive levels., SelectiveCompressor (+3 more)

### Community 140 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 148 - "cli/main.py"
Cohesion: 0.15
Nodes (15): command, _beam_budget(), chat(), compress_file(), count_tokens(), goal(), Start an interactive chat session with context management and flashlight., Start an autonomous goal execution session driven by .torchlight task tracking. (+7 more)

### Community 149 - "AutonomousHarness"
Cohesion: 0.19
Nodes (20): AutonomousHarness, HarnessConfig, Path, Ensure target project has local git repository and persistent memory initialized, Autonomous Harness Engine driving long-running continuous execution., main(), CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., create_mock_feedback_loop() (+12 more)

### Community 150 - "iter_project_files"
Cohesion: 0.27
Nodes (9): Binding, test_build_palette_items_kinds_and_visibility(), test_iter_project_files_caps(), test_iter_project_files_skips_dot_and_vendor_dirs(), build_palette_items(), iter_project_files(), Path, Build ``(label, detail, kind, value)`` entries for the palette. (+1 more)

### Community 151 - "ActionEntry"
Cohesion: 0.29
Nodes (3): ActionEntry, A single recorded action with its status and elapsed time., Text

### Community 152 - "context_manager/prompts.py"
Cohesion: 0.29
Nodes (4): verify_cli_prompt(), build_default_system_prompt(), Torchlight prompt stack — single source of truth.  V2: Optimized for local LLMs, Build system prompt. Use V2 for small contexts.

### Community 153 - "Plan: Non-Security Improvements"
Cohesion: 0.17
Nodes (11): Decisions, Out of Scope, Plan: Non-Security Improvements, Task 1: Frontend Consolidation, Task 2: Split `implementations.py` into Sub-Modules, Task 3: Cache `SymbolIndex` Across Micro-Epochs, Task 4: Extract Tool Execution Pipeline, Task 5: Fix Error Handling Gaps (+3 more)

### Community 154 - "context_manager/memory/embeddings.py"
Cohesion: 0.21
Nodes (9): build_embedder(), Embedder, FallbackEmbedder, HashEmbedder, _normalize(), ProviderEmbedder, any, Protocol (+1 more)

### Community 155 - "ToolCallCard"
Cohesion: 0.19
Nodes (6): ComposeResult, Container, A status-aware tool call card.      Header shows the risk-tier icon, tool name,, Refresh the elapsed counter while the tool is still running., Flip the card from running to done and fill params + output.          Re-derives, ToolCallCard

### Community 156 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

### Community 157 - "test_tui_command_palette.py"
Cohesion: 0.18
Nodes (14): anyio, Tests for Phase-4 command palette + prompt autocomplete., test_command_palette_composes_filters_and_selects(), test_command_palette_enter_runs_highlighted_item(), test_match_prompt_suggestions_file_at(), test_match_prompt_suggestions_slash(), test_prompt_text_area_enter_submits_and_accepts_suggestion(), test_prompt_text_area_file_suggestions_and_dismiss() (+6 more)

### Community 158 - "MyCustomSkill"
Cohesion: 0.33
Nodes (3): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi

### Community 159 - "DirectiveTracker"
Cohesion: 0.16
Nodes (9): DirectiveTracker, Any, Directive tracker and constraint violation reinforcement module for Torchlight., Record a directive violation (e.g. 'cd_command', 'test_assertion_delete'), Reset violation counts., Tracks model constraint violations during execution turns and dynamically     in, Unit tests for CRITICAL_DIRECTIVES system prompt lock and DirectiveTracker., test_critical_directives_in_system_prompt() (+1 more)

### Community 160 - "test_prompts_and_memory.py"
Cohesion: 0.18
Nodes (10): get_phase_system_prompt(), Unified system prompts for Torchlight.  Single source of truth for all frontends, Generate phase-tailored system prompt by appending phase instructions, critical, Unit tests for phase-tailored system prompts, anti-symptom-patching rules, and L, test_headroom_calculation(), test_l0_scratchpad_formatting(), test_persistent_memory_loading_and_prompt_inclusion(), test_phase_system_prompt_generation() (+2 more)

### Community 161 - "Flashlight"
Cohesion: 0.26
Nodes (3): _beam_config_for_context(), BeamResult, Flashlight

### Community 162 - "ProjectMemory"
Cohesion: 0.32
Nodes (3): ProjectMemory, MemoryObject, SessionState

### Community 163 - "Plan: UI Improvements — Torchlight Codex IDE"
Cohesion: 0.18
Nodes (10): Decisions, Effort & Sequencing, Non-Goals, Plan: UI Improvements — Torchlight Codex IDE, Task 1: Fix Latent Bugs (prerequisite), Task 2: Phase 5 — Tabbed Editor Split Pane, Task 3: Phase 6a — Accessibility & Focus Management, Task 4: Phase 6b — Performance & Streaming Polish (+2 more)

### Community 164 - "opencode.json"
Cohesion: 0.50
Nodes (3): plugin, $schema, .opencode/plugins/graphify.js

### Community 165 - "classify_command"
Cohesion: 0.26
Nodes (11): test_classify_confirm_commands(), test_classify_destructive_commands(), test_classify_empty_command(), test_classify_safe_commands(), test_classify_unknown_defaults_to_confirm(), test_classify_whitespace_handling(), classify_command(), classify_tool() (+3 more)

### Community 167 - "on"
Cohesion: 0.29
Nodes (4): Highlighted, on, Selected, Submitted

### Community 168 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

### Community 169 - "ExecutionFeedbackLoop"
Cohesion: 0.05
Nodes (44): Re-export ExecutionFeedbackLoop and TestRunResult from shared core library core., Execution feedback loop for Torchlight., ExecutionFeedbackLoop, extract_surgical_traceback(), Enum, Path, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Auto-run tests and web outcome inspection after code changes and inject feedback (+36 more)

### Community 170 - ".load"
Cohesion: 0.18
Nodes (6): Load graph from JSON file if available., Search nodes matching search_term. Returns code snippets alongside names., Read a short code snippet from disk for a matched node., Find relationship path between source and target symbols., Extract connected subgraph centered at symbol or file path., Return structured summary of files, classes, and function signatures.

### Community 171 - "ApprovalModal"
Cohesion: 0.17
Nodes (3): ApprovalModal, Production-grade modal dialog for tool & file modification approval., Snapshot file contents *before* a diffable write executes.          ``_handle_st

### Community 172 - "tool_write_file_impl"
Cohesion: 0.15
Nodes (13): test_tool_write_file_integration(), test_write_file_blocks_broken_syntax_and_truncation(), test_write_file_content_hash_dedup(), test_write_file_impl(), test_write_file_impl_missing_path(), Tests for performance and accuracy optimizations in Torchlight., test_batch_tool_execution(), test_inline_syntax_guardrail() (+5 more)

### Community 173 - "._build_messages"
Cohesion: 0.22
Nodes (5): get_phase_system_prompt(), Infer the current agent phase from user input and the last model response., Infer the current agent phase from user input and the last model response., Auto-switch _params based on detected phase.  No-op when locked., Build the final message list for the LLM, respecting the context budget.

### Community 174 - "discovery.py"
Cohesion: 0.18
Nodes (14): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+6 more)

### Community 175 - "test_tools_core.py"
Cohesion: 0.13
Nodes (17): CoreToolRegistry, get_core_registry(), Any, Compatibility subclass of ToolRegistry providing CLI-specific execute/dangerous_, test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command() (+9 more)

### Community 177 - "test_tui_diff_view.py"
Cohesion: 0.09
Nodes (33): anyio, Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)., A pre-write snapshot (from approval) wins over the already-written disk state., The engine's own CODE_FILE_WRITE approval path is diffable too., The approval modal shows a DIFF PREVIEW section when entries exist., test_approval_modal_omits_diff_when_empty(), test_approval_modal_renders_diff(), test_build_diff_preview_code_file_write() (+25 more)

### Community 178 - ".compose"
Cohesion: 0.40
Nodes (3): ComposeResult, ComposeResult, Vertical

### Community 179 - "TestApp"
Cohesion: 0.22
Nodes (5): App, ComposeResult, on, Pressed, TestApp

### Community 180 - "PromptTextArea"
Cohesion: 0.15
Nodes (8): ContextFileAttached, PromptTextArea, Message, TextArea whose Enter submits instead of inserting a newline.      Hooks ``update, Posted when the user presses Enter with no active suggestion., Posted when the user accepts an @file suggestion., SubmitRequested, TextArea

### Community 182 - "ConversationSummarizer"
Cohesion: 0.29
Nodes (6): ConversationSummarizer, Message, Summarize conversation turns for compression., Create a simple summary of messages., Extract key information from text., _role_label()

### Community 190 - "._execute_tool_with_approval"
Cohesion: 0.29
Nodes (3): ActionTracker, Lock phase based on concrete execution events., _tool_kind()

### Community 191 - "TestApp"
Cohesion: 0.33
Nodes (3): App, ComposeResult, TestApp

### Community 192 - "test_autonomous_harness_pipeline.py"
Cohesion: 0.52
Nodes (6): create_mock_feedback_loop(), Path, Unit tests for Inter-Task Context Pipeline, Dependencies, and File Collision Gua, test_inter_task_output_summary_injection(), test_target_file_collision_detection(), test_task_dependencies_and_execution_ordering()

### Community 193 - "core/api/lmstudio.py"
Cohesion: 0.40
Nodes (4): Re-export LMStudioClient from shared core library core.api.lmstudio., get_phase_inference_params(), LM Studio REST client.  Recovered from the original CLI implementation (commit f, Return the inference parameters preset for a named phase.

### Community 194 - "context_manager/memory/persistence.py"
Cohesion: 0.67
Nodes (4): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path

### Community 195 - ".solve_async"
Cohesion: 0.40
Nodes (3): Return True if the most recent test run actually ran and has failing or, Build an explicit warning attached to an accepted final answer when the, SolveResult

### Community 197 - "._parse_response"
Cohesion: 0.33
Nodes (5): _looks_like_prose_or_outline(), Parse the LLM response for action tags.         Returns: (action, thinking, cont, Trim prose a model appended after the file body when </WRITE_FILE> was     consu, Heuristic gate for inline code interception (step 6b of _parse_response).      R, _trim_trailing_prose()

### Community 199 - "tool_schemas.py"
Cohesion: 0.33
Nodes (5): get_openai_tools_schema(), Schema definitions and validation for SLM tool calls. Ensures Small Language Mod, Generate OpenAI-style tools list for function calling / structured schema enforc, Validate tool call against schema and normalize parameter aliases.      Returns:, validate_and_normalize_tool_call()

## Knowledge Gaps
- **444 isolated node(s):** `📊 Summary Table`, `Implementation Steps`, `Implementation Steps`, `Implementation Steps`, `Implementation Steps` (+439 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **41 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AutonomousHarness` connect `AutonomousHarness` to `test_autonomous_harness_pipeline.py`, `tui_app.py`, `test_tui_plan_panel.py`, `on`, `._handle_slash_command`, `PaneResizer`, `ExecutionFeedbackLoop`, `ApprovalModal`, `autonomous_harness.py`, `SymbolIndex`, `cli/main.py`, `TorchlightApp`, `StreamingChatSession`, `Static`, `TieredMemory`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `TorchlightApp` connect `TorchlightApp` to `tui_app.py`, `test_tui_plan_panel.py`, `on`, `._handle_slash_command`, `PaneResizer`, `test_resizer.py`, `ApprovalModal`, `test_tui_transcript_widgets.py`, `._live_context_tokens`, `test_tui_diff_view.py`, `Step`, `Static`, `test_tui_theme.py`, `AutonomousHarness`, `test_tui_tool_cards.py`, `test_tui_accessibility.py`, `test_tui_trajectory_rail.py`, `RLMEngineOptimized`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `TieredMemory` connect `TieredMemory` to `implementations.py`, `SelectiveCompressor`, `cli/main.py`, `AutonomousHarness`, `StreamingChatSession`, `RLMEngineOptimized`, `test_prompts_and_memory.py`, `LlamaCppClient`, `ContextBudget`, `core/memory/manager.py`, `ExecutionFeedbackLoop`, `core/memory/models.py`, `tool_edit_file_impl`, `test_enhanced_memory_retrieval.py`, `test_autonomous_harness_pipeline.py`, `Message`, `.solve_async`, `.compact_context`, `Step`, `test_plan_execution_loop.py`, `autonomous_harness.py`, `rlm_engine_optimized.py`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TorchlightApp` (e.g. with `_StubClient` and `AutonomousHarness`) actually correct?**
  _`TorchlightApp` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `TieredMemory` (e.g. with `StreamingChatSession` and `AutonomousHarness`) actually correct?**
  _`TieredMemory` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `RLMEngineOptimized` (e.g. with `DebateVerifier` and `ExecutionFeedbackLoop`) actually correct?**
  _`RLMEngineOptimized` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `AutonomousHarness` (e.g. with `StreamingChatSession` and `ExecutionFeedbackLoop`) actually correct?**
  _`AutonomousHarness` has 16 INFERRED edges - model-reasoned connections that need verification._