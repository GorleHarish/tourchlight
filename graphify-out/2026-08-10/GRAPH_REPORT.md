# Graph Report - tourchlight v1_i6  (2026-08-10)

## Corpus Check
- 232 files · ~174,639 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3530 nodes · 7248 edges · 194 communities (174 shown, 20 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 659 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7f136666`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_tui_command_palette.py
- context_manager/memory/models.py
- ProjectSnapshot
- SymbolIndex
- ToolRegistry
- BaseSkill
- LMStudioClient
- TokenCounter
- repl_sandbox.py
- LlamaCppClient
- test_resizer.py
- StructurePreservingHTMLParser
- RecoveryEngine
- test_implementations.py
- HtmlGamePlayer
- ActionTracker
- TrajectoryLogger
- InferenceParams
- ensure_project_initialized
- rlm_engine_optimized.py
- android_ref_build.md
- test_tools_core.py
- test_tui_plan_panel.py
- PlanningSkill
- ContextDashboard
- DebateVerifier
- verify_m1_setup.py
- StreamingChatSession
- cli/main.py
- LLMClient
- Changelog
- RLMEngineOptimized
- PyASTVisitor
- context_manager/compression/summarizer.py
- TorchlightApp
- android_ref_runtime.md
- VerbatimCompactor
- ContextBudget
- context_manager/memory/persistence.py
- TaskDAG
- PaneResizer
- main_optimized.py
- TDDSkill
- Issues Found
- android_ref_emulator.md
- AutonomousHarness
- MessageCard
- context-manager-cli/tests/test_models.py
- VerbatimCompactor
- core/memory/manager.py
- ProjectMemory
- test_tui_status_bar.py
- SkillResult
- test_surgical_task_verification.py
- task_helpers.py
- ConversationSummarizer
- Torchlight Architecture
- tool_edit_file_impl
- ProjectGraph
- core/memory/persistence.py
- test_tui_accessibility.py
- test_tui_file_tree.py
- ToolCallCard
- TDDSkill
- android_ref_adb.md
- SelectiveCompressor
- SelectiveCompressor
- unified.py
- Architecture
- OllamaClient
- test_code_quality_harness.py
- prompts_minimal.py
- test_phase_detection.py
- android_ref_signing.md
- Prompt Templates for 7B Coder Models
- Torchlight Excellence Roadmap
- Checklist
- Memory System Deep Dive
- ProjectMemory
- Execution Feedback Loop
- start_optimized_local.sh
- CenterEmptyState
- setup_optimized.sh
- tui_app.py
- run.sh
- prompts/__init__.py
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- test_tui_tabbed_editor.py
- context-manager-cli
- torchlight-core
- test_grammar_parse.py
- Console
- Context Manager CLI
- Torchlight — Terminal AI Coding Agent
- test_tui_tool_cards.py
- .agents/AGENTS.md
- .build
- Data Flow
- Core Classes
- Static
- SymbolIndex
- ConnectionPill
- test_tui_theme.py
- Resource-Adaptive Features
- mark_task_status
- test_tool_parser.py
- rules/graphify.md
- workflows/graphify.md
- web_server.py
- on
- TieredMemory
- Target Quality Tiers
- P1: Important Follow-On Work
- Compression System
- Future Improvements
- Improvement Recommendations by Resource Tier
- Torchlight Documentation
- TrajectoryLock
- test_plan_execution_loop.py
- TestResult
- Android Troubleshoot — Routing Layer
- Memory Tiers
- Persistence
- .load
- CloudClient
- Retrieval System
- ~350 tokens. Do NOT load other reference files in the same turn.
- Profile: Run -> Profile app -> Memory tab
- at android.app.Activity...          <- framework — ignore
- StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
- Context null in Fragment -> requireContext() (throws if detached, which is correct)
- implementation 'androidx.multidex:multidex:2.0.1'
- Never use StrictMode.allowThreadDiskReads() — it masks the bug
- test_prompts_and_memory.py
- TaskSpec
- autonomous_harness.py
- _load_goal_spec
- context_manager/prompts.py
- Plan: Non-Security Improvements
- context_manager/memory/embeddings.py
- ActionEntry
- classify_command
- IndexVisitor
- .complete
- DirectiveTracker
- normalize_model_name
- Flashlight
- PromptTextArea
- Plan: UI Improvements — Torchlight Codex IDE
- opencode.json
- .__init__
- graphify.js
- get_tool_registry
- HTMLGameSkill
- ExecutionFeedbackLoop
- MyCustomSkill
- test_tui_trajectory_rail.py
- .has_failing_tests
- core/api/lmstudio.py
- discovery.py
- tool_card.py
- sync_workspace_tasks
- test_tui_diff_view.py
- implementations.py
- TestApp
- dashboard.py
- test_goal_mode_process.py
- ._append_message
- _clean_and_parse_json
- Token Budget
- test_execution_mode_normalization_and_sync
- .set_execution_mode_callback
- ._stream_llm_with_retry
- asyncio
- tui_widgets/__init__.py

## God Nodes (most connected - your core abstractions)
1. `TorchlightApp` - 168 edges
2. `TieredMemory` - 146 edges
3. `RLMEngineOptimized` - 91 edges
4. `MemoryConfig` - 83 edges
5. `AutonomousHarness` - 63 edges
6. `ExecutionFeedbackLoop` - 53 edges
7. `LlamaCppClient` - 45 edges
8. `StreamingChatSession` - 41 edges
9. `CloudClient` - 39 edges
10. `Step` - 38 edges

## Surprising Connections (you probably didn't know these)
- `test_classify_safe_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py
- `test_classify_destructive_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py
- `test_classify_install_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py
- `test_classify_empty_command()` --calls--> `classify_command()`  [INFERRED]
  context-manager-cli/tests/test_tools_core.py → core/tools/classification.py
- `test_action_entry_markup_safety()` --calls--> `ActionEntry`  [EXTRACTED]
  core/tests/test_markup_escaping.py → context-manager-cli/src/context_manager/cli/dashboard.py

## Import Cycles
- None detected.

## Communities (194 total, 20 thin omitted)

### Community 0 - "test_tui_command_palette.py"
Cohesion: 0.06
Nodes (34): Binding, Changed, anyio, Tests for Phase-4 command palette + prompt autocomplete., test_build_palette_items_kinds_and_visibility(), test_command_palette_composes_filters_and_selects(), test_command_palette_enter_runs_highlighted_item(), test_fuzzy_filter_empty_query_and_no_match() (+26 more)

### Community 1 - "context_manager/memory/models.py"
Cohesion: 0.12
Nodes (16): _build_excerpt(), LLMStateExtractor, _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa (+8 more)

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
Cohesion: 0.09
Nodes (19): ABC, BaseSkill, CalculatorSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, MarkdownDocumentSkill (+11 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.14
Nodes (8): _friendly_timeout_msg(), LMStudioClient, Synchronous streaming generator — yields tokens one-by-one.          Uses DEFAUL, Async streaming generator. Uses per-chunk read timeout (DEFAULT_TIMEOUT)., Simple synchronous query interface (LLMClient protocol compatibility)., Return a human-readable message explaining which part of the request timed out., Timeout, TimeoutException

### Community 7 - "TokenCounter"
Cohesion: 0.12
Nodes (22): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, Configuration for selective memory compression., Create a compressor tuned for the given context window.      Always pass the sha, Summary of a conversation turn. (+14 more)

### Community 8 - "repl_sandbox.py"
Cohesion: 0.09
Nodes (30): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+22 more)

### Community 9 - "LlamaCppClient"
Cohesion: 0.04
Nodes (39): A successful WRITE_FILE step mounts a DiffView card with real content., test_app_write_step_renders_diff_card(), DirectoryTree, NamedTuple, LlamaCppClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.          Runs the, Step (+31 more)

### Community 10 - "test_resizer.py"
Cohesion: 0.26
Nodes (14): _build_app(), _click_resizer(), _drag_resizer(), Regression tests for the PaneResizer drag/click resizing in tui_app.py.  The Pan, No-op client so the engine never touches LM Studio / Ollama / cloud., Simulate a real drag: mouse_down -> captured MouseMove -> mouse_up., _resize_to(), _start_app() (+6 more)

### Community 11 - "StructurePreservingHTMLParser"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 12 - "RecoveryEngine"
Cohesion: 0.06
Nodes (59): get_recovery_hint(), inject_recovery_into_memory(), Any, Recovery engine for Torchlight errors.  Provides structured recovery strategies, Push recovery hint into memory state's tried_and_failed scratchpad list     to e, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type. (+51 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.08
Nodes (36): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_read_symbols_indented_methods_and_duplicate_names(), test_run_command_intercept_ast_functions(), test_search_ast_action_aliases(), test_search_ast_impl_fallback(), test_verify_compile_param(), test_edit_file_impl(), test_edit_file_impl_not_found() (+28 more)

### Community 14 - "HtmlGamePlayer"
Cohesion: 0.05
Nodes (50): GameInputEvent, GameOutcomeResult, get_process_memory_mb(), HtmlGamePlayer, Path, HTML Game Inspector & Player Harness for Torchlight.  Provides autonomous playin, Autonomous HTML Game Harness & Dynamic Verifier.      Launches an ephemeral brow, Plays the HTML game for duration_ms while simulating inputs and checking frame d (+42 more)

### Community 15 - "ActionTracker"
Cohesion: 0.22
Nodes (5): ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex

### Community 16 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 17 - "InferenceParams"
Cohesion: 0.08
Nodes (23): detect_model_traits(), InferenceParams, Abstract LLM client interface and shared inference parameters.  All LLM backends, Writing code files. Near-deterministic — exact syntax matters., Reasoning through plans. Moderate creativity. All tools remain available., Detect architecture traits (size, reasoning status) from model name.      Return, Diagnosing errors. Slightly more exploration., General conversation. (+15 more)

### Community 18 - "ensure_project_initialized"
Cohesion: 0.09
Nodes (26): Ensure target project has local git repository and persistent memory initialized, ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, Ensure target project directory exists and has a local Git repository initialize, Write a marker proving the harness itself initialized this git repo.      Only w, Ensure target project directory exists and has `.context-memory.json` persistent (+18 more)

### Community 19 - "rlm_engine_optimized.py"
Cohesion: 0.08
Nodes (29): ConversationSummarizer, Summarizer with LLM-powered and rule-based fallback paths.      When an llm_clie, Conversation Summarizer for Torchlight.  Extracts key information from conversat, Message, _detect_apple_silicon_ram(), _detect_chip(), estimate_metadata_overhead(), Detect total RAM in GB on macOS. (+21 more)

### Community 20 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 21 - "test_tools_core.py"
Cohesion: 0.13
Nodes (16): CoreToolRegistry, get_core_registry(), Any, Compatibility subclass of ToolRegistry providing CLI-specific execute/dangerous_, test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command() (+8 more)

### Community 22 - "test_tui_plan_panel.py"
Cohesion: 0.16
Nodes (18): _build_plan_text(), _make_app(), anyio, Delegate to the real TUI plan-builder helper., Verify build_plan_text handles bulleted plan lists without explicit checkboxes., Repeated checklist entries (summary + detailed sections) must not duplicate., test_build_plan_text_all_done(), test_build_plan_text_dedupes_duplicate_checkbox_lines() (+10 more)

### Community 23 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 24 - "ContextDashboard"
Cohesion: 0.10
Nodes (7): ContextDashboard, Panel, Print sub-agent task progress to the console., Return a new ActionTracker bound to this dashboard's console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 25 - "DebateVerifier"
Cohesion: 0.09
Nodes (23): Adversarial critique / debate. Focused flaw identification., Synthesis and refinement following critique. Deterministic., Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., CritiqueResult, DebateVerifier, DebateVerifier implementation: orchestrates adversarial critique and refinement, Synthesize refined output incorporating valid critiques using InferenceParams.fo (+15 more)

### Community 26 - "verify_m1_setup.py"
Cohesion: 0.18
Nodes (24): format_memory_status(), get_memory_pressure(), is_memory_safe(), Memory pressure monitor for macOS Apple Silicon.  Provides real-time memory pres, Return a human-readable one-line memory status string., Get current macOS memory pressure level and stats.      Returns:         dict wi, Quick check: is it safe to run inference without swap thrashing?      Args:, check_hardware() (+16 more)

### Community 27 - "StreamingChatSession"
Cohesion: 0.11
Nodes (15): chat(), get_phase_system_prompt(), goal(), Panel, /params                    — show current params         /params auto, Start an interactive chat session with context management and flashlight., Start an autonomous goal execution session driven by .torchlight task tracking., Re-append closing tags and unclosed JSON braces that were consumed as stop token (+7 more)

### Community 28 - "cli/main.py"
Cohesion: 0.11
Nodes (12): command, compress_file(), count_tokens(), Compress a file using verbatim compaction., Count tokens in text., Manage saved sessions., Lock phase based on concrete execution events., _risk_tier() (+4 more)

### Community 29 - "LLMClient"
Cohesion: 0.08
Nodes (21): LLMClient, Protocol, Protocol that all LLM backends must implement.      Both sync and async methods, Send messages and return the full response., Send messages and yield response chunks., Check if the backend is reachable., List available models., Simple query interface (for backward compatibility). (+13 more)

### Community 30 - "Changelog"
Cohesion: 0.06
Nodes (30): Added, Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+22 more)

