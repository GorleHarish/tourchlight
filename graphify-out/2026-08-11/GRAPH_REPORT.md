# Graph Report - tourchlight v1_i6  (2026-08-11)

## Corpus Check
- 233 files · ~177,102 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3551 nodes · 7299 edges · 187 communities (169 shown, 18 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 660 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `363fe600`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_tui_command_palette.py
- context-manager-cli/tests/test_models.py
- ProjectSnapshot
- SymbolIndex
- registry.py
- BaseSkill
- LMStudioClient
- TokenCounter
- REPLSandbox
- CommandPalette
- test_resizer.py
- StructurePreservingHTMLParser
- RecoveryEngine
- test_implementations.py
- HtmlGamePlayer
- ActionTracker
- TrajectoryLogger
- InferenceParams
- ProjectMemory
- get_phase_system_prompt
- android_ref_build.md
- core.py
- test_tui_plan_panel.py
- PlanningSkill
- ContextDashboard
- DebateVerifier
- config.py
- StreamingChatSession
- mark_task_status
- LLMClient
- Changelog
- RLMEngineOptimized
- PyASTVisitor
- context_manager/compression/summarizer.py
- TorchlightApp
- android_ref_runtime.md
- VerbatimCompactor
- UnifiedSkillRegistry
- context_manager/memory/persistence.py
- TaskDAG
- PaneResizer
- main_optimized.py
- TDDSkill
- Issues Found
- android_ref_emulator.md
- AgentStatusModal
- MessageCard
- validate_tool_call
- VerbatimCompactor
- core/memory/manager.py
- ProjectMemory
- test_tui_status_bar.py
- SkillResult
- test_surgical_task_verification.py
- ._stream_llm_with_retry
- cli/main.py
- Torchlight Architecture
- tool_edit_file_impl
- ProjectGraph
- MemoryObject
- test_tui_accessibility.py
- ApprovalModal
- Static
- TDDSkill
- android_ref_adb.md
- test_inline_interception.py
- context_manager/memory/manager.py
- test_tui_tool_cards.py
- Architecture
- RLMEngine
- test_code_quality_harness.py
- prompts_minimal.py
- test_phase_detection.py
- android_ref_signing.md
- Prompt Templates for 7B Coder Models
- Torchlight Excellence Roadmap
- Checklist
- Memory System Deep Dive
- CenterEmptyState
- Execution Feedback Loop
- start_optimized_local.sh
- test_ast_tool.py
- setup_optimized.sh
- tui_app.py
- run.sh
- test_prompts_and_memory.py
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- .format_l0_scratchpad
- context-manager-cli
- torchlight-core
- test_grammar_parse.py
- Console
- Context Manager CLI
- Torchlight — Terminal AI Coding Agent
- ._parse_response
- .agents/AGENTS.md
- .build
- Data Flow
- Core Classes
- Step
- SymbolIndex
- ConnectionPill
- test_tui_theme.py
- Resource-Adaptive Features
- task_helpers.py
- rlm_engine_optimized.py
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
- test_autonomous_harness_pipeline.py
- Android Troubleshoot — Routing Layer
- Memory Tiers
- Persistence
- .load
- WebOutcomeInspector
- Retrieval System
- ~350 tokens. Do NOT load other reference files in the same turn.
- Profile: Run -> Profile app -> Memory tab
- at android.app.Activity...          <- framework — ignore
- StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
- Context null in Fragment -> requireContext() (throws if detached, which is correct)
- implementation 'androidx.multidex:multidex:2.0.1'
- Never use StrictMode.allowThreadDiskReads() — it masks the bug
- test_tui_trajectory_rail.py
- AutonomousHarness
- prompts/__init__.py
- _load_goal_spec
- context_manager/prompts.py
- Plan: Non-Security Improvements
- context_manager/memory/embeddings.py
- context_manager/memory/models.py
- test_tui_file_tree.py
- system.py
- CalculatorSkill
- .load_project_memory
- ContextBudget
- Flashlight
- PromptTextArea
- Plan: UI Improvements — Torchlight Codex IDE
- opencode.json
- graphify.js
- HTMLGameSkill
- ExecutionFeedbackLoop
- MyCustomSkill
- llamacpp_client.py
- core/api/lmstudio.py
- discovery.py
- sync_workspace_tasks
- test_tui_diff_view.py
- implementations.py
- TestApp
- ._append_message
- .__init__
- Schema Reference
- .memory
- TestApp
- tui_widgets/__init__.py
- TestApp

## God Nodes (most connected - your core abstractions)
1. `TorchlightApp` - 168 edges
2. `TieredMemory` - 147 edges
3. `RLMEngineOptimized` - 93 edges
4. `MemoryConfig` - 83 edges
5. `AutonomousHarness` - 63 edges
6. `ExecutionFeedbackLoop` - 53 edges
7. `LlamaCppClient` - 45 edges
8. `StreamingChatSession` - 41 edges
9. `CloudClient` - 39 edges
10. `Step` - 38 edges

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

## Communities (187 total, 18 thin omitted)

### Community 0 - "test_tui_command_palette.py"
Cohesion: 0.06
Nodes (34): Binding, Changed, anyio, Tests for Phase-4 command palette + prompt autocomplete., test_build_palette_items_kinds_and_visibility(), test_command_palette_composes_filters_and_selects(), test_command_palette_enter_runs_highlighted_item(), test_fuzzy_filter_empty_query_and_no_match() (+26 more)

### Community 1 - "context-manager-cli/tests/test_models.py"
Cohesion: 0.15
Nodes (14): ContentChunk, MemoryNeedle, MemoryObject, WorkingSetSnapshot, SessionState, test_content_chunk_custom(), test_content_chunk_defaults(), test_memory_needle_custom() (+6 more)

### Community 2 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 3 - "SymbolIndex"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 4 - "registry.py"
Cohesion: 0.05
Nodes (42): Return True if the most recent test run actually ran and has failing or, test_game_tools_registered(), test_edit_file_tail_ultra_compact_directive(), test_identical_old_new_text_preflight(), test_schema_target_alias_no_collision(), test_trajectory_lock_window_and_read_only_rate_limiting(), test_validate_and_repair_compact_json_errors(), test_whitespace_stripped_preflight() (+34 more)

### Community 5 - "BaseSkill"
Cohesion: 0.10
Nodes (18): ABC, BaseSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, MarkdownDocumentSkill, Skills — external / plugin capabilities.  Skills are DIFFERENT from core tools: (+10 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.14
Nodes (8): _friendly_timeout_msg(), LMStudioClient, Synchronous streaming generator — yields tokens one-by-one.          Uses DEFAUL, Async streaming generator. Uses per-chunk read timeout (DEFAULT_TIMEOUT)., Simple synchronous query interface (LLMClient protocol compatibility)., Return a human-readable message explaining which part of the request timed out., Timeout, TimeoutException

### Community 7 - "TokenCounter"
Cohesion: 0.07
Nodes (32): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing. (+24 more)

### Community 8 - "REPLSandbox"
Cohesion: 0.08
Nodes (31): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+23 more)

### Community 9 - "CommandPalette"
Cohesion: 0.11
Nodes (9): NamedTuple, AgentMemoryWidget, Displays the live L0 Agent Brain Scratchpad., AttachContextModal, CommandPalette, PaletteResult, Command palette + slash-command autocomplete for the Torchlight TUI.  Phase 4: *, Ctrl+P modal: fuzzy-search actions, slash commands, and files. (+1 more)

### Community 10 - "test_resizer.py"
Cohesion: 0.26
Nodes (14): _build_app(), _click_resizer(), _drag_resizer(), Regression tests for the PaneResizer drag/click resizing in tui_app.py.  The Pan, No-op client so the engine never touches LM Studio / Ollama / cloud., Simulate a real drag: mouse_down -> captured MouseMove -> mouse_up., _resize_to(), _start_app() (+6 more)

### Community 11 - "StructurePreservingHTMLParser"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 12 - "RecoveryEngine"
Cohesion: 0.05
Nodes (61): get_recovery_hint(), inject_recovery_into_memory(), Any, Recovery engine for Torchlight errors.  Provides structured recovery strategies, Push recovery hint into memory state's tried_and_failed scratchpad list     to e, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type. (+53 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.08
Nodes (36): test_run_command_intercept_ast_functions(), test_verify_compile_param(), test_edit_file_impl(), test_edit_file_impl_not_found(), test_grep_hyphen_pattern(), test_grep_impl(), test_grep_impl_file_path(), test_grep_impl_no_match() (+28 more)

### Community 14 - "HtmlGamePlayer"
Cohesion: 0.09
Nodes (32): GameInputEvent, GameOutcomeResult, get_process_memory_mb(), HtmlGamePlayer, Path, HTML Game Inspector & Player Harness for Torchlight.  Provides autonomous playin, Autonomous HTML Game Harness & Dynamic Verifier.      Launches an ephemeral brow, Plays the HTML game for duration_ms while simulating inputs and checking frame d (+24 more)

### Community 15 - "ActionTracker"
Cohesion: 0.13
Nodes (10): _ActionContext, ActionEntry, ActionTracker, A single recorded action with its status and elapsed time., Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex (+2 more)

### Community 16 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 17 - "InferenceParams"
Cohesion: 0.08
Nodes (23): detect_model_traits(), InferenceParams, Writing code files. Near-deterministic — exact syntax matters., Reasoning through plans. Moderate creativity. All tools remain available., Detect architecture traits (size, reasoning status) from model name.      Return, Diagnosing errors. Slightly more exploration., General conversation., Dynamically return an InferenceParams preset calibrated for both         the tar (+15 more)

### Community 18 - "ProjectMemory"
Cohesion: 0.08
Nodes (28): ensure_git_repository(), ensure_project_initialized(), init_new_project(), ProjectMemory, MemoryObject, Path, SessionState, Ensure target project directory exists and has a local Git repository initialize (+20 more)

### Community 19 - "get_phase_system_prompt"
Cohesion: 0.09
Nodes (16): DirectiveTracker, Any, Directive tracker and constraint violation reinforcement module for Torchlight., Record a directive violation (e.g. 'cd_command', 'test_assertion_delete'), Reset violation counts., Tracks model constraint violations during execution turns and dynamically     in, get_phase_system_prompt(), Generate phase-tailored system prompt by appending phase instructions, critical (+8 more)

### Community 20 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 21 - "core.py"
Cohesion: 0.08
Nodes (36): CoreToolRegistry, get_core_registry(), Any, Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Th, Compatibility subclass of ToolRegistry providing CLI-specific execute/dangerous_, test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command() (+28 more)

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

### Community 26 - "config.py"
Cohesion: 0.07
Nodes (41): test_list_available_models_includes_gemma4e4b(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), test_normalize_mlx_gemma_4_4e4b(), index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings. (+33 more)

### Community 27 - "StreamingChatSession"
Cohesion: 0.11
Nodes (15): chat(), get_phase_system_prompt(), goal(), Panel, /params                    — show current params         /params auto, Start an interactive chat session with context management and flashlight., Start an autonomous goal execution session driven by .torchlight task tracking., Re-append closing tags and unclosed JSON braces that were consumed as stop token (+7 more)

### Community 28 - "mark_task_status"
Cohesion: 0.15
Nodes (12): test_mark_task_status_preserves_markdown(), _commit_edit_and_format_result(), get_active_task_description(), _is_task_match(), mark_task_in_progress(), mark_task_status(), _patch_plan_checkbox(), Retrieve the title/description of the current active (in_progress) task, or firs (+4 more)

### Community 29 - "LLMClient"
Cohesion: 0.08
Nodes (21): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Send messages and yield response chunks., Check if the backend is reachable., List available models., Simple query interface (for backward compatibility). (+13 more)

### Community 30 - "Changelog"
Cohesion: 0.06
Nodes (30): Added, Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+22 more)

