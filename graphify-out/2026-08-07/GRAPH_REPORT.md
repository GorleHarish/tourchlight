# Graph Report - tourchlight v1_i6  (2026-08-07)

## Corpus Check
- 222 files · ~154,451 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3194 nodes · 6391 edges · 187 communities (162 shown, 25 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 583 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5d1f624b`
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
- repl_sandbox.py
- ActionTracker
- test_resizer.py
- test_enhanced_web_tools.py
- RecoveryEngine
- test_implementations.py
- WebOutcomeInspector
- test_context_budget_overflow.py
- TrajectoryLogger
- InferenceParams
- core/memory/persistence.py
- LlamaCppClient
- android_ref_build.md
- CloudClient
- .open_file_tab
- PlanningSkill
- ContextDashboard
- DebateVerifier
- verify_m1_setup.py
- StreamingChatSession
- test_tui_file_tree.py
- LLMClient
- Changelog
- RLMEngineOptimized
- PyASTVisitor
- context_manager/compression/summarizer.py
- get_tool_registry
- android_ref_runtime.md
- VerbatimCompactor
- ContextBudget
- on
- core/memory/models.py
- ._apply_pane_widths
- rlm_engine_optimized.py
- TDDSkill
- Issues Found
- android_ref_emulator.md
- MemoryNeedle
- CopySelectionModal
- GitFileTree
- VerbatimCompactor
- core/memory/manager.py
- context_manager/memory/models.py
- test_tui_status_bar.py
- SkillResult
- SessionPersistence
- main_optimized.py
- AgentMemoryWidget
- Torchlight Architecture
- tool_edit_file_impl
- ProjectGraph
- MemoryObject
- test_tui_accessibility.py
- PaneResizer
- CommandPalette
- TDDSkill
- android_ref_adb.md
- test_phase_detection.py
- tui_app.py
- ProjectMemory
- Architecture
- .update_sidebar_meta
- test_code_quality_harness.py
- prompts_minimal.py
- ._handle_slash_command
- android_ref_signing.md
- Prompt Templates for 7B Coder Models
- Torchlight Excellence Roadmap
- Checklist
- Memory System Deep Dive
- ProjectMemory
- Execution Feedback Loop
- start_optimized_local.sh
- TorchlightApp
- setup_optimized.sh
- prompts/__init__.py
- run.sh
- start_mlx_server.sh
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- test_inline_interception.py
- context-manager-cli
- torchlight-core
- FolderPickerModal
- get_workspace_pending_tasks
- Context Manager CLI
- Torchlight — Terminal AI Coding Agent
- ConversationSummarizer
- .agents/AGENTS.md
- .build
- Data Flow
- Core Classes
- test_tui_trajectory_rail.py
- SymbolIndex
- _HttpxLMStudioClient
- test_tui_theme.py
- Resource-Adaptive Features
- IndexVisitor
- test_tool_parser.py
- rules/graphify.md
- workflows/graphify.md
- web_server.py
- dashboard.py
- TieredMemory
- Target Quality Tiers
- P1: Important Follow-On Work
- Compression System
- Future Improvements
- Improvement Recommendations by Resource Tier
- Torchlight Documentation
- test_dedup.py
- test_tui_plan_panel.py
- Console
- Android Troubleshoot — Routing Layer
- Memory Tiers
- Persistence
- ._safe_mount
- format.py
- Retrieval System
- ~350 tokens. Do NOT load other reference files in the same turn.
- Profile: Run -> Profile app -> Memory tab
- at android.app.Activity...          <- framework — ignore
- StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
- Context null in Fragment -> requireContext() (throws if detached, which is correct)
- implementation 'androidx.multidex:multidex:2.0.1'
- Never use StrictMode.allowThreadDiskReads() — it masks the bug
- LLMStateExtractor
- AutonomousHarness
- context_manager/memory/persistence.py
- ActionEntry
- context_manager/prompts.py
- Plan: Non-Security Improvements
- context_manager/memory/embeddings.py
- ToolCallCard
- Schema Reference
- PromptTextArea
- MyCustomSkill
- get_phase_system_prompt
- cli/main.py
- Flashlight
- .compact_context
- Plan: UI Improvements — Torchlight Codex IDE
- opencode.json
- MarkdownDocumentSkill
- graphify.js
- .for_critic
- HTMLGameSkill
- ExecutionFeedbackLoop
- .query
- SessionPersistence
- .memory
- discovery.py
- classify_command
- test_tui_diff_view.py
- TestApp
- ._submit_user_input
- Message
- TestApp
- core/api/lmstudio.py
- TestApp
- tui_widgets/__init__.py

## God Nodes (most connected - your core abstractions)
1. `TorchlightApp` - 159 edges
2. `TieredMemory` - 128 edges
3. `RLMEngineOptimized` - 85 edges
4. `MemoryConfig` - 72 edges
5. `AutonomousHarness` - 62 edges
6. `ExecutionFeedbackLoop` - 52 edges
7. `LlamaCppClient` - 44 edges
8. `StreamingChatSession` - 41 edges
9. `Step` - 37 edges
10. `FolderPickerModal` - 36 edges

## Surprising Connections (you probably didn't know these)
- `test_action_entry_markup_safety()` --calls--> `ActionEntry`  [EXTRACTED]
  core/tests/test_markup_escaping.py → context-manager-cli/src/context_manager/cli/dashboard.py
- `StreamingChatSession` --uses--> `LMStudioClient`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/api/lmstudio.py
- `StreamingChatSession` --uses--> `DebateVerifier`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/debate/verifier.py
- `StreamingChatSession` --uses--> `AutonomousHarness`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/execution/autonomous_harness.py
- `StreamingChatSession` --uses--> `ExecutionFeedbackLoop`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/execution/feedback_loop.py

## Import Cycles
- None detected.

## Communities (187 total, 25 thin omitted)

### Community 0 - "implementations.py"
Cohesion: 0.08
Nodes (48): Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Th, test_read_symbols_indented_methods_and_duplicate_names(), test_read_symbols_impl(), _ddg_search(), _detect_doc_source(), _extract_identifiers(), _extract_symbols(), _git_run() (+40 more)

### Community 1 - "datetime"
Cohesion: 0.18
Nodes (13): ContentChunk, ContextSnapshot, SessionState, WorkingSetSnapshot, test_content_chunk_custom(), test_content_chunk_defaults(), test_context_snapshot_fields(), test_message_custom_fields() (+5 more)

### Community 2 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 3 - "SymbolIndex"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 4 - "ToolRegistry"
Cohesion: 0.08
Nodes (26): test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command(), test_tool_result_failure(), test_tool_result_success() (+18 more)

### Community 5 - "BaseSkill"
Cohesion: 0.08
Nodes (25): ABC, BaseSkill, CalculatorSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, Skills — external / plugin capabilities.  Skills are DIFFERENT from core tools: (+17 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.14
Nodes (8): _friendly_timeout_msg(), LMStudioClient, Synchronous streaming generator — yields tokens one-by-one.          Uses DEFAUL, Async streaming generator. Uses per-chunk read timeout (DEFAULT_TIMEOUT)., Simple synchronous query interface (LLMClient protocol compatibility)., Return a human-readable message explaining which part of the request timed out., Timeout, TimeoutException

### Community 7 - "TokenCounter"
Cohesion: 0.07
Nodes (32): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing. (+24 more)

### Community 8 - "repl_sandbox.py"
Cohesion: 0.19
Nodes (17): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+9 more)

### Community 9 - "ActionTracker"
Cohesion: 0.22
Nodes (5): ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex

### Community 10 - "test_resizer.py"
Cohesion: 0.26
Nodes (14): _build_app(), _click_resizer(), _drag_resizer(), Regression tests for the PaneResizer drag/click resizing in tui_app.py.  The Pan, No-op client so the engine never touches LM Studio / Ollama / cloud., Simulate a real drag: mouse_down -> captured MouseMove -> mouse_up., _resize_to(), _start_app() (+6 more)

### Community 11 - "test_enhanced_web_tools.py"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 12 - "RecoveryEngine"
Cohesion: 0.06
Nodes (56): get_recovery_hint(), inject_recovery_into_memory(), Any, Recovery engine for Torchlight errors.  Provides structured recovery strategies, Push recovery hint into memory state's tried_and_failed scratchpad list     to e, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type. (+48 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.11
Nodes (26): test_verify_compile_param(), test_edit_file_impl(), test_edit_file_impl_not_found(), test_grep_hyphen_pattern(), test_grep_impl(), test_grep_impl_file_path(), test_grep_impl_no_match(), test_list_dir_impl() (+18 more)

### Community 14 - "WebOutcomeInspector"
Cohesion: 0.09
Nodes (22): EphemeralHTTPServer, Any, HTMLParser, Path, QuietHTTPRequestHandler, Web Outcome Inspector for Torchlight.  Provides low-memory, ephemeral runtime an, Spins up a lightweight local HTTP server for static file inspection., Tier 1: Static HTML syntax and asset path validator. (+14 more)

### Community 15 - "test_context_budget_overflow.py"
Cohesion: 0.40
Nodes (5): Unit tests for context budget overflow detection and fixes in TieredMemory, RLME, test_tiered_memory_total_tokens_includes_pinned_files(), test_tool_context_window_scaling(), Tell the tool layer what context window the current model has., set_ctx_window()

### Community 16 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 17 - "InferenceParams"
Cohesion: 0.09
Nodes (19): InferenceParams, General conversation., Sampling parameters forwarded to the LLM /chat/completions endpoint.     Only no, Send messages and return the full response., Send messages and yield response chunks., One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters. (+11 more)

### Community 18 - "core/memory/persistence.py"
Cohesion: 0.12
Nodes (23): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, Session and project memory persistence for Torchlight., Ensure target project directory exists and has a local Git repository initialize, Write a marker proving the harness itself initialized this git repo.      Only w, Ensure target project directory exists and has `.context-memory.json` persistent (+15 more)

### Community 19 - "LlamaCppClient"
Cohesion: 0.09
Nodes (18): test_rlm_engine_solve_method(), LlamaCppClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.          Runs the, create_client(), display_step(), get_depth_style(), main() (+10 more)

### Community 20 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 21 - "CloudClient"
Cohesion: 0.19
Nodes (6): CloudClient, Sanitize message roles. Convert system role to user role for models (e.g. Gemma, Async streaming implementation required by LLMClient protocol., Return the ids of models the provider currently reports as available.         Us, Resolve requested self.model against live models to prevent 404 mismatches., _sanitize_messages_for_cloud()

### Community 22 - ".open_file_tab"
Cohesion: 0.14
Nodes (4): FileSelected, NodeSelected, Show or hide the center empty state (hide when a file is open)., Global key bindings that aren't caught by specific widgets.          Key contrac

### Community 23 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 24 - "ContextDashboard"
Cohesion: 0.10
Nodes (7): ContextDashboard, Panel, Print sub-agent task progress to the console., Return a new ActionTracker bound to this dashboard's console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 25 - "DebateVerifier"
Cohesion: 0.11
Nodes (20): Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., CritiqueResult, DebateVerifier, DebateVerifier implementation: orchestrates adversarial critique and refinement, Synthesize refined output incorporating valid critiques using InferenceParams.fo, Full debate flow: evaluate should_debate, execute critique, and refine if flaws, Helper to extract JSON payload or XML tags from LLM response. (+12 more)

### Community 26 - "verify_m1_setup.py"
Cohesion: 0.18
Nodes (24): format_memory_status(), get_memory_pressure(), is_memory_safe(), Memory pressure monitor for macOS Apple Silicon.  Provides real-time memory pres, Return a human-readable one-line memory status string., Get current macOS memory pressure level and stats.      Returns:         dict wi, Quick check: is it safe to run inference without swap thrashing?      Args:, check_hardware() (+16 more)

### Community 27 - "StreamingChatSession"
Cohesion: 0.11
Nodes (14): get_phase_system_prompt(), goal(), Panel, /params                    — show current params         /params auto, Start an autonomous goal execution session driven by .torchlight task tracking., Re-append closing tags and unclosed JSON braces that were consumed as stop token, Estimate tokens consumed by system prompt, tools, and flashlight beam., Infer the current agent phase from user input and the last model response. (+6 more)

### Community 28 - "test_tui_file_tree.py"
Cohesion: 0.13
Nodes (14): _FakeProc, anyio, Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)., test_git_tree_decorates_file_labels(), test_normalize_status_code(), test_parse_git_status_porcelain_basic(), test_parse_git_status_porcelain_quoted_path(), test_parse_git_status_porcelain_rename_takes_destination() (+6 more)

### Community 29 - "LLMClient"
Cohesion: 0.12
Nodes (18): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client() (+10 more)

### Community 30 - "Changelog"
Cohesion: 0.07
Nodes (26): Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+18 more)

### Community 31 - "RLMEngineOptimized"
Cohesion: 0.05
Nodes (44): ConversationSummarizer, Summarizer with LLM-powered and rule-based fallback paths.      When an llm_clie, Message, Return True if the most recent test run actually ran and has failing or, Verify Goal mode detects missing implementation_plan.md and forces 'plan' phase., Verify bare JSON tool calls without <tool_call> tags are correctly parsed as too, test_detect_phase_goal_mode_missing_plan_forces_plan(), test_parse_response_bare_json_tool_call() (+36 more)

### Community 32 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.19
Nodes (14): DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer, Message (+6 more)

### Community 34 - "get_tool_registry"
Cohesion: 0.08
Nodes (34): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_run_command_intercept_ast_functions(), test_search_ast_action_aliases(), test_search_ast_impl_fallback(), test_search_ast_schema_validation(), test_batch_tool_execution(), test_get_tool_registry(), test_tool_registry_preview_dry_run() (+26 more)

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
Nodes (5): DirectorySelected, on, Pressed, Selected, Submitted

### Community 39 - "core/memory/models.py"
Cohesion: 0.13
Nodes (24): Conversation Summarizer for Torchlight.  Extracts key information from conversat, ContentChunk, ContentType, ContextSnapshot, ExecutionMode, Message, MessageRole, Enum (+16 more)

### Community 41 - "rlm_engine_optimized.py"
Cohesion: 0.25
Nodes (7): build_step_message(), _looks_like_prose_or_outline(), Trim prose a model appended after the file body when </WRITE_FILE> was     consu, Heuristic gate for inline code interception (step 6b of _parse_response).      R, _trim_trailing_prose(), Validate tool call against schema and normalize parameter aliases.      Returns:, validate_and_normalize_tool_call()

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "Issues Found"
Cohesion: 0.12
Nodes (16): 1. **ExecutionMode Enum Mismatch**, 2. **Phase Detection Not Integrated with Goal Mode**, 3. **Goal Spec Initialization Race Condition**, 4. **Missing Verification Gate in CLI Goal Mode**, 5. **AutonomousHarness Not Wired to LLM Engine in CLI**, 6. **Inconsistent ExecutionMode Default**, 7. **Memory State Sync Issues**, Fix Plan (+8 more)

### Community 44 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 45 - "MemoryNeedle"
Cohesion: 0.21
Nodes (10): build_embedder(), Embedder, HybridEmbedder, KeywordEmbedder, Hybrid embedder: uses LLM embeddings when available, falls back to keyword vecto, Factory function to create an embedder., Base embedder interface., Simple term-frequency vector embedding. (+2 more)

### Community 46 - "CopySelectionModal"
Cohesion: 0.07
Nodes (31): anyio, Tests for Phase-1 transcript widgets (message cards, streaming, thinking)., Smoke test: the real app mounts MessageCards and drives the streaming view., test_app_transcript_wiring(), test_card_meta_for(), test_estimate_token_count(), test_message_card_composes(), test_streaming_view_updates() (+23 more)

### Community 47 - "GitFileTree"
Cohesion: 0.14
Nodes (15): DirectoryTree, DirEntry, git_status_for_tree(), GitFileTree, Path, Git-aware file tree for the Torchlight TUI.  Phase 4: the explorer's ``Directory, Check if a directory name should be skipped from exploration., Filter out OS noise, cache directories, and internal state files. (+7 more)

### Community 48 - "VerbatimCompactor"
Cohesion: 0.14
Nodes (6): CompressionConfig, Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 49 - "core/memory/manager.py"
Cohesion: 0.08
Nodes (31): Re-export TieredMemory and MemoryConfig from shared core library core.memory.man, Adaptive, headroom-driven context budget coordinator for Torchlight.  Static res, _is_valid_decision(), Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, Load persistent project memory (.context-memory.json) into L0 working state., Filter out empty, generic, or noisy session summary strings., Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length., _scratchpad_clean() (+23 more)

### Community 50 - "context_manager/memory/models.py"
Cohesion: 0.21
Nodes (11): _build_excerpt(), _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Run LLM extraction and merge findings into *state* in-place.          Returns Tr, Build a compact conversation view for the extraction prompt. (+3 more)

### Community 51 - "test_tui_status_bar.py"
Cohesion: 0.16
Nodes (17): anyio, Tests for Phase-4 consolidated status bar (gauge + segments widget)., test_build_status_segments_defaults(), test_build_status_segments_populated(), test_build_status_segments_running_no_tps_yet(), test_build_status_segments_server_offline_and_branch_escape(), test_gauge_markup_clamps_out_of_range(), test_gauge_markup_color_escalation() (+9 more)

### Community 52 - "SkillResult"
Cohesion: 0.16
Nodes (9): Any, ReproSkill, Any, Registry for external skills.      Does NOT contain core tools (READ_FILE, WRITE, Synchronous wrapper for use from non-async contexts., Trigger real load on first call, then delegate., SkillRegistry, SkillResult (+1 more)

### Community 53 - "SessionPersistence"
Cohesion: 0.18
Nodes (8): MemoryNeedle, MemoryObject, SessionState, SessionPersistence, test_memory_needle_custom(), test_memory_needle_defaults(), test_memory_object_defaults(), test_memory_object_full()

### Community 54 - "main_optimized.py"
Cohesion: 0.27
Nodes (12): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Step (+4 more)

### Community 55 - "AgentMemoryWidget"
Cohesion: 0.13
Nodes (9): AgentMemoryWidget, Displays the live L0 Agent Brain Scratchpad., CenterEmptyState, Container, Pressed, CenterEmptyState — the welcome / idle screen shown in the editor pane.  Replaces, Switch displayed content based on connection state., Route chip buttons to app-level actions. (+1 more)

### Community 56 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 57 - "tool_edit_file_impl"
Cohesion: 0.12
Nodes (26): test_edit_file_blocks_broken_syntax(), test_tool_edit_file_integration(), Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_auto_fallback_to_write(), test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_line_bounded(), test_edit_file_line_bounded_without_old_text() (+18 more)

### Community 58 - "ProjectGraph"
Cohesion: 0.16
Nodes (13): ProjectGraph, Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Remove all nodes and edges referencing a deleted file., Unit tests for incremental O(1) AST graph delta updates., test_incremental_graph_file_update(), test_update_project_graph_file_helper(), Path (+5 more)

### Community 59 - "MemoryObject"
Cohesion: 0.12
Nodes (24): compute_tf_idf_score(), cosine_similarity(), HybridMemoryRetriever, _is_low_memory(), MemoryObject, Hybrid Embedding & Vector Retrieval Engine for Torchlight.  Provides BM25/TF-IDF, Hybrid Memory Retrieval Engine.      Ranks MemoryObject items combining BM25/TF-, Score a single MemoryObject against a query. (+16 more)

### Community 60 - "test_tui_accessibility.py"
Cohesion: 0.10
Nodes (28): _make_app(), anyio, Tests for Phase-6 accessibility and keyboard navigation.  Covers: - Tab bar keyb, Arrow navigation wraps around at the ends., Arrow keys don't do anything when no tabs are open., Verify :focus rules exist for tab items in the .tcss file., Verify responsive @media-equivalent class rules exist., Verify no #hex color values appear in the .tcss file. (+20 more)

### Community 61 - "PaneResizer"
Cohesion: 0.09
Nodes (17): MouseDown, MouseUp, PaneResizer, ComposeResult, Interactive splitter bar to resize the left/right side panes.      Drag the bar, ComposeResult, ComposeResult, ComposeResult (+9 more)

### Community 62 - "CommandPalette"
Cohesion: 0.09
Nodes (14): Changed, Highlighted, NamedTuple, Modal dialog displaying keyboard shortcuts and slash commands., ShortcutsHelpModal, AttachContextModal, CommandPalette, PaletteResult (+6 more)

### Community 63 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 64 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 65 - "test_phase_detection.py"
Cohesion: 0.21
Nodes (13): _make_session(), Create a StreamingChatSession with mocked heavy dependencies., Troubleshoot wins over code when both signals are present., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., test_detect_chat_phase(), test_detect_code_phase(), test_detect_phase_empty_input() (+5 more)

### Community 66 - "tui_app.py"
Cohesion: 0.09
Nodes (29): test_list_available_models_includes_gemma4e4b(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), test_normalize_mlx_gemma_4_4e4b(), _detect_apple_silicon_ram(), _detect_chip(), fetch_provider_models(), is_port_in_use() (+21 more)

### Community 67 - "ProjectMemory"
Cohesion: 0.29
Nodes (6): ProjectMemory, MemoryObject, SessionState, test_corrupt_memory_file_self_heals(), test_manual_deletion_context_memory_self_heals(), test_project_memory_auto_init()

### Community 68 - "Architecture"
Cohesion: 0.15
Nodes (12): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Rules, Commands, Context Budget Breakdown, Development (+4 more)

### Community 69 - ".update_sidebar_meta"
Cohesion: 0.10
Nodes (9): _provider_runtime_info(), Return (port, externally_managed) for a given provider key.      externally_mana, Sync all connection-dependent UI elements.          Called on server status chan, Update the context usage bar in the Agent tab., Build the AST knowledge graph silently in background thread., Consolidated Phase-4 status bar (state · model · context gauge · tps · tokens ·, Committed memory tokens plus in-flight streamed tokens for the context gauge., Repoint the file tree at the engine root and refresh git status. (+1 more)

### Community 70 - "test_code_quality_harness.py"
Cohesion: 0.06
Nodes (50): Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_compile_gate_rejects_return_outside_function(), test_detect_stubs(), test_detect_symptom_patching() (+42 more)

### Community 71 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 72 - "._handle_slash_command"
Cohesion: 0.16
Nodes (3): copy_to_clipboard(), Copy text to system clipboard across macOS, Linux, and Windows., Manually trigger memory context compaction.

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

### Community 82 - "TorchlightApp"
Cohesion: 0.07
Nodes (21): anyio, Tests for Phase-5 tabbed editor split pane (open_file_tab, dirty marker, keyboar, test_close_file_tab_removes_from_open_tabs(), test_close_file_tab_switches_active_tab(), test_dirty_marker_not_set_for_non_tab_file(), test_dirty_marker_set_on_write_step(), test_editor_split_pane_composes(), test_get_tab_hash() (+13 more)

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

### Community 94 - "test_inline_interception.py"
Cohesion: 0.24
Nodes (11): _looks_like_full_file(), Helper to check if content looks like a complete standalone file rather than a s, MockEngine, Unit tests for inline code interception safety checks, tight regex matching, and, test_detect_phase_prioritizes_write_and_file_extensions(), test_existing_file_partial_snippet_protection(), test_explicit_pre_text_path_declaration_triggers(), test_in_block_comment_header_triggers() (+3 more)

### Community 104 - "FolderPickerModal"
Cohesion: 0.05
Nodes (26): AgentStatusModal, ApprovalModal, FileActionModal, FolderPickerModal, Production-grade modal dialog for tool & file modification approval., Modal dialog for interactive visual folder selection across the entire computer., Modal dialog for selecting session execution mode (Chat vs Goal)., Modal dialog presenting OS options when a file is selected in the Explorer tree. (+18 more)

### Community 105 - "get_workspace_pending_tasks"
Cohesion: 0.29
Nodes (8): anyio, test_get_workspace_pending_tasks_goal_spec(), test_get_workspace_pending_tasks_md(), test_verification_gate_allows_final_answer_when_all_done(), test_verification_gate_rejects_premature_final_answer(), get_workspace_pending_tasks(), Unified Task Helper Module for Torchlight.  Extracts pending tasks from implemen, Extract list of pending task descriptions from the workspace.     Priority order

### Community 106 - "Context Manager CLI"
Cohesion: 0.20
Nodes (9): Architecture, CLI Options, Commands (in CLI), Context Manager CLI, Features, How It Works, Installation, Requirements (+1 more)

### Community 107 - "Torchlight — Terminal AI Coding Agent"
Cohesion: 0.18
Nodes (11): Architecture, CLI Commands, Core Flow, Development, Error Handling, Key Features, Memory Files, Module Structure (+3 more)

### Community 108 - "ConversationSummarizer"
Cohesion: 0.25
Nodes (6): ConversationSummarizer, Message, Summarize conversation turns for compression., Create a simple summary of messages., Extract key information from text., _role_label()

### Community 110 - ".build"
Cohesion: 0.16
Nodes (12): get_project_graph(), Any, Path, Scan project files and construct the AST graph., Perform an incremental O(1) AST update for a single modified file., Save graph data to JSON and markdown report., Load graph from JSON file if available., Find relationship path between source and target symbols. (+4 more)

### Community 111 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 112 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 113 - "test_tui_trajectory_rail.py"
Cohesion: 0.24
Nodes (9): anyio, Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)., The streamed <tool_call> adds a dot; the completing step flips it., test_app_pending_step_updates_rail(), test_rail_add_pending_and_complete_ok(), test_rail_clear_removes_dots(), test_rail_complete_error_and_denied(), test_rail_complete_without_pending_is_noop() (+1 more)

### Community 114 - "SymbolIndex"
Cohesion: 0.15
Nodes (9): BeamResult, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build() (+1 more)

### Community 116 - "test_tui_theme.py"
Cohesion: 0.18
Nodes (15): _make_app(), anyio, Tests for Phase-6 theme consistency and responsive layout classes.  Covers: - CS, Ensure CSS doesn't contain hardcoded hex colors., Ensure CSS uses theme variables like $background., Ensure CSS has rules for responsive terminal classes., Responsive classes are applied when terminal is narrow., Short-terminal class applied when height < 24. (+7 more)

### Community 117 - "Resource-Adaptive Features"
Cohesion: 0.29
Nodes (7): Compression Cooldown, Embedding Cache, LLM State Extraction, Resource-Adaptive Configuration, Resource-Adaptive Features, Resource Tiers, Tool Result Budget

### Community 118 - "IndexVisitor"
Cohesion: 0.27
Nodes (4): index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings.

### Community 119 - "test_tool_parser.py"
Cohesion: 0.13
Nodes (26): Unit tests for core/tools/parser.py tolerant tool parser & fuzzy repair engine., test_extract_balanced_json_object(), test_parse_tool_call_payload(), test_repair_unclosed_action_tags(), test_repair_unclosed_tool_call_tag(), test_single_quoted_dict_parsing(), test_strip_interleaved_prose(), test_strip_thinking_tags() (+18 more)

### Community 123 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 124 - "dashboard.py"
Cohesion: 0.33
Nodes (3): _ActionContext, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 125 - "TieredMemory"
Cohesion: 0.06
Nodes (43): ContextSnapshot, MemoryConfig, Tiered memory system with L0-L3 hierarchy:     - L0: Active prompt (current cont, Return list of (path, content) for pinned files., Remove all pinned files., Compact context between tasks while preserving continuous session state., Calculate remaining token budget headroom before reaching max_tokens threshold., Predict likely next tools based on current state. (+35 more)

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

### Community 132 - "test_dedup.py"
Cohesion: 0.20
Nodes (12): Unit tests for core/tools/dedup.py argument normalization & TrajectoryLock., test_compute_payload_hash(), test_normalize_tool_args(), test_trajectory_lock(), compute_payload_hash(), normalize_tool_args(), Any, Anti-Looping Trajectory Lock and Tool Payload Signature Deduplication.  Provides (+4 more)

### Community 133 - "test_tui_plan_panel.py"
Cohesion: 0.18
Nodes (16): _build_plan_text(), _make_app(), anyio, Delegate to the real TUI plan-builder helper., Repeated checklist entries (summary + detailed sections) must not duplicate., test_build_plan_text_all_done(), test_build_plan_text_dedupes_duplicate_checkbox_lines(), test_build_plan_text_goal_spec_json() (+8 more)

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

### Community 138 - "._safe_mount"
Cohesion: 0.25
Nodes (3): Append a line to the Output tab's RichLog.          severity: 'info' | 'tool' |, Mount a widget defensively and scroll safely after layout pass., Mount a running ToolCallCard for a streamed ``<tool_call>`` marker.          Kep

### Community 139 - "format.py"
Cohesion: 0.25
Nodes (5): build_plan_overview_text(), build_task_checklist_text(), Pure text-formatting helpers for the Torchlight TUI.  No engine / App state, no, Render Implementation Plan overview (title & mode badge)., Render Task Checklist hierarchy & progress bar.

### Community 140 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 148 - "LLMStateExtractor"
Cohesion: 0.29
Nodes (3): LLMStateExtractor, Uses the local LLM to extract structured SessionState fields from a     conversa, Return a copy of the call/hit/miss/error counters.

### Community 149 - "AutonomousHarness"
Cohesion: 0.07
Nodes (43): AutonomousHarness, GoalSpec, HarnessConfig, Enum, Path, str, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, Ensure target project has local git repository and persistent memory initialized (+35 more)

### Community 150 - "context_manager/memory/persistence.py"
Cohesion: 0.67
Nodes (4): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path

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
Cohesion: 0.09
Nodes (25): anyio, Tests for Phase-2 tool call cards (risk badge, status, timing, sections)., The streamed <tool_call> mounts a pending card completed by the step., test_app_pending_card_wiring(), test_risk_for_tool(), test_summarize_args(), test_tool_card_complete_denied(), test_tool_card_complete_error_expands() (+17 more)

### Community 156 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

### Community 157 - "PromptTextArea"
Cohesion: 0.06
Nodes (37): Binding, anyio, Tests for Phase-4 command palette + prompt autocomplete., test_build_palette_items_kinds_and_visibility(), test_command_palette_composes_filters_and_selects(), test_command_palette_enter_runs_highlighted_item(), test_fuzzy_filter_empty_query_and_no_match(), test_fuzzy_filter_prefix_beats_substring() (+29 more)

### Community 158 - "MyCustomSkill"
Cohesion: 0.33
Nodes (3): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi

### Community 159 - "get_phase_system_prompt"
Cohesion: 0.13
Nodes (13): DirectiveTracker, Any, Directive tracker and constraint violation reinforcement module for Torchlight., Record a directive violation (e.g. 'cd_command', 'test_assertion_delete'), Reset violation counts., Tracks model constraint violations during execution turns and dynamically     in, get_phase_system_prompt(), Unified system prompts for Torchlight.  Single source of truth for all frontends (+5 more)

### Community 160 - "cli/main.py"
Cohesion: 0.12
Nodes (15): command, _beam_budget(), chat(), compress_file(), count_tokens(), Start an interactive chat session with context management and flashlight., Compress a file using verbatim compaction., Count tokens in text. (+7 more)

### Community 161 - "Flashlight"
Cohesion: 0.26
Nodes (4): _beam_config_for_context(), Flashlight, FileEntry, SymbolIndex

### Community 163 - "Plan: UI Improvements — Torchlight Codex IDE"
Cohesion: 0.18
Nodes (10): Decisions, Effort & Sequencing, Non-Goals, Plan: UI Improvements — Torchlight Codex IDE, Task 1: Fix Latent Bugs (prerequisite), Task 2: Phase 5 — Tabbed Editor Split Pane, Task 3: Phase 6a — Accessibility & Focus Management, Task 4: Phase 6b — Performance & Streaming Polish (+2 more)

### Community 164 - "opencode.json"
Cohesion: 0.50
Nodes (3): plugin, $schema, .opencode/plugins/graphify.js

### Community 167 - ".for_critic"
Cohesion: 0.40
Nodes (3): Adversarial critique / debate. Focused flaw identification., Synthesis and refinement following critique. Deterministic., test_critic_and_refine_presets()

### Community 168 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

### Community 169 - "ExecutionFeedbackLoop"
Cohesion: 0.06
Nodes (44): Re-export ExecutionFeedbackLoop and TestRunResult from shared core library core., Execution feedback loop for Torchlight., Post-edit auto-run test suite failure., TestFailureError, ExecutionFeedbackLoop, extract_surgical_traceback(), Enum, Path (+36 more)

### Community 170 - ".query"
Cohesion: 0.33
Nodes (3): Search nodes matching search_term. Returns code snippets alongside names., Read a short code snippet from disk for a matched node., Return structured summary of files, classes, and function signatures.

### Community 172 - ".memory"
Cohesion: 0.40
Nodes (3): estimate_metadata_overhead(), Estimate tokens consumed by system prompt, tool schemas, and the flashlight beam, setter

### Community 174 - "discovery.py"
Cohesion: 0.18
Nodes (14): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+6 more)

### Community 175 - "classify_command"
Cohesion: 0.09
Nodes (29): CoreToolRegistry, get_core_registry(), Any, Compatibility subclass of ToolRegistry providing CLI-specific execute/dangerous_, test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command() (+21 more)

### Community 177 - "test_tui_diff_view.py"
Cohesion: 0.10
Nodes (31): anyio, Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)., A pre-write snapshot (from approval) wins over the already-written disk state., The engine's own CODE_FILE_WRITE approval path is diffable too., The approval modal shows a DIFF PREVIEW section when entries exist., A successful WRITE_FILE step mounts a DiffView card with real content., test_app_write_step_renders_diff_card(), test_approval_modal_omits_diff_when_empty() (+23 more)

### Community 179 - "TestApp"
Cohesion: 0.22
Nodes (5): App, ComposeResult, on, Pressed, TestApp

### Community 182 - "Message"
Cohesion: 0.18
Nodes (7): Message, MessageRole, Persist L0 working state to disk in .context-memory.json (debounced)., Update or set the primary system prompt (first system message in history)., Generic add_message method for role-based message addition., Compress older messages, preserving the first N messages., Async wrapper for compress_recent.

### Community 191 - "TestApp"
Cohesion: 0.33
Nodes (3): App, ComposeResult, TestApp

### Community 193 - "core/api/lmstudio.py"
Cohesion: 0.40
Nodes (4): Re-export LMStudioClient from shared core library core.api.lmstudio., get_phase_inference_params(), LM Studio REST client.  Recovered from the original CLI implementation (commit f, Return the inference parameters preset for a named phase.

## Knowledge Gaps
- **340 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `context-manager-cli`, `run.sh script`, `COLORTERM` (+335 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AutonomousHarness` connect `AutonomousHarness` to `cli/main.py`, `tui_app.py`, `SymbolIndex`, `core/memory/models.py`, `FolderPickerModal`, `ExecutionFeedbackLoop`, `._handle_slash_command`, `CopySelectionModal`, `TorchlightApp`, `PaneResizer`, `AgentMemoryWidget`, `StreamingChatSession`, `TieredMemory`, `CommandPalette`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `TorchlightApp` connect `TorchlightApp` to `test_tui_plan_panel.py`, `test_resizer.py`, `._safe_mount`, `format.py`, `LlamaCppClient`, `AutonomousHarness`, `CloudClient`, `.open_file_tab`, `ToolCallCard`, `PromptTextArea`, `RLMEngineOptimized`, `on`, `._apply_pane_widths`, `CopySelectionModal`, `GitFileTree`, `test_tui_diff_view.py`, `._submit_user_input`, `AgentMemoryWidget`, `test_tui_accessibility.py`, `PaneResizer`, `CommandPalette`, `tui_app.py`, `.update_sidebar_meta`, `._handle_slash_command`, `FolderPickerModal`, `test_tui_trajectory_rail.py`, `test_tui_theme.py`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `TieredMemory` connect `TieredMemory` to `cli/main.py`, `.compact_context`, `ContextBudget`, `core/memory/models.py`, `ExecutionFeedbackLoop`, `MemoryObject`, `get_workspace_pending_tasks`, `rlm_engine_optimized.py`, `MemoryNeedle`, `.memory`, `test_context_budget_overflow.py`, `core/memory/manager.py`, `LlamaCppClient`, `AutonomousHarness`, `Message`, `tool_edit_file_impl`, `StreamingChatSession`, `RLMEngineOptimized`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `TorchlightApp` (e.g. with `_StubClient` and `AutonomousHarness`) actually correct?**
  _`TorchlightApp` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `TieredMemory` (e.g. with `StreamingChatSession` and `AutonomousHarness`) actually correct?**
  _`TieredMemory` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `RLMEngineOptimized` (e.g. with `ConversationSummarizer` and `Message`) actually correct?**
  _`RLMEngineOptimized` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `MemoryConfig` (e.g. with `StreamingChatSession` and `ContextBudget`) actually correct?**
  _`MemoryConfig` has 19 INFERRED edges - model-reasoned connections that need verification._