### Community 31 - "RLMEngineOptimized"
Cohesion: 0.14
Nodes (21): anyio, test_verification_gate_allows_final_answer_when_all_done(), test_verification_gate_rejects_premature_final_answer(), test_action_tag_braces_inside_string_values(), test_action_tag_no_json_args(), test_action_tag_unclosed_with_trailing_prose(), test_inline_interception_requires_explicit_file_or_header(), test_inline_interception_skips_plan_phase() (+13 more)

### Community 32 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.19
Nodes (14): DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer, Message (+6 more)

### Community 34 - "TorchlightApp"
Cohesion: 0.04
Nodes (30): Tests for TorchlightApp project_root property and task manager modal integration, test_action_task_manager_pushes_screen(), test_torchlight_app_project_root_fallback(), test_torchlight_app_project_root_property(), is_port_in_use(), Check if server port 8080 is actively listening., copy_to_clipboard(), App (+22 more)

### Community 35 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (8): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 37 - "ContextBudget"
Cohesion: 0.06
Nodes (18): _clamp(), ContextBudget, Token reserve kept for the recent-message window., Current fraction of the target window in use., Effective budget allocations for the current turn.      `used_tokens` is the liv, Token allowance for the L0 working memory scratchpad this turn., Max characters per scratchpad entry (longer when headroom is ample)., Max entries shown per state section (3 tight ... 8 rich). (+10 more)