### Community 31 - "RLMEngineOptimized"
Cohesion: 0.09
Nodes (30): Verify Goal mode detects missing implementation_plan.md and forces 'plan' phase., Verify bare JSON tool calls without <tool_call> tags are correctly parsed as too, test_detect_phase_goal_mode_missing_plan_forces_plan(), test_parse_response_bare_json_tool_call(), asyncio, test_ring_buffer_prompt_dedup_skip(), anyio, test_verification_gate_allows_final_answer_when_all_done() (+22 more)

### Community 32 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.19
Nodes (14): DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer, Message (+6 more)

### Community 34 - "TorchlightApp"
Cohesion: 0.04
Nodes (33): asyncio, Tests for TorchlightApp project_root property and task manager modal integration, test_action_task_manager_pushes_screen(), test_torchlight_app_project_root_fallback(), test_torchlight_app_project_root_property(), FileSelected, NodeSelected, is_port_in_use() (+25 more)

### Community 35 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.11
Nodes (15): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, ConversationSummarizer, Message, Summarize conversation turns for compression using high-density structured templ, Generate a high-density structured compaction template preserving key context in (+7 more)

### Community 37 - "UnifiedSkillRegistry"
Cohesion: 0.18
Nodes (9): Run an async coroutine safely regardless of whether an event loop is already run, _run_async(), Any, Robustly parses tool calls from text.         Supports:           1. JSON format, A single registry for ALL tools and skills.     Bridges the gap between core too, Synchronous wrapper for execute_skill., Unified execution bridge.         Routes to core tools or external skills as app, Condensed tool documentation injected into the system prompt.                  U (+1 more)

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
Cohesion: 0.26
Nodes (11): amain(), approval_prompt(), display_step(), get_depth_style(), main(), print_banner(), Step, Interactive approval for CONFIRM/REVIEW tier tools. (+3 more)

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "Issues Found"
Cohesion: 0.12
Nodes (16): 1. **ExecutionMode Enum Mismatch**, 2. **Phase Detection Not Integrated with Goal Mode**, 3. **Goal Spec Initialization Race Condition**, 4. **Missing Verification Gate in CLI Goal Mode**, 5. **AutonomousHarness Not Wired to LLM Engine in CLI**, 6. **Inconsistent ExecutionMode Default**, 7. **Memory State Sync Issues**, Fix Plan (+8 more)

### Community 44 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 46 - "MessageCard"
Cohesion: 0.06
Nodes (33): anyio, Tests for Phase-1 transcript widgets (message cards, streaming, thinking)., Smoke test: the real app mounts MessageCards and drives the streaming view., test_app_transcript_wiring(), test_card_meta_for(), test_estimate_token_count(), test_message_card_composes(), test_streaming_view_updates() (+25 more)

### Community 47 - "validate_tool_call"
Cohesion: 0.11
Nodes (25): test_get_openai_tools_schema(), test_get_schemas_for_phase(), test_registry_get_description_block_phase(), test_validate_tool_call_alias(), test_validate_tool_call_coercion(), test_validate_tool_call_list_dir_optional_path(), test_validate_tool_call_missing_required(), test_validate_tool_call_set_phase() (+17 more)

### Community 48 - "VerbatimCompactor"
Cohesion: 0.14
Nodes (6): CompressionConfig, Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 49 - "core/memory/manager.py"
Cohesion: 0.12
Nodes (28): Conversation Summarizer for Torchlight.  Extracts key information from conversat, Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, ContentChunk, ContentType, ContextSnapshot, ExecutionMode, Message, MessageRole (+20 more)

### Community 50 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 51 - "test_tui_status_bar.py"
Cohesion: 0.16
Nodes (17): anyio, Tests for Phase-4 consolidated status bar (gauge + segments widget)., test_build_status_segments_defaults(), test_build_status_segments_populated(), test_build_status_segments_running_no_tps_yet(), test_build_status_segments_server_offline_and_branch_escape(), test_gauge_markup_clamps_out_of_range(), test_gauge_markup_color_escalation() (+9 more)