### Community 38 - "context_manager/memory/persistence.py"
Cohesion: 0.22
Nodes (8): SessionState, ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, SessionPersistence, test_session_state_defaults(), test_session_state_populated()

### Community 39 - "TaskDAG"
Cohesion: 0.07
Nodes (38): Any, Enum, str, Robust Task Lifecycle and Directed Acyclic Graph (DAG) Engine for Torchlight.  P, Directed Acyclic Graph (DAG) for Task Lifecycle Management., Add a task node to the DAG after verifying cycle safety., Remove a node and strip references to it from dependencies and subtasks., Detect cycles using Kahn's topological sort algorithm. (+30 more)

### Community 40 - "PaneResizer"
Cohesion: 0.16
Nodes (6): Click, MouseDown, MouseMove, MouseUp, PaneResizer, Interactive splitter bar to resize the left/right side panes.      Drag the bar

### Community 41 - "main_optimized.py"
Cohesion: 0.27
Nodes (12): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Step (+4 more)

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "Issues Found"
Cohesion: 0.12
Nodes (16): 1. **ExecutionMode Enum Mismatch**, 2. **Phase Detection Not Integrated with Goal Mode**, 3. **Goal Spec Initialization Race Condition**, 4. **Missing Verification Gate in CLI Goal Mode**, 5. **AutonomousHarness Not Wired to LLM Engine in CLI**, 6. **Inconsistent ExecutionMode Default**, 7. **Memory State Sync Issues**, Fix Plan (+8 more)

### Community 44 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 45 - "AutonomousHarness"
Cohesion: 0.29
Nodes (17): AutonomousHarness, HarnessConfig, Autonomous Harness Engine driving long-running continuous execution., main(), CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., create_mock_feedback_loop(), Path, Unit tests for AutonomousHarness module. (+9 more)

### Community 46 - "MessageCard"
Cohesion: 0.07
Nodes (30): anyio, Tests for Phase-1 transcript widgets (message cards, streaming, thinking)., Smoke test: the real app mounts MessageCards and drives the streaming view., test_app_transcript_wiring(), test_card_meta_for(), test_estimate_token_count(), test_message_card_composes(), test_streaming_view_updates() (+22 more)

### Community 47 - "context-manager-cli/tests/test_models.py"
Cohesion: 0.15
Nodes (15): ContentChunk, ContextSnapshot, MemoryNeedle, MemoryObject, WorkingSetSnapshot, test_content_chunk_custom(), test_content_chunk_defaults(), test_context_snapshot_fields() (+7 more)

### Community 48 - "VerbatimCompactor"
Cohesion: 0.22
Nodes (5): Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 49 - "core/memory/manager.py"
Cohesion: 0.08
Nodes (41): Re-export TieredMemory and MemoryConfig from shared core library core.memory.man, Adaptive, headroom-driven context budget coordinator for Torchlight.  Static res, Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length., _scratchpad_clean(), ContentChunk, ContentType, ContextSnapshot (+33 more)

### Community 50 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 51 - "test_tui_status_bar.py"
Cohesion: 0.16
Nodes (17): anyio, Tests for Phase-4 consolidated status bar (gauge + segments widget)., test_build_status_segments_defaults(), test_build_status_segments_populated(), test_build_status_segments_running_no_tps_yet(), test_build_status_segments_server_offline_and_branch_escape(), test_gauge_markup_clamps_out_of_range(), test_gauge_markup_color_escalation() (+9 more)