### Community 52 - "SkillResult"
Cohesion: 0.23
Nodes (6): Any, ReproSkill, Any, Synchronous wrapper for use from non-async contexts., Trigger real load on first call, then delegate., SkillResult

### Community 53 - "test_surgical_task_verification.py"
Cohesion: 0.20
Nodes (13): Unit tests for Surgical Targeted Task Verification in Torchlight., test_verify_task_preflight_invalid_json(), test_verify_task_preflight_syntax_error(), test_verify_task_preflight_valid_python(), test_verify_task_targeted_command(), _extract_referenced_files(), _find_file_in_project(), Extract distinct code/markup filenames referenced in task description. (+5 more)

### Community 54 - "._stream_llm_with_retry"
Cohesion: 0.17
Nodes (6): Notify listeners of real-time background status and action telemetry., Notify listeners (dashboard/TUI) that task state changed after a tool call., Re-append closing tags that were consumed as stop tokens by llama-server., Stream LLM response token-by-token cleanly without thread deadlocks., True when an LLM error string looks like a transient server stall that         a, Stream an LLM response, retrying up to ``retries`` times on transient         se

### Community 55 - "cli/main.py"
Cohesion: 0.16
Nodes (11): command, compress_file(), count_tokens(), Compress a file using verbatim compaction., Count tokens in text., Manage saved sessions., Lock phase based on concrete execution events., _risk_tier() (+3 more)

### Community 56 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 57 - "tool_edit_file_impl"
Cohesion: 0.12
Nodes (26): test_edit_file_blocks_broken_syntax(), test_tool_edit_file_integration(), Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_auto_fallback_to_write(), test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_line_bounded(), test_edit_file_line_bounded_without_old_text() (+18 more)

### Community 58 - "ProjectGraph"
Cohesion: 0.18
Nodes (20): get_project_graph(), ProjectGraph, Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Get or create the ProjectGraph instance for a given root directory., Incrementally update the AST graph for a single modified file., update_project_graph_file(), Unit tests for incremental O(1) AST graph delta updates. (+12 more)

### Community 59 - "MemoryObject"
Cohesion: 0.10
Nodes (31): build_embedder(), compute_tf_idf_score(), cosine_similarity(), Embedder, HybridEmbedder, HybridMemoryRetriever, _is_low_memory(), KeywordEmbedder (+23 more)

### Community 60 - "test_tui_accessibility.py"
Cohesion: 0.10
Nodes (28): _make_app(), anyio, Tests for Phase-6 accessibility and keyboard navigation.  Covers: - Tab bar keyb, Arrow navigation wraps around at the ends., Arrow keys don't do anything when no tabs are open., Verify :focus rules exist for tab items in the .tcss file., Verify responsive @media-equivalent class rules exist., Verify no #hex color values appear in the .tcss file. (+20 more)

### Community 61 - "ApprovalModal"
Cohesion: 0.17
Nodes (3): ApprovalModal, Production-grade modal dialog for tool & file modification approval., Snapshot file contents *before* a diffable write executes.          ``_handle_st

### Community 62 - "Static"
Cohesion: 0.09
Nodes (14): ComposeResult, ComposeResult, ComposeResult, ComposeResult, ComposeResult, ComposeResult, Trajectory rail for the Torchlight TUI.  Phase 2: a collapsed, status-colored ra, Flip the most recent pending dot to a terminal status. (+6 more)

### Community 63 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 64 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 65 - "test_inline_interception.py"
Cohesion: 0.24
Nodes (11): _looks_like_full_file(), Helper to check if content looks like a complete standalone file rather than a s, MockEngine, Unit tests for inline code interception safety checks, tight regex matching, and, test_detect_phase_prioritizes_write_and_file_extensions(), test_existing_file_partial_snippet_protection(), test_explicit_pre_text_path_declaration_triggers(), test_in_block_comment_header_triggers() (+3 more)

### Community 66 - "context_manager/memory/manager.py"
Cohesion: 0.10
Nodes (23): Re-export TieredMemory and MemoryConfig from shared core library core.memory.man, CompressionConfig, CompressionLevel, Enum, Pattern, Selective Memory Compression — Progressive context reduction for local LLMs.  4-, Progressive compression that preserves semantic meaning.      Strategy:     - Re, Compress a list of messages using progressive levels. (+15 more)

### Community 67 - "test_tui_tool_cards.py"
Cohesion: 0.10
Nodes (20): anyio, Tests for Phase-2 tool call cards (risk badge, status, timing, sections)., test_risk_for_tool(), test_summarize_args(), test_target_from_args_line_ranges(), test_tool_card_complete_denied(), test_tool_card_complete_error_expands(), test_tool_card_complete_ok() (+12 more)

### Community 68 - "Architecture"
Cohesion: 0.15
Nodes (12): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Rules, Commands, Context Budget Breakdown, Development (+4 more)

### Community 69 - "RLMEngine"
Cohesion: 0.20
Nodes (13): Message, test_rlm_engine_solve_method(), display_step(), get_depth_style(), main(), print_banner(), print_help(), Step (+5 more)

### Community 70 - "test_code_quality_harness.py"
Cohesion: 0.07
Nodes (48): Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_compile_gate_rejects_return_outside_function(), test_detect_stubs(), test_detect_symptom_patching() (+40 more)

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
Nodes (12): Allocation for 4k Context, Architecture Overview, Auto-tuned Budgets by Context Size, Auto-tuning, CLI Integration, Configuration Commands, Configuration Commands, File Locations (+4 more)

### Community 78 - "CenterEmptyState"
Cohesion: 0.18
Nodes (7): CenterEmptyState, Container, Pressed, CenterEmptyState — the welcome / idle screen shown in the editor pane.  Replaces, Switch displayed content based on connection state., Route chip buttons to app-level actions., Full-pane empty state widget for the editor / center area.      Mount this insid

### Community 79 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

### Community 81 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

### Community 82 - "test_ast_tool.py"
Cohesion: 0.24
Nodes (11): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_read_symbols_indented_methods_and_duplicate_names(), test_search_ast_action_aliases(), test_search_ast_after_writing_file(), test_search_ast_impl_fallback(), test_search_ast_schema_validation(), test_read_symbols_impl(), READ_SYMBOLS — show file structure without loading content. (+3 more)

### Community 83 - "setup_optimized.sh"
Cohesion: 0.60
Nodes (3): info(), ok(), setup_optimized.sh script

### Community 84 - "tui_app.py"
Cohesion: 0.04
Nodes (47): DirectoryTree, CloudClient, fetch_provider_models(), Query an OpenAI-compatible /models endpoint (LM Studio, Ollama, llama.cpp)     a, LlamaCppClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.          Runs the, create_client() (+39 more)

### Community 85 - "run.sh"
Cohesion: 0.40
Nodes (4): COLORTERM, PYTHONPATH, run.sh script, TERM