### Community 52 - "SkillResult"
Cohesion: 0.20
Nodes (7): Any, ReproSkill, Any, Synchronous wrapper for use from non-async contexts., Trigger real load on first call, then delegate., SkillResult, expr

### Community 53 - "test_surgical_task_verification.py"
Cohesion: 0.20
Nodes (13): Unit tests for Surgical Targeted Task Verification in Torchlight., test_verify_task_preflight_invalid_json(), test_verify_task_preflight_syntax_error(), test_verify_task_preflight_valid_python(), test_verify_task_targeted_command(), _extract_referenced_files(), _find_file_in_project(), Extract distinct code/markup filenames referenced in task description. (+5 more)

### Community 54 - "task_helpers.py"
Cohesion: 0.16
Nodes (19): test_insert_task_into_plan_section(), Tests for robust task and status tracking in LLM context and TUI., test_compact_task_matrix_adaptive_rendering(), test_status_badges_and_boxes(), test_validate_task_transition(), _file_looks_complete(), get_compact_task_matrix(), insert_task_into_plan() (+11 more)

### Community 55 - "ConversationSummarizer"
Cohesion: 0.29
Nodes (7): ConversationSummarizer, Message, Summarize conversation turns for compression using high-density structured templ, Generate a high-density structured compaction template preserving key context in, Create a compact structured summary of messages., Extract key information from text., _role_label()

### Community 56 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 57 - "tool_edit_file_impl"
Cohesion: 0.12
Nodes (26): test_edit_file_blocks_broken_syntax(), test_tool_edit_file_integration(), Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_auto_fallback_to_write(), test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_line_bounded(), test_edit_file_line_bounded_without_old_text() (+18 more)

### Community 58 - "ProjectGraph"
Cohesion: 0.18
Nodes (20): get_project_graph(), ProjectGraph, Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Get or create the ProjectGraph instance for a given root directory., Incrementally update the AST graph for a single modified file., update_project_graph_file(), Unit tests for incremental O(1) AST graph delta updates. (+12 more)

### Community 59 - "core/memory/persistence.py"
Cohesion: 0.10
Nodes (33): build_embedder(), compute_tf_idf_score(), cosine_similarity(), Embedder, HybridEmbedder, HybridMemoryRetriever, _is_low_memory(), KeywordEmbedder (+25 more)

### Community 60 - "test_tui_accessibility.py"
Cohesion: 0.10
Nodes (28): _make_app(), anyio, Tests for Phase-6 accessibility and keyboard navigation.  Covers: - Tab bar keyb, Arrow navigation wraps around at the ends., Arrow keys don't do anything when no tabs are open., Verify :focus rules exist for tab items in the .tcss file., Verify responsive @media-equivalent class rules exist., Verify no #hex color values appear in the .tcss file. (+20 more)

### Community 61 - "test_tui_file_tree.py"
Cohesion: 0.07
Nodes (26): _FakeProc, anyio, Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)., test_git_tree_decorates_file_labels(), test_normalize_status_code(), test_parse_git_status_porcelain_basic(), test_parse_git_status_porcelain_quoted_path(), test_parse_git_status_porcelain_rename_takes_destination() (+18 more)

### Community 62 - "ToolCallCard"
Cohesion: 0.29
Nodes (4): ComposeResult, Container, A status-aware tool call card.      Header shows the risk-tier icon, tool name,, ToolCallCard

### Community 63 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 64 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 65 - "SelectiveCompressor"
Cohesion: 0.15
Nodes (10): Pattern, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing., Legacy heuristic — only used when no tokenizer is injected., Determine compression level based on turn position from the end., FIX 2: Remove whitespace/noise then TOKEN-TRUNCATE to compact_budget.          T, Compress a list of message dicts with progressive levels.          Args:, Build a compressed context string within token budget.          Uses the real to (+2 more)

### Community 66 - "SelectiveCompressor"
Cohesion: 0.12
Nodes (13): _is_valid_decision(), Filter out empty, generic, or noisy session summary strings., Load persistent project memory (.context-memory.json) into L0 working state., CompressionConfig, Pattern, Progressive compression that preserves semantic meaning.      Strategy:     - Re, Compress a list of messages using progressive levels., SelectiveCompressor (+5 more)

### Community 67 - "unified.py"
Cohesion: 0.17
Nodes (12): Run an async coroutine safely regardless of whether an event loop is already run, _run_async(), create_unified_registry(), Any, Robustly parses tool calls from text.         Supports:           1. JSON format, A single registry for ALL tools and skills.     Bridges the gap between core too, Synchronous wrapper for execute_skill., Unified execution bridge.         Routes to core tools or external skills as app (+4 more)

### Community 68 - "Architecture"
Cohesion: 0.15
Nodes (12): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Rules, Commands, Context Budget Breakdown, Development (+4 more)

### Community 69 - "OllamaClient"
Cohesion: 0.22
Nodes (3): OllamaClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.

### Community 70 - "test_code_quality_harness.py"
Cohesion: 0.07
Nodes (46): Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_compile_gate_rejects_return_outside_function(), test_detect_stubs(), test_detect_symptom_patching() (+38 more)

### Community 71 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 72 - "test_phase_detection.py"
Cohesion: 0.21
Nodes (13): _make_session(), Create a StreamingChatSession with mocked heavy dependencies., Troubleshoot wins over code when both signals are present., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., test_detect_chat_phase(), test_detect_code_phase(), test_detect_phase_empty_input() (+5 more)

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
Nodes (12): Architecture Overview, Auto-tuning, CLI Integration, Configuration Commands, Configuration Commands, `.context-memory.json` Schema, File Locations, Memory System Deep Dive (+4 more)

### Community 78 - "ProjectMemory"
Cohesion: 0.15
Nodes (7): ProjectMemory, MemoryObject, SessionState, SessionPersistence, Infer the current agent phase from user input and the last model response., Auto-switch inference parameters based on detected phase., setter

### Community 79 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

### Community 81 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

### Community 82 - "CenterEmptyState"
Cohesion: 0.12
Nodes (8): Global key bindings that aren't caught by specific widgets.          Key contrac, CenterEmptyState, Container, Pressed, CenterEmptyState — the welcome / idle screen shown in the editor pane.  Replaces, Switch displayed content based on connection state., Route chip buttons to app-level actions., Full-pane empty state widget for the editor / center area.      Mount this insid

### Community 83 - "setup_optimized.sh"
Cohesion: 0.60
Nodes (3): info(), ok(), setup_optimized.sh script

### Community 84 - "tui_app.py"
Cohesion: 0.07
Nodes (28): Unified system prompts for Torchlight.  Single source of truth for all frontends, Remove raw tool payload dumps (Params:, Result:, Writing code to file: ...) from, sanitize_assistant_text(), fetch_provider_models(), Query an OpenAI-compatible /models endpoint (LM Studio, Ollama, llama.cpp)     a, create_client(), load_last_state(), main() (+20 more)

### Community 85 - "run.sh"
Cohesion: 0.40
Nodes (4): COLORTERM, PYTHONPATH, run.sh script, TERM

### Community 86 - "prompts/__init__.py"
Cohesion: 0.43
Nodes (5): build_tool_syntax_prompt(), get_tool_syntax_for_context_size(), Tool syntax instructions for Torchlight.  Generates the appropriate tool calling, Build the complete tool syntax prompt for the system message.      Args:, Return the tool calling syntax instructions appropriate for the model's context

### Community 87 - "tui.sh"
Cohesion: 0.40
Nodes (5): cleanup(), COLORTERM, PYTHONPATH, tui.sh script, TERM