### Community 86 - "test_prompts_and_memory.py"
Cohesion: 0.10
Nodes (21): calculate_in_memory_diff(), extract_modified_symbols(), is_valid_file_path(), Explicitly record a modified file, Net Delta line stats, and touched symbols in, Validate if a string is a genuine file path rather than code attribute access (e, Calculate exact lines added and deleted between two string buffers in RAM., Extract function/class AST symbol names modified or added between old and new te, Unit tests for phase-tailored system prompts, anti-symptom-patching rules, and L (+13 more)

### Community 87 - "tui.sh"
Cohesion: 0.40
Nodes (5): cleanup(), COLORTERM, PYTHONPATH, tui.sh script, TERM

### Community 94 - ".format_l0_scratchpad"
Cohesion: 0.12
Nodes (9): Build critical context block from session state., Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length., Return headroom-aware budget allocations for the current turn., Pin a recently-read file slice so it survives compression without bloating conte, Remove a file from pinned memory if deleted or stale., Re-read an edited file from disk and update its pin in memory., Build the message list for the LLM.          Pinned files and dynamic L0 Scratch, Format current SessionState into a dynamic L0 working memory scratchpad. (+1 more)

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

### Community 108 - "._parse_response"
Cohesion: 0.20
Nodes (8): test_clean_and_parse_json_tolerant_multiline_content(), test_clean_and_parse_json_trailing_unterminated_string(), _looks_like_prose_or_outline(), Trim prose a model appended after the file body when </WRITE_FILE> was     consu, Parse the LLM response for action tags.         Returns: (action, thinking, cont, Heuristic gate for inline code interception (step 6b of _parse_response).      R, _trim_trailing_prose(), _clean_and_parse_json()

### Community 110 - ".build"
Cohesion: 0.18
Nodes (7): Any, Path, Scan project files incrementally using st_mtime and construct/update the AST gra, Parse file via Tree-Sitter when tree_sitter library is installed., Perform an incremental O(1) AST update for a single modified file., Remove all nodes and edges referencing a deleted file., Save graph data to JSON and markdown report.

### Community 111 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 112 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 113 - "Step"
Cohesion: 0.10
Nodes (22): A successful WRITE_FILE step mounts a DiffView card with real content., test_app_write_step_renders_diff_card(), anyio, Tests for Phase-5 tabbed editor split pane (open_file_tab, dirty marker, keyboar, test_close_file_tab_removes_from_open_tabs(), test_close_file_tab_switches_active_tab(), test_dirty_marker_not_set_for_non_tab_file(), test_dirty_marker_set_on_write_step() (+14 more)

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

### Community 118 - "task_helpers.py"
Cohesion: 0.15
Nodes (20): test_task_matrix_compress_over_45_percent_context(), test_insert_task_into_plan_section(), Tests for robust task and status tracking in LLM context and TUI., test_compact_task_matrix_adaptive_rendering(), test_status_badges_and_boxes(), test_validate_task_transition(), _file_looks_complete(), get_compact_task_matrix() (+12 more)

### Community 119 - "rlm_engine_optimized.py"
Cohesion: 0.15
Nodes (26): Unit tests for core/tools/parser.py tolerant tool parser & fuzzy repair engine., test_extract_balanced_json_object(), test_parse_tool_call_payload(), test_repair_unclosed_action_tags(), test_repair_unclosed_tool_call_tag(), test_single_quoted_dict_parsing(), test_strip_interleaved_prose(), test_strip_thinking_tags() (+18 more)

### Community 123 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 124 - "on"
Cohesion: 0.07
Nodes (11): DirectorySelected, FileActionModal, FolderPickerModal, on, Pressed, Selected, Submitted, Modal dialog for interactive visual folder selection across the entire computer. (+3 more)

### Community 125 - "TieredMemory"
Cohesion: 0.07
Nodes (43): ContextSnapshot, MemoryConfig, Calculate remaining token budget headroom before reaching max_tokens threshold., Predict likely next tools based on current state., Tiered memory system with L0-L3 hierarchy:     - L0: Active prompt (current cont, Return list of (path, content) for pinned files., TieredMemory, MemoryEventType (+35 more)

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
Cohesion: 0.13
Nodes (20): Unit tests for core/tools/dedup.py argument normalization & TrajectoryLock., test_compute_payload_hash(), test_edit_file_alternate_trajectory_hint(), test_normalize_tool_args(), test_trajectory_lock(), test_trajectory_lock_error_feedback(), compute_payload_hash(), get_alternate_trajectory_hint() (+12 more)

### Community 133 - "test_plan_execution_loop.py"
Cohesion: 0.17
Nodes (21): test_auto_mark_does_not_complete_stub_or_missing_file(), test_auto_mark_does_not_overmark_unrelated_tasks(), test_auto_mark_matches_target_files_exact_basename(), test_auto_mark_multi_file_task_in_progress(), test_auto_mark_no_false_positive_substring(), test_auto_mark_pending_task_becomes_in_progress_without_verification(), test_auto_mark_task_completed_by_file(), test_get_workspace_pending_tasks_goal_spec() (+13 more)

### Community 134 - "test_autonomous_harness_pipeline.py"
Cohesion: 0.52
Nodes (6): create_mock_feedback_loop(), Path, Unit tests for Inter-Task Context Pipeline, Dependencies, and File Collision Gua, test_inter_task_output_summary_injection(), test_target_file_collision_detection(), test_task_dependencies_and_execution_ordering()

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

### Community 139 - "WebOutcomeInspector"
Cohesion: 0.09
Nodes (19): EphemeralHTTPServer, Any, HTMLParser, Path, QuietHTTPRequestHandler, Spins up a lightweight local HTTP server for static file inspection., Tier 1: Static HTML syntax and asset path validator., Main Inspector Subsystem driving zero-memory, ephemeral web verification. (+11 more)

### Community 140 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 148 - "test_tui_trajectory_rail.py"
Cohesion: 0.29
Nodes (7): anyio, Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)., test_rail_add_pending_and_complete_ok(), test_rail_clear_removes_dots(), test_rail_complete_error_and_denied(), test_rail_complete_without_pending_is_noop(), test_rail_prunes_over_max()

### Community 149 - "AutonomousHarness"
Cohesion: 0.09
Nodes (35): AutonomousHarness, GoalSpec, HarnessConfig, Enum, Path, str, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, Ensure target project has local git repository and persistent memory initialized (+27 more)

### Community 150 - "prompts/__init__.py"
Cohesion: 0.43
Nodes (5): build_tool_syntax_prompt(), get_tool_syntax_for_context_size(), Tool syntax instructions for Torchlight.  Generates the appropriate tool calling, Build the complete tool syntax prompt for the system message.      Args:, Return the tool calling syntax instructions appropriate for the model's context

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

### Community 155 - "context_manager/memory/models.py"
Cohesion: 0.12
Nodes (16): _build_excerpt(), LLMStateExtractor, _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa (+8 more)

### Community 156 - "test_tui_file_tree.py"
Cohesion: 0.07
Nodes (26): _FakeProc, anyio, Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)., test_git_tree_decorates_file_labels(), test_normalize_status_code(), test_parse_git_status_porcelain_basic(), test_parse_git_status_porcelain_quoted_path(), test_parse_git_status_porcelain_rename_takes_destination() (+18 more)

### Community 157 - "system.py"
Cohesion: 0.33
Nodes (4): Unified system prompts for Torchlight.  Single source of truth for all frontends, Remove raw tool payload dumps (Params:, Result:, Writing code to file: ...) from, sanitize_assistant_text(), Apply any pending streaming text that was throttled.

### Community 158 - "CalculatorSkill"
Cohesion: 0.40
Nodes (3): CalculatorSkill, Evaluate a mathematical expression safely using Python's AST., expr

### Community 159 - ".load_project_memory"
Cohesion: 0.50
Nodes (3): _is_valid_decision(), Filter out empty, generic, or noisy session summary strings., Load persistent project memory (.context-memory.json) into L0 working state.

### Community 160 - "ContextBudget"
Cohesion: 0.10
Nodes (12): _clamp(), ContextBudget, Adaptive, headroom-driven context budget coordinator for Torchlight.  Static res, Token reserve kept for the recent-message window., Current fraction of the target window in use., Effective budget allocations for the current turn.      `used_tokens` is the liv, Token allowance for the L0 working memory scratchpad this turn., Max characters per scratchpad entry (longer when headroom is ample). (+4 more)

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

### Community 168 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

### Community 169 - "ExecutionFeedbackLoop"
Cohesion: 0.06
Nodes (43): Re-export ExecutionFeedbackLoop and TestRunResult from shared core library core., Execution feedback loop for Torchlight., ExecutionFeedbackLoop, extract_surgical_traceback(), Enum, Path, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Auto-run tests and web outcome inspection after code changes and inject feedback (+35 more)

### Community 170 - "MyCustomSkill"
Cohesion: 0.33
Nodes (3): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi

### Community 171 - "llamacpp_client.py"
Cohesion: 0.32
Nodes (4): _context_limit_message(), Ensure strict role alternation (user, assistant...) and merge consecutive same-r, Friendly remediation for llama-server 'context exceeded' errors., _sanitize_messages()

### Community 173 - "core/api/lmstudio.py"
Cohesion: 0.40
Nodes (4): Re-export LMStudioClient from shared core library core.api.lmstudio., get_phase_inference_params(), LM Studio REST client.  Recovered from the original CLI implementation (commit f, Return the inference parameters preset for a named phase.

### Community 174 - "discovery.py"
Cohesion: 0.21
Nodes (12): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+4 more)

### Community 176 - "sync_workspace_tasks"
Cohesion: 0.27
Nodes (10): test_add_subtask_survives_sync_and_lands_in_plan(), test_sync_preserves_stable_ids_and_fields_across_reorder(), test_sync_workspace_tasks_populates_tasks_md(), test_update_task_graph_syncs_plan(), UPDATE_TASK_GRAPH — dynamically mutate sub-tasks in .torchlight/goal_spec.json., tool_update_task_graph_impl(), Generate a collision-free stable task id (never index-based)., Synchronize the canonical goal_spec.json with the plan/task markdown views. (+2 more)

### Community 177 - "test_tui_diff_view.py"
Cohesion: 0.12
Nodes (28): anyio, Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)., A pre-write snapshot (from approval) wins over the already-written disk state., The engine's own CODE_FILE_WRITE approval path is diffable too., The approval modal shows a DIFF PREVIEW section when entries exist., test_approval_modal_omits_diff_when_empty(), test_approval_modal_renders_diff(), test_build_diff_preview_code_file_write() (+20 more)

### Community 178 - "implementations.py"
Cohesion: 0.06
Nodes (47): _auto_repair(), _commit_edit_file(), _ddg_search(), _detect_doc_source(), _extract_identifiers(), _git_run(), play_and_verify_game(), Any (+39 more)

### Community 179 - "TestApp"
Cohesion: 0.22
Nodes (5): App, ComposeResult, on, Pressed, TestApp

### Community 182 - "._append_message"
Cohesion: 0.08
Nodes (16): Message, MessageRole, Trim SessionState lists to configured maximum to prevent unbounded growth., Explicitly record a read file in session state if it is a valid file path., Register a callback for memory events (MESSAGE_ADDED, PIN_ADDED, COMPACTION_TRIG, Unregister a memory event callback., Dispatch a memory event to registered listeners safely., Reactive event-driven compaction trigger. Automatically runs when token ratio cr (+8 more)

### Community 185 - ".__init__"
Cohesion: 0.20
Nodes (7): _beam_budget(), Estimate tokens consumed by system prompt, tools, and flashlight beam., Return (max_beam_files, max_lines_per_file) for the given context size., ConversationSummarizer, Summarizer with LLM-powered and rule-based fallback paths.      When an llm_clie, create_unified_registry(), Factory to create and bootstrap the unified registry.      Reuses create_default

### Community 187 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

### Community 188 - ".memory"
Cohesion: 0.14
Nodes (9): estimate_metadata_overhead(), Estimate tokens consumed by system prompt, tool schemas, and the flashlight beam, Return the current project root path from engine or working directory., build_plan_overview_text(), build_task_checklist_text(), Pure text-formatting helpers for the Torchlight TUI.  No engine / App state, no, Render Implementation Plan overview (title & mode badge)., Render Task Checklist hierarchy & progress bar. (+1 more)

### Community 191 - "TestApp"
Cohesion: 0.33
Nodes (3): App, ComposeResult, TestApp

## Knowledge Gaps
- **341 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `context-manager-cli`, `run.sh script`, `COLORTERM` (+336 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RLMEngineOptimized` connect `RLMEngineOptimized` to `registry.py`, `test_plan_execution_loop.py`, `TrajectoryLock`, `REPLSandbox`, `CommandPalette`, `test_resizer.py`, `ProjectMemory`, `get_phase_system_prompt`, `test_tui_trajectory_rail.py`, `test_tui_plan_panel.py`, `DebateVerifier`, `context_manager/memory/models.py`, `TorchlightApp`, `PaneResizer`, `main_optimized.py`, `ExecutionFeedbackLoop`, `AgentStatusModal`, `MessageCard`, `core/memory/manager.py`, `test_tui_diff_view.py`, `ProjectMemory`, `._stream_llm_with_retry`, `.__init__`, `.memory`, `ApprovalModal`, `test_inline_interception.py`, `test_tui_tool_cards.py`, `RLMEngine`, `tui_app.py`, `._parse_response`, `Step`, `rlm_engine_optimized.py`, `on`, `TieredMemory`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `TorchlightApp` connect `TorchlightApp` to `CommandPalette`, `test_resizer.py`, `test_tui_trajectory_rail.py`, `AutonomousHarness`, `test_tui_plan_panel.py`, `system.py`, `RLMEngineOptimized`, `PromptTextArea`, `PaneResizer`, `AgentStatusModal`, `MessageCard`, `test_tui_diff_view.py`, `.memory`, `test_tui_accessibility.py`, `ApprovalModal`, `Static`, `test_tui_tool_cards.py`, `CenterEmptyState`, `tui_app.py`, `Step`, `ConnectionPill`, `test_tui_theme.py`, `on`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `AutonomousHarness` connect `AutonomousHarness` to `TorchlightApp`, `SymbolIndex`, `test_autonomous_harness_pipeline.py`, `PaneResizer`, `ExecutionFeedbackLoop`, `CommandPalette`, `AgentStatusModal`, `HtmlGamePlayer`, `core/memory/manager.py`, `ApprovalModal`, `tui_app.py`, `cli/main.py`, `StreamingChatSession`, `on`, `TieredMemory`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `TorchlightApp` (e.g. with `_StubClient` and `AutonomousHarness`) actually correct?**
  _`TorchlightApp` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `TieredMemory` (e.g. with `StreamingChatSession` and `AutonomousHarness`) actually correct?**
  _`TieredMemory` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `RLMEngineOptimized` (e.g. with `ConversationSummarizer` and `Message`) actually correct?**
  _`RLMEngineOptimized` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `MemoryConfig` (e.g. with `StreamingChatSession` and `ContextBudget`) actually correct?**
  _`MemoryConfig` has 21 INFERRED edges - model-reasoned connections that need verification._