### Community 94 - "test_tui_tabbed_editor.py"
Cohesion: 0.13
Nodes (15): anyio, Tests for Phase-5 tabbed editor split pane (open_file_tab, dirty marker, keyboar, test_close_file_tab_removes_from_open_tabs(), test_close_file_tab_switches_active_tab(), test_dirty_marker_not_set_for_non_tab_file(), test_dirty_marker_set_on_write_step(), test_editor_split_pane_composes(), test_get_tab_hash() (+7 more)

### Community 104 - "test_grammar_parse.py"
Cohesion: 0.11
Nodes (29): _code_lines(), _grammar_text(), _grammar_tool_names(), _parse_rules(), Regression guard for the TurboQuant GBNF grammar-parser incompatibility.  The Tu, Return ``body`` up to (but not including) a top-level '#' comment,     ignoring, Map rule name -> raw (comment-stripped) rule body., TurboQuant parser rejects rule continuations that START with '|'. (+21 more)

### Community 105 - "Console"
Cohesion: 0.24
Nodes (7): Console, test_render_task_progress_empty(), test_render_task_progress_with_tasks(), test_action_entry_markup_safety(), test_action_tracker_print_action_safety(), test_escape_raw_brackets_and_json(), test_tui_markup_escaping_safety()

### Community 106 - "Context Manager CLI"
Cohesion: 0.20
Nodes (9): Architecture, CLI Options, Commands (in CLI), Context Manager CLI, Features, How It Works, Installation, Requirements (+1 more)

### Community 107 - "Torchlight — Terminal AI Coding Agent"
Cohesion: 0.18
Nodes (11): Architecture, CLI Commands, Core Flow, Development, Error Handling, Key Features, Memory Files, Module Structure (+3 more)

### Community 108 - "test_tui_tool_cards.py"
Cohesion: 0.23
Nodes (12): anyio, Tests for Phase-2 tool call cards (risk badge, status, timing, sections)., The streamed <tool_call> mounts a pending card completed by the step., test_app_pending_card_wiring(), test_tool_card_complete_denied(), test_tool_card_complete_error_expands(), test_tool_card_complete_ok(), test_tool_card_composes_with_header() (+4 more)

### Community 110 - ".build"
Cohesion: 0.18
Nodes (7): Any, Path, Scan project files incrementally using st_mtime and construct/update the AST gra, Parse file via Tree-Sitter when tree_sitter library is installed., Perform an incremental O(1) AST update for a single modified file., Remove all nodes and edges referencing a deleted file., Save graph data to JSON and markdown report.

### Community 111 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 112 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 113 - "Static"
Cohesion: 0.11
Nodes (12): ComposeResult, ComposeResult, ComposeResult, ComposeResult, ComposeResult, Flip the most recent pending dot to a terminal status., Remove all dots (called on transcript clear/reset)., Vertical spine of tool-outcome dots next to the transcript.      ``add_pending`` (+4 more)

### Community 114 - "SymbolIndex"
Cohesion: 0.15
Nodes (9): BeamResult, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build() (+1 more)

### Community 115 - "ConnectionPill"
Cohesion: 0.18
Nodes (7): ConnectionPill, ComposeResult, Horizontal, Pressed, ConnectionPill — compact header widget showing live model/server status.  Replac, Compact connection status pill for the top HUD header.      Usage in compose()::, Update the pill's connected state and model name.

### Community 116 - "test_tui_theme.py"
Cohesion: 0.18
Nodes (15): _make_app(), anyio, Tests for Phase-6 theme consistency and responsive layout classes.  Covers: - CS, Ensure CSS doesn't contain hardcoded hex colors., Ensure CSS uses theme variables like $background., Ensure CSS has rules for responsive terminal classes., Responsive classes are applied when terminal is narrow., Short-terminal class applied when height < 24. (+7 more)

### Community 117 - "Resource-Adaptive Features"
Cohesion: 0.29
Nodes (7): Compression Cooldown, Embedding Cache, LLM State Extraction, Resource-Adaptive Configuration, Resource-Adaptive Features, Resource Tiers, Tool Result Budget

### Community 118 - "mark_task_status"
Cohesion: 0.15
Nodes (12): test_mark_task_status_preserves_markdown(), _commit_edit_and_format_result(), get_active_task_description(), _is_task_match(), mark_task_in_progress(), mark_task_status(), _patch_plan_checkbox(), Retrieve the title/description of the current active (in_progress) task, or firs (+4 more)

### Community 119 - "test_tool_parser.py"
Cohesion: 0.07
Nodes (43): Unit tests for core/tools/parser.py tolerant tool parser & fuzzy repair engine., test_extract_balanced_json_object(), test_parse_tool_call_payload(), test_repair_unclosed_action_tags(), test_repair_unclosed_tool_call_tag(), test_single_quoted_dict_parsing(), test_strip_interleaved_prose(), test_strip_thinking_tags() (+35 more)

### Community 123 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 124 - "on"
Cohesion: 0.06
Nodes (14): DirectorySelected, FileSelected, NodeSelected, FileActionModal, FolderPickerModal, on, Pressed, Selected (+6 more)

### Community 125 - "TieredMemory"
Cohesion: 0.07
Nodes (44): ContextSnapshot, MemoryConfig, Calculate remaining token budget headroom before reaching max_tokens threshold., Predict likely next tools based on current state., Tiered memory system with L0-L3 hierarchy:     - L0: Active prompt (current cont, Return list of (path, content) for pinned files., TieredMemory, Unit tests for Tree-of-Thoughts / Branching Evaluator in AutonomousHarness. (+36 more)

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
Cohesion: 0.14
Nodes (17): Unit tests for core/tools/dedup.py argument normalization & TrajectoryLock., test_compute_payload_hash(), test_normalize_tool_args(), test_trajectory_lock(), test_trajectory_lock_error_feedback(), compute_payload_hash(), normalize_tool_args(), Any (+9 more)

### Community 133 - "test_plan_execution_loop.py"
Cohesion: 0.17
Nodes (21): test_auto_mark_does_not_complete_stub_or_missing_file(), test_auto_mark_does_not_overmark_unrelated_tasks(), test_auto_mark_matches_target_files_exact_basename(), test_auto_mark_multi_file_task_in_progress(), test_auto_mark_no_false_positive_substring(), test_auto_mark_pending_task_becomes_in_progress_without_verification(), test_auto_mark_task_completed_by_file(), test_get_workspace_pending_tasks_goal_spec() (+13 more)

### Community 134 - "TestResult"
Cohesion: 0.24
Nodes (6): Path, Run fast pre-flight auto-fixer/linter on modified files before test execution., Detect and run the project's test suite or web inspector., TestResult, Quiet runners (e.g. `pytest -q`) produce no per-test markers; exit code     must, test_all_passed_uses_exit_code()

### Community 135 - "Android Troubleshoot — Routing Layer"
Cohesion: 0.50
Nodes (3): Android Troubleshoot — Routing Layer, Step 1 — Call the tool, Step 2 — Read ONE reference file only if deeper guidance is needed

### Community 136 - "Memory Tiers"
Cohesion: 0.50
Nodes (4): Disk Tiers (ProjectMemory), In-Memory Tiers (TieredMemory.messages), Memory Tiers, Session State Tiers

### Community 137 - "Persistence"
Cohesion: 0.50
Nodes (4): Loading Session State, Persistence, Project Memory Persistence, Session Persistence

### Community 138 - ".load"
Cohesion: 0.18
Nodes (6): Load graph from JSON file if available., Search nodes matching search_term. Returns code snippets alongside names., Read a short code snippet from disk for a matched node., Find relationship path between source and target symbols., Extract connected subgraph centered at symbol or file path., Return structured summary of files, classes, and function signatures.

### Community 139 - "CloudClient"
Cohesion: 0.21
Nodes (6): CloudClient, Sanitize message roles. Convert system role to user role for models (e.g. Gemma, Async streaming implementation required by LLMClient protocol., Return the ids of models the provider currently reports as available.         Us, Resolve requested self.model against live models to prevent 404 mismatches., _sanitize_messages_for_cloud()

### Community 140 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 148 - "test_prompts_and_memory.py"
Cohesion: 0.08
Nodes (28): calculate_in_memory_diff(), extract_modified_symbols(), is_valid_file_path(), Explicitly record a modified file, Net Delta line stats, and touched symbols in, Explicitly record a read file in session state if it is a valid file path., Validate if a string is a genuine file path rather than code attribute access (e, Calculate exact lines added and deleted between two string buffers in RAM., Extract function/class AST symbol names modified or added between old and new te (+20 more)

### Community 149 - "TaskSpec"
Cohesion: 0.11
Nodes (11): GoalSpec, Path, Ensure a goal spec exists on disk in .torchlight, initializing a default workspa, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks., Construct inter-task memory prompt summarizing prior verified tasks and dependen, Run a single micro-epoch for a target task., Tree-of-Thoughts / Branching Evaluator: evaluate candidate implementation option (+3 more)

### Community 150 - "autonomous_harness.py"
Cohesion: 0.13
Nodes (17): Re-export ExecutionFeedbackLoop and TestRunResult from shared core library core., Execution feedback loop for Torchlight., Enum, str, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, TaskStatus, Enum, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an (+9 more)

### Community 151 - "_load_goal_spec"
Cohesion: 0.24
Nodes (8): test_auto_mark_task_completed_triggers_verification(), _clean_task_text(), _load_goal_spec(), Load goal_spec.json; returns None if missing or invalid., Normalize task text by stripping list bullets, numbers, markdown formatting, and, build_task_tree_markup(), TaskTreeWidget: High-performance, non-blocking task tree widget for Torchlight T, Build Rich-markup formatted text representation of workspace tasks.

### Community 152 - "context_manager/prompts.py"
Cohesion: 0.29
Nodes (4): verify_cli_prompt(), build_default_system_prompt(), Torchlight prompt stack — single source of truth.  V2: Optimized for local LLMs, Build system prompt. Use V2 for small contexts.

### Community 153 - "Plan: Non-Security Improvements"
Cohesion: 0.17
Nodes (11): Decisions, Out of Scope, Plan: Non-Security Improvements, Task 1: Frontend Consolidation, Task 2: Split `implementations.py` into Sub-Modules, Task 3: Cache `SymbolIndex` Across Micro-Epochs, Task 4: Extract Tool Execution Pipeline, Task 5: Fix Error Handling Gaps (+3 more)

### Community 154 - "context_manager/memory/embeddings.py"
Cohesion: 0.21
Nodes (9): build_embedder(), Embedder, FallbackEmbedder, HashEmbedder, _normalize(), ProviderEmbedder, any, Protocol (+1 more)

### Community 156 - "classify_command"
Cohesion: 0.27
Nodes (10): test_classify_unknown_command(), test_classify_confirm_commands(), test_classify_destructive_commands(), test_classify_empty_command(), test_classify_safe_commands(), test_classify_unknown_defaults_to_confirm(), test_classify_whitespace_handling(), classify_command() (+2 more)

### Community 157 - "IndexVisitor"
Cohesion: 0.27
Nodes (4): index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings.

### Community 158 - ".complete"
Cohesion: 0.20
Nodes (5): test_summarize_args(), Refresh the elapsed counter while the tool is still running., Flip the card from running to done and fill params + output.          Re-derives, Compact key/value summary of tool args (path, cmd, query, ...)., summarize_args()

### Community 159 - "DirectiveTracker"
Cohesion: 0.16
Nodes (9): DirectiveTracker, Any, Directive tracker and constraint violation reinforcement module for Torchlight., Record a directive violation (e.g. 'cd_command', 'test_assertion_delete'), Reset violation counts., Tracks model constraint violations during execution turns and dynamically     in, Unit tests for CRITICAL_DIRECTIVES system prompt lock and DirectiveTracker., test_critical_directives_in_system_prompt() (+1 more)

### Community 160 - "normalize_model_name"
Cohesion: 0.33
Nodes (8): test_list_available_models_includes_gemma4e4b(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), test_normalize_mlx_gemma_4_4e4b(), list_available_models(), normalize_model_name(), Normalize model alias names (e.g. 'gemma-2-2b', 'qwen', 'gemma 4 E2B', 'gemma 4, Scan local models directory and returns available GGUF and MLX models.

### Community 161 - "Flashlight"
Cohesion: 0.26
Nodes (4): _beam_config_for_context(), Flashlight, FileEntry, SymbolIndex

### Community 162 - "PromptTextArea"
Cohesion: 0.12
Nodes (8): ContextFileAttached, PromptTextArea, Message, TextArea whose Enter submits instead of inserting a newline.      Hooks ``update, Posted when the user presses Enter with no active suggestion., Posted when the user accepts an @file suggestion., SubmitRequested, TextArea

### Community 163 - "Plan: UI Improvements — Torchlight Codex IDE"
Cohesion: 0.18
Nodes (10): Decisions, Effort & Sequencing, Non-Goals, Plan: UI Improvements — Torchlight Codex IDE, Task 1: Fix Latent Bugs (prerequisite), Task 2: Phase 5 — Tabbed Editor Split Pane, Task 3: Phase 6a — Accessibility & Focus Management, Task 4: Phase 6b — Performance & Streaming Polish (+2 more)

### Community 164 - "opencode.json"
Cohesion: 0.50
Nodes (3): plugin, $schema, .opencode/plugins/graphify.js

### Community 165 - ".__init__"
Cohesion: 0.40
Nodes (3): _beam_budget(), Estimate tokens consumed by system prompt, tools, and flashlight beam., Return (max_beam_files, max_lines_per_file) for the given context size.

### Community 167 - "get_tool_registry"
Cohesion: 0.08
Nodes (33): test_search_ast_schema_validation(), test_game_tools_registered(), Tests for performance and accuracy optimizations in Torchlight., test_batch_tool_execution(), test_inline_syntax_guardrail(), test_symbol_index_mtime_cache(), test_get_tool_registry(), test_tool_registry_preview_dry_run() (+25 more)

### Community 168 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

### Community 169 - "ExecutionFeedbackLoop"
Cohesion: 0.08
Nodes (30): ExecutionFeedbackLoop, extract_surgical_traceback(), Auto-run tests and web outcome inspection after code changes and inject feedback, Called after a tool is executed. Returns test results if tests were run., Freshly verify any modified-but-unverified files and return True if         ever, Fetch speculative background test result if running, else execute tests synchron, Convert current failing TestRunResult into a structured TestFailureError for Rec, Build feedback context string for the LLM with surgical error injection. (+22 more)

### Community 170 - "MyCustomSkill"
Cohesion: 0.33
Nodes (3): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi

### Community 171 - "test_tui_trajectory_rail.py"
Cohesion: 0.24
Nodes (9): anyio, Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)., The streamed <tool_call> adds a dot; the completing step flips it., test_app_pending_step_updates_rail(), test_rail_add_pending_and_complete_ok(), test_rail_clear_removes_dots(), test_rail_complete_error_and_denied(), test_rail_complete_without_pending_is_noop() (+1 more)

### Community 173 - "core/api/lmstudio.py"
Cohesion: 0.40
Nodes (4): Re-export LMStudioClient from shared core library core.api.lmstudio., get_phase_inference_params(), LM Studio REST client.  Recovered from the original CLI implementation (commit f, Return the inference parameters preset for a named phase.

### Community 174 - "discovery.py"
Cohesion: 0.21
Nodes (12): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+4 more)

### Community 175 - "tool_card.py"
Cohesion: 0.33
Nodes (6): test_risk_for_tool(), classify_tool(), Classify a tool call into AUTO, CONFIRM, or REVIEW risk tier., Tool call cards for the Torchlight TUI.  Phase 2 of the UI-improvements plan: ev, Risk tier for a tool call, mirroring the shared classification module., risk_for_tool()

### Community 176 - "sync_workspace_tasks"
Cohesion: 0.27
Nodes (10): test_add_subtask_survives_sync_and_lands_in_plan(), test_sync_preserves_stable_ids_and_fields_across_reorder(), test_sync_workspace_tasks_populates_tasks_md(), test_update_task_graph_syncs_plan(), UPDATE_TASK_GRAPH — dynamically mutate sub-tasks in .torchlight/goal_spec.json., tool_update_task_graph_impl(), Generate a collision-free stable task id (never index-based)., Synchronize the canonical goal_spec.json with the plan/task markdown views. (+2 more)

### Community 177 - "test_tui_diff_view.py"
Cohesion: 0.12
Nodes (28): anyio, Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)., A pre-write snapshot (from approval) wins over the already-written disk state., The engine's own CODE_FILE_WRITE approval path is diffable too., The approval modal shows a DIFF PREVIEW section when entries exist., test_approval_modal_omits_diff_when_empty(), test_approval_modal_renders_diff(), test_build_diff_preview_code_file_write() (+20 more)

### Community 178 - "implementations.py"
Cohesion: 0.06
Nodes (59): Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Th, test_set_ctx_window(), test_tool_context_window_scaling(), _ddg_search(), _detect_doc_source(), _extract_identifiers(), _extract_symbols(), _git_run() (+51 more)

### Community 179 - "TestApp"
Cohesion: 0.28
Nodes (5): App, ComposeResult, on, Pressed, TestApp

### Community 180 - "dashboard.py"
Cohesion: 0.33
Nodes (3): _ActionContext, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 181 - "test_goal_mode_process.py"
Cohesion: 0.40
Nodes (4): Verify Goal mode detects missing implementation_plan.md and forces 'plan' phase., Verify bare JSON tool calls without <tool_call> tags are correctly parsed as too, test_detect_phase_goal_mode_missing_plan_forces_plan(), test_parse_response_bare_json_tool_call()

### Community 182 - "._append_message"
Cohesion: 0.10
Nodes (13): Message, MessageRole, Register a callback for memory events (MESSAGE_ADDED, PIN_ADDED, COMPACTION_TRIG, Unregister a memory event callback., Dispatch a memory event to registered listeners safely., Reactive event-driven compaction trigger. Automatically runs when token ratio cr, Update or set the primary system prompt (first system message in history)., Remove all pinned files. (+5 more)

### Community 183 - "_clean_and_parse_json"
Cohesion: 0.50
Nodes (3): test_clean_and_parse_json_tolerant_multiline_content(), test_clean_and_parse_json_trailing_unterminated_string(), _clean_and_parse_json()

### Community 184 - "Token Budget"
Cohesion: 0.67
Nodes (3): Allocation for 4k Context, Auto-tuned Budgets by Context Size, Token Budget

### Community 188 - "._stream_llm_with_retry"
Cohesion: 0.17
Nodes (6): Notify listeners of real-time background status and action telemetry., Notify listeners (dashboard/TUI) that task state changed after a tool call., Re-append closing tags that were consumed as stop tokens by llama-server., Stream LLM response token-by-token cleanly without thread deadlocks., True when an LLM error string looks like a transient server stall that         a, Stream an LLM response, retrying up to ``retries`` times on transient         se

### Community 191 - "asyncio"
Cohesion: 0.15
Nodes (6): asyncio, App, ComposeResult, TestApp, App, TestApp

## Knowledge Gaps
- **341 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `context-manager-cli`, `run.sh script`, `COLORTERM` (+336 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RLMEngineOptimized` connect `RLMEngineOptimized` to `context_manager/memory/models.py`, `TrajectoryLock`, `test_plan_execution_loop.py`, `ToolRegistry`, `repl_sandbox.py`, `LlamaCppClient`, `test_resizer.py`, `ensure_project_initialized`, `rlm_engine_optimized.py`, `test_tui_plan_panel.py`, `DebateVerifier`, `TorchlightApp`, `ContextBudget`, `PaneResizer`, `main_optimized.py`, `ExecutionFeedbackLoop`, `test_tui_trajectory_rail.py`, `.has_failing_tests`, `MessageCard`, `core/memory/manager.py`, `test_tui_diff_view.py`, `ProjectMemory`, `test_goal_mode_process.py`, `test_execution_mode_normalization_and_sync`, `.set_execution_mode_callback`, `._stream_llm_with_retry`, `ProjectMemory`, `tui_app.py`, `test_tui_tabbed_editor.py`, `test_tui_tool_cards.py`, `test_tool_parser.py`, `on`, `TieredMemory`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `TorchlightApp` connect `TorchlightApp` to `LlamaCppClient`, `test_resizer.py`, `CloudClient`, `test_tui_plan_panel.py`, `RLMEngineOptimized`, `PromptTextArea`, `PaneResizer`, `test_tui_trajectory_rail.py`, `AutonomousHarness`, `MessageCard`, `test_tui_diff_view.py`, `test_tui_accessibility.py`, `ToolCallCard`, `OllamaClient`, `CenterEmptyState`, `tui_app.py`, `test_tui_tabbed_editor.py`, `test_tui_tool_cards.py`, `Static`, `ConnectionPill`, `test_tui_theme.py`, `on`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `TieredMemory` connect `TieredMemory` to `test_plan_execution_loop.py`, `LlamaCppClient`, `rlm_engine_optimized.py`, `test_prompts_and_memory.py`, `TaskSpec`, `autonomous_harness.py`, `StreamingChatSession`, `cli/main.py`, `RLMEngineOptimized`, `.__init__`, `ContextBudget`, `AutonomousHarness`, `core/memory/manager.py`, `._append_message`, `task_helpers.py`, `tool_edit_file_impl`, `core/memory/persistence.py`, `SelectiveCompressor`, `ProjectMemory`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `TorchlightApp` (e.g. with `_StubClient` and `AutonomousHarness`) actually correct?**
  _`TorchlightApp` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `TieredMemory` (e.g. with `StreamingChatSession` and `AutonomousHarness`) actually correct?**
  _`TieredMemory` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `RLMEngineOptimized` (e.g. with `ConversationSummarizer` and `Message`) actually correct?**
  _`RLMEngineOptimized` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `MemoryConfig` (e.g. with `StreamingChatSession` and `ContextBudget`) actually correct?**
  _`MemoryConfig` has 21 INFERRED edges - model-reasoned connections that need verification._