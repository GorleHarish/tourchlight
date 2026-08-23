# Graph Report - tourchlight v1_i6  (2026-08-16)

## Corpus Check
- 251 files · ~205,380 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4100 nodes · 8563 edges · 201 communities (179 shown, 22 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 827 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `363fe600`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- PromptTextArea
- context-manager-cli/tests/test_models.py
- ProjectSnapshot
- SymbolIndex
- ToolRegistry
- BaseSkill
- LMStudioClient
- TokenCounter
- REPLSandbox
- CommandPalette
- test_resizer.py
- StructurePreservingHTMLParser
- RecoveryEngine
- test_implementations.py
- verify_m1_setup.py
- ActionTracker
- TrajectoryLogger
- InferenceParams
- ProjectMemory
- get_phase_system_prompt
- android_ref_build.md
- classify_command
- test_tui_plan_panel.py
- PlanningSkill
- ContextDashboard
- DebateVerifier
- config.py
- StreamingChatSession
- UI Chat Improvements Plan - Minimal Context & Token Savings
- LLMClient
- Changelog
- RLMEngineOptimized
- PyASTVisitor
- context_manager/compression/summarizer.py
- TorchlightApp
- android_ref_runtime.md
- VerbatimCompactor
- test_tui_image_viewer.py
- context_manager/memory/persistence.py
- TaskDAG
- ._apply_pane_widths
- test_multimodal_vision.py
- TDDSkill
- Issues Found
- android_ref_emulator.md
- test_tui_tabbed_editor.py
- test_tui_transcript_widgets.py
- get_tool_registry
- VerbatimCompactor
- test_prompts_and_memory.py
- ProjectMemory
- test_tui_status_bar.py
- MarkdownDocumentSkill
- TestRunResult
- ._handle_slash_command
- cli/main.py
- Torchlight Architecture
- tool_edit_file_impl
- test_graph_engine.py
- core/memory/manager.py
- test_tui_accessibility.py
- import_skill_file
- Static
- SkillResult
- android_ref_adb.md
- IndexVisitor
- update_project_graph_file
- ToolCallCard
- Architecture
- ImageViewer
- test_code_quality_harness.py
- prompts_minimal.py
- test_phase_detection.py
- android_ref_signing.md
- Prompt Templates for 7B Coder Models
- Torchlight Excellence Roadmap
- Checklist
- Memory System Deep Dive
- .action_tracker
- Execution Feedback Loop
- start_optimized_local.sh
- DeduplicationEngine
- setup_optimized.sh
- EditorTab
- run.sh
- TokenCounter
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- CloudClient
- context-manager-cli
- torchlight-core
- test_grammar_parse.py
- Console
- Context Manager CLI
- Torchlight — Terminal AI Coding Agent
- .update
- .agents/AGENTS.md
- ProjectGraph
- Data Flow
- Core Classes
- .solve_async
- SymbolIndex
- PaneResizer
- test_tui_theme.py
- Resource-Adaptive Features
- .reset
- rlm_engine_optimized.py
- Graphify Codebase Exploration & Dependency Hard Rules
- workflows/graphify.md
- web_server.py
- on
- MemoryConfig
- Target Quality Tiers
- P1: Important Follow-On Work
- Compression System
- Future Improvements
- Improvement Recommendations by Resource Tier
- Torchlight Documentation
- TrajectoryLock
- test_plan_execution_loop.py
- Torchlight Rust Port: Performance-Critical Paths
- Android Troubleshoot — Routing Layer
- Memory Tiers
- Persistence
- HtmlGamePlayer
- dashboard.py
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
- .on_button_pressed
- test_tui_file_tree.py
- context_manager/prompts.py
- Plan: Non-Security Improvements
- context_manager/memory/embeddings.py
- context_manager/memory/models.py
- main_optimized.py
- build_agent_memory_scratchpad_text
- ContextBudget
- Flashlight
- Plan: UI Improvements — Torchlight Codex IDE
- opencode.json
- rlm_engine.py
- graphify.js
- TranscriptView
- HTMLGameSkill
- ExecutionFeedbackLoop
- test_inline_interception.py
- test_tui_command_palette.py
- ._submit_user_input
- _extract_markdown_skill_metadata
- test_tui_diff_view.py
- implementations.py
- TestApp
- MessageCard
- TieredMemory
- test_autonomous_harness.py
- core/compression/summarizer.py
- .__init__
- tui_app.py
- TestApp
- ActionEntry
- 🎮 Essential Game Mechanics Checklist
- ModalTestApp
- llamacpp_client.py
- Textual & Rich TUI Performance and Design Rules
- tui_widgets/__init__.py
- Ponytail
- Ponytail
- TestApp
- ModalTestApp
- core/api/lmstudio.py
- .__init__
- .append_output_log
- Code Cleaner Skill
- sanitize_assistant_text
- Schema Reference

## God Nodes (most connected - your core abstractions)
1. `TorchlightApp` - 199 edges
2. `TieredMemory` - 167 edges
3. `RLMEngineOptimized` - 104 edges
4. `MemoryConfig` - 95 edges
5. `AutonomousHarness` - 67 edges
6. `ExecutionFeedbackLoop` - 53 edges
7. `LlamaCppClient` - 50 edges
8. `SkillUploadModal` - 49 edges
9. `CloudClient` - 44 edges
10. `ProjectMemory` - 42 edges

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

## Communities (201 total, 22 thin omitted)

### Community 0 - "PromptTextArea"
Cohesion: 0.19
Nodes (6): ContextFileAttached, PromptTextArea, Message, TextArea whose Enter submits instead of inserting a newline.      Hooks ``update, Posted when the user accepts an @file suggestion., TextArea

### Community 1 - "context-manager-cli/tests/test_models.py"
Cohesion: 0.16
Nodes (14): ContentChunk, ContextSnapshot, MemoryObject, SessionState, WorkingSetSnapshot, test_content_chunk_custom(), test_content_chunk_defaults(), test_context_snapshot_fields() (+6 more)

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
Cohesion: 0.07
Nodes (32): ABC, BaseSkill, CalculatorSkill, create_default_registry(), GitSkill, _LazySkill, Any, Skills — external / plugin capabilities.  Skills are DIFFERENT from core tools: (+24 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.14
Nodes (8): _friendly_timeout_msg(), LMStudioClient, Synchronous streaming generator — yields tokens one-by-one.          Uses DEFAUL, Async streaming generator. Uses per-chunk read timeout (DEFAULT_TIMEOUT)., Simple synchronous query interface (LLMClient protocol compatibility)., Return a human-readable message explaining which part of the request timed out., Timeout, TimeoutException

### Community 7 - "TokenCounter"
Cohesion: 0.08
Nodes (27): Re-export TieredMemory and MemoryConfig from shared core library core.memory.man, Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length., _scratchpad_clean(), CompressionConfig, CompressionLevel, Enum, Pattern, Selective Memory Compression — Progressive context reduction for local LLMs.  4- (+19 more)

### Community 8 - "REPLSandbox"
Cohesion: 0.09
Nodes (31): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+23 more)

### Community 9 - "CommandPalette"
Cohesion: 0.10
Nodes (10): Highlighted, AttachContextModal, CommandPalette, Changed, on, Selected, Submitted, Command palette + slash-command autocomplete for the Torchlight TUI.  Phase 4: * (+2 more)

### Community 10 - "test_resizer.py"
Cohesion: 0.26
Nodes (15): _build_app(), _click_resizer(), _drag_resizer(), Regression tests for the PaneResizer drag/click resizing in tui_app.py.  The Pan, No-op client so the engine never touches LM Studio / Ollama / cloud., Simulate a real drag: mouse_down -> captured MouseMove -> mouse_up., _resize_to(), _start_app() (+7 more)

### Community 11 - "StructurePreservingHTMLParser"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 12 - "RecoveryEngine"
Cohesion: 0.07
Nodes (52): get_recovery_hint(), inject_recovery_into_memory(), Any, Recovery engine for Torchlight errors.  Provides structured recovery strategies, Push recovery hint into memory state's tried_and_failed scratchpad list     to e, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type. (+44 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.07
Nodes (40): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_read_symbols_indented_methods_and_duplicate_names(), test_run_command_intercept_ast_functions(), test_search_ast_action_aliases(), test_search_ast_after_writing_file(), test_search_ast_impl_fallback(), test_verify_compile_param(), test_edit_file_impl() (+32 more)

### Community 14 - "verify_m1_setup.py"
Cohesion: 0.18
Nodes (24): format_memory_status(), get_memory_pressure(), is_memory_safe(), Memory pressure monitor for macOS Apple Silicon.  Provides real-time memory pres, Return a human-readable one-line memory status string., Get current macOS memory pressure level and stats.      Returns:         dict wi, Quick check: is it safe to run inference without swap thrashing?      Args:, check_hardware() (+16 more)

### Community 15 - "ActionTracker"
Cohesion: 0.22
Nodes (5): ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex

### Community 16 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 17 - "InferenceParams"
Cohesion: 0.07
Nodes (25): detect_model_traits(), InferenceParams, One-line description of current params., Convert to API payload dict, excluding None and default values., Detect architecture traits (size, reasoning status, vision capability) from mode, Writing code files. Near-deterministic — exact syntax matters., Reasoning through plans. Moderate creativity. All tools remain available., Diagnosing errors. Slightly more exploration. (+17 more)

### Community 18 - "ProjectMemory"
Cohesion: 0.06
Nodes (40): ensure_git_repository(), ensure_project_initialized(), init_new_project(), ProjectMemory, MemoryObject, Path, SessionState, Ensure target project directory exists and has a local Git repository initialize (+32 more)

### Community 19 - "get_phase_system_prompt"
Cohesion: 0.10
Nodes (16): DirectiveTracker, Any, Directive tracker and constraint violation reinforcement module for Torchlight., Record a directive violation (e.g. 'cd_command', 'test_assertion_delete'), Reset violation counts., Tracks model constraint violations during execution turns and dynamically     in, get_phase_system_prompt(), Generate phase-tailored system prompt by selecting the dedicated phase template (+8 more)

### Community 20 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 21 - "classify_command"
Cohesion: 0.10
Nodes (26): CoreToolRegistry, get_core_registry(), Any, Compatibility subclass of ToolRegistry providing CLI-specific execute/dangerous_, test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command() (+18 more)

### Community 22 - "test_tui_plan_panel.py"
Cohesion: 0.18
Nodes (16): _build_plan_text(), _make_app(), anyio, Delegate to the real TUI plan-builder helper., Verify build_plan_text handles bulleted plan lists without explicit checkboxes., Repeated checklist entries (summary + detailed sections) must not duplicate., test_build_plan_text_all_done(), test_build_plan_text_dedupes_duplicate_checkbox_lines() (+8 more)

### Community 23 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 24 - "ContextDashboard"
Cohesion: 0.11
Nodes (6): ContextDashboard, Panel, Print sub-agent task progress to the console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 25 - "DebateVerifier"
Cohesion: 0.09
Nodes (23): Adversarial critique / debate. Focused flaw identification., Synthesis and refinement following critique. Deterministic., Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., CritiqueResult, DebateVerifier, DebateVerifier implementation: orchestrates adversarial critique and refinement, Synthesize refined output incorporating valid critiques using InferenceParams.fo (+15 more)

### Community 26 - "config.py"
Cohesion: 0.11
Nodes (21): test_list_available_models_includes_gemma4e4b(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), test_normalize_mlx_gemma_4_4e4b(), ContextProfile, _detect_apple_silicon_ram(), _detect_chip(), get_context_profile() (+13 more)

### Community 27 - "StreamingChatSession"
Cohesion: 0.14
Nodes (12): chat(), get_phase_system_prompt(), Panel, /params                    — show current params         /params auto, Start an interactive chat session with context management and flashlight., Re-append closing tags and unclosed JSON braces that were consumed as stop token, Auto-switch _params based on detected phase.  No-op when locked., Run out-of-band DebateVerifier pass if candidate proposal needs verification. (+4 more)

### Community 28 - "UI Chat Improvements Plan - Minimal Context & Token Savings"
Cohesion: 0.05
Nodes (36): 1.1 Rich Message Card Component, 1.2 Streaming Experience Improvements, 1.3 Transcript Container Enhancements, 1. Message Rendering & Formatting (Claude Code-like Experience), 2.1 Content Fingerprinting System, 2.2 Deduplication-Aware Compression, 2.3 Tool Result Deduplication, 2. Semantic Deduplication for Token Savings (+28 more)

### Community 29 - "LLMClient"
Cohesion: 0.09
Nodes (20): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client() (+12 more)

### Community 30 - "Changelog"
Cohesion: 0.06
Nodes (32): Added, Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+24 more)

### Community 31 - "RLMEngineOptimized"
Cohesion: 0.07
Nodes (37): Verify Goal mode detects missing implementation_plan.md and forces 'plan' phase., Verify bare JSON tool calls without <tool_call> tags are correctly parsed as too, test_detect_phase_goal_mode_missing_plan_forces_plan(), test_parse_response_bare_json_tool_call(), anyio, test_verification_gate_allows_final_answer_when_all_done(), test_verification_gate_rejects_premature_final_answer(), test_verification_gate_rejects_resume_work_without_tools() (+29 more)

### Community 32 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.16
Nodes (16): ConversationSummarizer, DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer (+8 more)

### Community 34 - "TorchlightApp"
Cohesion: 0.05
Nodes (15): asyncio, Tests for TorchlightApp project_root property and task manager modal integration, test_action_task_manager_pushes_screen(), test_torchlight_app_project_root_fallback(), test_torchlight_app_project_root_property(), NodeSelected, App, Codex / Tiny-Brain 2 Style Agent IDE TUI. (+7 more)

### Community 35 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (8): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 37 - "test_tui_image_viewer.py"
Cohesion: 0.10
Nodes (26): anyio, fixture, Tests for TUI ImageViewer, BinaryFileViewer, and ImageAttachmentCard.  Verifies:, Create a temporary PNG image file for testing., Test save_clipboard_image when PIL ImageGrab returns a PIL Image., Test save_clipboard_image when PIL ImageGrab returns list of copied file paths., Test save_clipboard_image when clipboard is empty / contains no image., Test PromptTextArea pasting image path or clipboard image emits ContextFileAttac (+18 more)

### Community 38 - "context_manager/memory/persistence.py"
Cohesion: 0.18
Nodes (11): MemoryNeedle, Message, ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, SessionState, SessionPersistence (+3 more)

### Community 39 - "TaskDAG"
Cohesion: 0.07
Nodes (38): Any, Enum, str, Robust Task Lifecycle and Directed Acyclic Graph (DAG) Engine for Torchlight.  P, Directed Acyclic Graph (DAG) for Task Lifecycle Management., Add a task node to the DAG after verifying cycle safety., Remove a node and strip references to it from dependencies and subtasks., Detect cycles using Kahn's topological sort algorithm. (+30 more)

### Community 41 - "test_multimodal_vision.py"
Cohesion: 0.07
Nodes (55): Any, Convert Message to provider-compatible API payload dictionary., fixture, Path, Unit and integration tests for multimodal vision capabilities (Gemma 3, Qwen VL,, Verify Message.to_dict generates rich text description when vision_supported is, Verify format_image_text_summary extracts metadata and embeds exact calling cont, Create a minimal 1x1 valid PNG image. (+47 more)

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "Issues Found"
Cohesion: 0.12
Nodes (16): 1. **ExecutionMode Enum Mismatch**, 2. **Phase Detection Not Integrated with Goal Mode**, 3. **Goal Spec Initialization Race Condition**, 4. **Missing Verification Gate in CLI Goal Mode**, 5. **AutonomousHarness Not Wired to LLM Engine in CLI**, 6. **Inconsistent ExecutionMode Default**, 7. **Memory State Sync Issues**, Fix Plan (+8 more)

### Community 44 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 45 - "test_tui_tabbed_editor.py"
Cohesion: 0.12
Nodes (19): anyio, Tests for Phase-5 tabbed editor split pane (open_file_tab, dirty marker, keyboar, test_close_file_tab_removes_from_open_tabs(), test_close_file_tab_switches_active_tab(), test_dirty_marker_not_set_for_non_tab_file(), test_dirty_marker_set_on_write_step(), test_editor_pane_resizer_and_scrollbars(), test_editor_split_pane_composes() (+11 more)

### Community 46 - "test_tui_transcript_widgets.py"
Cohesion: 0.10
Nodes (23): anyio, Tests for Phase-1 transcript widgets (message cards, streaming, thinking)., Smoke test: the real app mounts MessageCards and drives the streaming view., Verify MessageCard copy and reuse actions work for user and assistant messages., Verify MessageCard duration formatting, empty user headers, and timestamp overri, test_app_transcript_wiring(), test_card_meta_for(), test_estimate_token_count() (+15 more)

### Community 47 - "get_tool_registry"
Cohesion: 0.07
Nodes (39): test_search_ast_schema_validation(), test_game_tools_registered(), Verify validate_tool_call auto-heals missing/misplaced path arguments for VIEW_I, test_validate_tool_call_view_image_auto_healing(), asyncio, test_edit_file_tail_ultra_compact_directive(), test_identical_old_new_text_preflight(), test_ring_buffer_prompt_dedup_skip() (+31 more)

### Community 48 - "VerbatimCompactor"
Cohesion: 0.14
Nodes (6): CompressionConfig, Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 49 - "test_prompts_and_memory.py"
Cohesion: 0.11
Nodes (18): extract_modified_symbols(), is_valid_file_path(), Validate if a string is a genuine file path rather than code attribute access (e, Extract function/class AST symbol names modified or added between old and new te, Unit tests for phase-tailored system prompts, anti-symptom-patching rules, and L, Verify L0 scratchpad does not inject disk task matrices when in Chat Mode., test_extract_modified_symbols(), test_goal_mode_pre_planning_context_check_directives() (+10 more)

### Community 50 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 51 - "test_tui_status_bar.py"
Cohesion: 0.16
Nodes (17): anyio, Tests for Phase-4 consolidated status bar (gauge + segments widget)., test_build_status_segments_defaults(), test_build_status_segments_populated(), test_build_status_segments_running_no_tps_yet(), test_build_status_segments_server_offline_and_branch_escape(), test_gauge_markup_clamps_out_of_range(), test_gauge_markup_color_escalation() (+9 more)

### Community 53 - "TestRunResult"
Cohesion: 0.16
Nodes (13): Re-export ExecutionFeedbackLoop and TestRunResult from shared core library core., Execution feedback loop for Torchlight., Enum, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Return True only if a run succeeded. Uses exit code as the authoritative, TestResultStatus, TestRunResult, create_mock_feedback_loop() (+5 more)

### Community 54 - "._handle_slash_command"
Cohesion: 0.07
Nodes (18): fetch_provider_models(), is_port_in_use(), Query an OpenAI-compatible /models endpoint (LM Studio, Ollama, llama.cpp)     o, Check if server port 8080 is actively listening., load_last_state(), main(), _provider_runtime_info(), Return (port, externally_managed) for a given provider key.      externally_mana (+10 more)

### Community 55 - "cli/main.py"
Cohesion: 0.14
Nodes (13): command, compress_file(), count_tokens(), goal(), Start an autonomous goal execution session driven by .torchlight task tracking., Compress a file using verbatim compaction., Count tokens in text., Manage saved sessions. (+5 more)

### Community 56 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 57 - "tool_edit_file_impl"
Cohesion: 0.12
Nodes (26): test_edit_file_blocks_broken_syntax(), test_tool_edit_file_integration(), Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_auto_fallback_to_write(), test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_line_bounded(), test_edit_file_line_bounded_without_old_text() (+18 more)

### Community 58 - "test_graph_engine.py"
Cohesion: 0.26
Nodes (12): get_project_graph(), Get or create the ProjectGraph instance for a given root directory., Path, Unit tests for Torchlight Native AST Graph Engine., test_empty_graph_json_rebuild(), test_html_script_indexing(), test_mtime_incremental_build(), test_project_graph_advanced_signatures_and_paths() (+4 more)

### Community 59 - "core/memory/manager.py"
Cohesion: 0.06
Nodes (63): Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, build_embedder(), compute_tf_idf_score(), cosine_similarity(), Embedder, HybridEmbedder, HybridMemoryRetriever, _is_low_memory() (+55 more)

### Community 60 - "test_tui_accessibility.py"
Cohesion: 0.10
Nodes (28): _make_app(), anyio, Tests for Phase-6 accessibility and keyboard navigation.  Covers: - Tab bar keyb, Arrow navigation wraps around at the ends., Arrow keys don't do anything when no tabs are open., Verify :focus rules exist for tab items in the .tcss file., Verify responsive @media-equivalent class rules exist., Verify no #hex color values appear in the .tcss file. (+20 more)

### Community 61 - "import_skill_file"
Cohesion: 0.10
Nodes (32): get_skill_directories(), Return candidate directories containing skills in priority order:     1. <worksp, discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any (+24 more)

### Community 62 - "Static"
Cohesion: 0.08
Nodes (17): DirectoryTree, ComposeResult, VerticalScroll, ComposeResult, ComposeResult, ComposeResult, ComposeResult, ComposeResult (+9 more)

### Community 63 - "SkillResult"
Cohesion: 0.11
Nodes (12): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi, Any, ReproSkill, SkillResult, Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor (+4 more)

### Community 64 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 65 - "IndexVisitor"
Cohesion: 0.27
Nodes (4): index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings.

### Community 66 - "update_project_graph_file"
Cohesion: 0.32
Nodes (6): Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Incrementally update the AST graph for a single modified file., update_project_graph_file(), Unit tests for incremental O(1) AST graph delta updates., test_incremental_graph_file_update(), test_update_project_graph_file_helper()

### Community 67 - "ToolCallCard"
Cohesion: 0.06
Nodes (38): anyio, Tests for Phase-2 tool call cards (risk badge, status, timing, sections)., The streamed <tool_call> mounts a pending card completed by the step., Verify tool calls with <= 10 lines of output default to expanded., Verify tool calls with > 10 lines of output default to collapsed., Verify ToolCallCard.action_copy extracts result/payload and triggers copy., test_app_pending_card_wiring(), test_risk_for_tool() (+30 more)

### Community 68 - "Architecture"
Cohesion: 0.15
Nodes (12): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Hard Rules, Commands, Context Budget Breakdown, Development (+4 more)

### Community 69 - "ImageViewer"
Cohesion: 0.14
Nodes (9): copy_to_clipboard(), Copy text to system clipboard across macOS, Linux, and Windows., ImageViewer, open_file_in_system_app(), on, Pressed, VerticalScroll, Open a file with the operating system default application. (+1 more)

### Community 70 - "test_code_quality_harness.py"
Cohesion: 0.06
Nodes (53): calculate_in_memory_diff(), Calculate exact lines added and deleted between two string buffers in RAM., Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_compile_gate_rejects_return_outside_function() (+45 more)

### Community 71 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 72 - "test_phase_detection.py"
Cohesion: 0.18
Nodes (15): _make_session(), Chat phase should have higher temperature than code phase., Create a StreamingChatSession with mocked heavy dependencies., Verify that when session is explicitly in Chat Mode, _detect_phase returns 'chat, Troubleshoot wins over code when both signals are present in unified mode., Code phase should yield lower temperature than chat phase., test_detect_chat_mode_resilient(), test_detect_chat_phase() (+7 more)

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

### Community 79 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

### Community 81 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

### Community 82 - "DeduplicationEngine"
Cohesion: 0.05
Nodes (36): ConceptTracker, ContentFingerprint, ContentFingerprinter, deduplicate_context(), DeduplicationEngine, DeduplicationStats, Semantic Deduplication Engine for Torchlight.  Provides content-aware deduplicat, Fingerprint explanatory content to track concepts explained. (+28 more)

### Community 83 - "setup_optimized.sh"
Cohesion: 0.60
Nodes (3): info(), ok(), setup_optimized.sh script

### Community 84 - "EditorTab"
Cohesion: 0.12
Nodes (9): EditorTab, Message, Clean single-line tab widget displaying file name with close button., Emitted when tab is clicked to switch active file., Emitted when tab close button '×' is clicked., Emitted when tab is right-clicked., TabClosed, TabRightClicked (+1 more)

### Community 85 - "run.sh"
Cohesion: 0.40
Nodes (4): COLORTERM, PYTHONPATH, run.sh script, TERM

### Community 86 - "TokenCounter"
Cohesion: 0.07
Nodes (32): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing. (+24 more)

### Community 87 - "tui.sh"
Cohesion: 0.40
Nodes (5): cleanup(), COLORTERM, PYTHONPATH, tui.sh script, TERM

### Community 94 - "CloudClient"
Cohesion: 0.09
Nodes (14): CloudClient, Sanitize message roles. Convert system role to user role for models (e.g. Gemma, Async streaming implementation required by LLMClient protocol., Return the ids of models the provider currently reports as available.         Us, Resolve requested self.model against live models to prevent 404 mismatches., _sanitize_messages_for_cloud(), create_client(), create_client() (+6 more)

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

### Community 108 - ".update"
Cohesion: 0.08
Nodes (12): Infer the current agent phase from user input and the last model response., Any, Submitted, Return the current project root path from engine or working directory., Update the inner static widget content., Update the context usage bar in the Agent tab., Committed memory tokens plus in-flight streamed tokens for the context gauge., build_plan_overview_text() (+4 more)

### Community 110 - "ProjectGraph"
Cohesion: 0.13
Nodes (15): ProjectGraph, Any, Path, Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Scan project files incrementally using st_mtime and construct/update the AST gra, Parse file via Tree-Sitter when tree_sitter library is installed., Perform an incremental O(1) AST update for a single modified file., Remove all nodes and edges referencing a deleted file. (+7 more)

### Community 111 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 112 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 113 - ".solve_async"
Cohesion: 0.10
Nodes (14): Return True if the most recent test run actually ran and has failing or, mark_task_in_progress(), Mark a task as in_progress (started)., Check if active LLM client or server supports multimodal image inputs., Build an explicit warning attached to an accepted final answer when the, Notify listeners of real-time background status and action telemetry., Notify listeners (dashboard/TUI) that task state changed after a tool call., Re-append closing tags that were consumed as stop tokens by llama-server. (+6 more)

### Community 114 - "SymbolIndex"
Cohesion: 0.13
Nodes (12): Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build(), test_symbol_index_summary() (+4 more)

### Community 115 - "PaneResizer"
Cohesion: 0.12
Nodes (11): MouseMove, MouseUp, PaneResizer, Interactive splitter bar to resize the left/right side panes.      Drag the bar, ConnectionPill, ComposeResult, Horizontal, Pressed (+3 more)

### Community 116 - "test_tui_theme.py"
Cohesion: 0.18
Nodes (15): _make_app(), anyio, Tests for Phase-6 theme consistency and responsive layout classes.  Covers: - CS, Ensure CSS doesn't contain hardcoded hex colors., Ensure CSS uses theme variables like $background., Ensure CSS has rules for responsive terminal classes., Responsive classes are applied when terminal is narrow., Short-terminal class applied when height < 24. (+7 more)

### Community 117 - "Resource-Adaptive Features"
Cohesion: 0.29
Nodes (7): Compression Cooldown, Embedding Cache, LLM State Extraction, Resource-Adaptive Configuration, Resource-Adaptive Features, Resource Tiers, Tool Result Budget

### Community 119 - "rlm_engine_optimized.py"
Cohesion: 0.15
Nodes (26): Unit tests for core/tools/parser.py tolerant tool parser & fuzzy repair engine., test_extract_balanced_json_object(), test_parse_tool_call_payload(), test_repair_unclosed_action_tags(), test_repair_unclosed_tool_call_tag(), test_single_quoted_dict_parsing(), test_strip_interleaved_prose(), test_strip_thinking_tags() (+18 more)

### Community 120 - "Graphify Codebase Exploration & Dependency Hard Rules"
Cohesion: 0.40
Nodes (4): 1. Mandatory Graphify-First Codebase Search, 2. Dependency & Relationship Analysis, 3. Graph Synchronization, Graphify Codebase Exploration & Dependency Hard Rules

### Community 123 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 124 - "on"
Cohesion: 0.05
Nodes (6): DirectorySelected, FileSelected, Changed, on, Pressed, Selected

### Community 125 - "MemoryConfig"
Cohesion: 0.07
Nodes (36): Enum, str, TaskStatus, MemoryConfig, test_pin_file_truncation_to_budget(), test_l0_scratchpad_priority_weighted_order(), Unit tests for manual context compaction trigger and 85%/91% threshold logic., test_compress_recent_truncates_oversized_tool_output_when_older_empty() (+28 more)

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
Cohesion: 0.12
Nodes (21): Unit tests for core/tools/dedup.py argument normalization & TrajectoryLock., test_compute_payload_hash(), test_edit_file_alternate_trajectory_hint(), test_normalize_tool_args(), test_trajectory_lock(), test_trajectory_lock_error_feedback(), test_trajectory_lock_window_and_read_only_rate_limiting(), compute_payload_hash() (+13 more)

### Community 133 - "test_plan_execution_loop.py"
Cohesion: 0.05
Nodes (79): test_add_subtask_survives_sync_and_lands_in_plan(), test_auto_mark_does_not_complete_stub_or_missing_file(), test_auto_mark_does_not_overmark_unrelated_tasks(), test_auto_mark_matches_target_files_exact_basename(), test_auto_mark_multi_file_task_in_progress(), test_auto_mark_no_false_positive_substring(), test_auto_mark_pending_task_becomes_in_progress_without_verification(), test_auto_mark_task_completed_by_file() (+71 more)

### Community 134 - "Torchlight Rust Port: Performance-Critical Paths"
Cohesion: 0.10
Nodes (20): 1. `token_counter` → `torchlight_core::token_counter` (Week 1), 2. `flashlight/indexer.py` → `torchlight_core::ast_indexer` (Week 2), 3. `graph_engine.py` → `torchlight_core::graph_engine` (Week 3), 4. `memory/manager.py` → `torchlight_core::memory::tiered` (Week 4), 5. `memory/selective_compression.py` → `torchlight_core::memory::selective` (Week 5), 6. `memory/budget.py` → `torchlight_core::memory::budget` (Week 5), 7. `compression/summarizer.py` → `torchlight_core::compression::summarizer` (Week 6), 8. `tools/parser.py` → `torchlight_core::tools::parser` (Week 6) (+12 more)

### Community 135 - "Android Troubleshoot — Routing Layer"
Cohesion: 0.50
Nodes (3): Android Troubleshoot — Routing Layer, Step 1 — Call the tool, Step 2 — Read ONE reference file only if deeper guidance is needed

### Community 136 - "Memory Tiers"
Cohesion: 0.50
Nodes (4): Disk Tiers (ProjectMemory), In-Memory Tiers (TieredMemory.messages), Memory Tiers, Session State Tiers

### Community 137 - "Persistence"
Cohesion: 0.50
Nodes (4): Loading Session State, Persistence, Project Memory Persistence, Session Persistence

### Community 138 - "HtmlGamePlayer"
Cohesion: 0.05
Nodes (50): GameInputEvent, GameOutcomeResult, get_process_memory_mb(), HtmlGamePlayer, Path, HTML Game Inspector & Player Harness for Torchlight.  Provides autonomous playin, Autonomous HTML Game Harness & Dynamic Verifier.      Launches an ephemeral brow, Plays the HTML game for duration_ms while simulating inputs and checking frame d (+42 more)

### Community 139 - "dashboard.py"
Cohesion: 0.33
Nodes (3): _ActionContext, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 140 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 148 - "test_tui_trajectory_rail.py"
Cohesion: 0.24
Nodes (9): anyio, Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)., The streamed <tool_call> adds a dot; the completing step flips it., test_app_pending_step_updates_rail(), test_rail_add_pending_and_complete_ok(), test_rail_clear_removes_dots(), test_rail_complete_error_and_denied(), test_rail_complete_without_pending_is_noop() (+1 more)

### Community 149 - "AutonomousHarness"
Cohesion: 0.11
Nodes (16): AutonomousHarness, GoalSpec, Path, Ensure target project has local git repository and persistent memory initialized, Ensure a goal spec exists on disk in .torchlight, initializing a default workspa, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks., Construct inter-task memory prompt summarizing prior verified tasks and dependen (+8 more)

### Community 151 - "test_tui_file_tree.py"
Cohesion: 0.06
Nodes (32): _FakeProc, anyio, Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)., test_git_tree_decorates_file_labels(), test_git_tree_right_click_posts_message(), test_normalize_status_code(), test_parse_git_status_porcelain_basic(), test_parse_git_status_porcelain_quoted_path() (+24 more)

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
Cohesion: 0.13
Nodes (14): _build_excerpt(), LLMStateExtractor, _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa (+6 more)

### Community 157 - "main_optimized.py"
Cohesion: 0.31
Nodes (10): amain(), approval_prompt(), display_step(), get_depth_style(), main(), print_banner(), Step, Interactive approval for CONFIRM/REVIEW tier tools. (+2 more)

### Community 158 - "build_agent_memory_scratchpad_text"
Cohesion: 0.18
Nodes (11): Verify that square brackets and special markup characters in code/errors are esc, Empty memory renders a clean, friendly idle state., Verify long error messages are preserved in full without 75-char ellipsis trunca, Scratchpad gracefully falls back to parsing raw prompt strings., test_scratchpad_empty_state(), test_scratchpad_escapes_rich_special_characters(), test_scratchpad_parses_raw_prompt_string(), test_scratchpad_preserves_long_error_messages() (+3 more)

### Community 160 - "ContextBudget"
Cohesion: 0.08
Nodes (19): _clamp(), ContextBudget, Adaptive, headroom-driven context budget coordinator for Torchlight.  Static res, Token reserve kept for the recent-message window., Current fraction of the target window in use., Effective budget allocations for the current turn.      `used_tokens` is the liv, Token allowance for the L0 working memory scratchpad this turn., Max characters per scratchpad entry (longer when headroom is ample). (+11 more)

### Community 161 - "Flashlight"
Cohesion: 0.20
Nodes (5): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex

### Community 163 - "Plan: UI Improvements — Torchlight Codex IDE"
Cohesion: 0.18
Nodes (10): Decisions, Effort & Sequencing, Non-Goals, Plan: UI Improvements — Torchlight Codex IDE, Task 1: Fix Latent Bugs (prerequisite), Task 2: Phase 5 — Tabbed Editor Split Pane, Task 3: Phase 6a — Accessibility & Focus Management, Task 4: Phase 6b — Performance & Streaming Polish (+2 more)

### Community 164 - "opencode.json"
Cohesion: 0.50
Nodes (3): plugin, $schema, .opencode/plugins/graphify.js

### Community 165 - "rlm_engine.py"
Cohesion: 0.17
Nodes (13): test_rlm_engine_solve_method(), estimate_metadata_overhead(), Estimate tokens consumed by system prompt, tool schemas, and the flashlight beam, display_step(), get_depth_style(), main(), print_banner(), print_help() (+5 more)

### Community 167 - "TranscriptView"
Cohesion: 0.12
Nodes (10): VerticalScroll, Bounded scroll container hosting the transcript.      Encapsulates the 120-child, Mount a card, prune the oldest when over the cap, and scroll., Scroll the transcript to the bottom without animation., Navigate up (vim-style)., Navigate down (vim-style)., Focus a specific card by index., Copy last message content to clipboard. (+2 more)

### Community 168 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

### Community 169 - "ExecutionFeedbackLoop"
Cohesion: 0.06
Nodes (39): Post-edit auto-run test suite failure., TestFailureError, ExecutionFeedbackLoop, extract_surgical_traceback(), Path, Auto-run tests and web outcome inspection after code changes and inject feedback, Called after a tool is executed. Returns test results if tests were run., Freshly verify any modified-but-unverified files and return True if         ever (+31 more)

### Community 171 - "test_inline_interception.py"
Cohesion: 0.12
Nodes (19): test_clean_and_parse_json_tolerant_multiline_content(), test_clean_and_parse_json_trailing_unterminated_string(), _looks_like_full_file(), _looks_like_prose_or_outline(), Helper to check if content looks like a complete standalone file rather than a s, Trim prose a model appended after the file body when </WRITE_FILE> was     consu, Parse the LLM response for action tags.         Returns: (action, thinking, cont, Heuristic gate for inline code interception (step 6b of _parse_response).      R (+11 more)

### Community 172 - "test_tui_command_palette.py"
Cohesion: 0.09
Nodes (30): Binding, anyio, Tests for Phase-4 command palette + prompt autocomplete., test_add_context_chip_image_prefix(), test_build_palette_items_kinds_and_visibility(), test_command_palette_composes_filters_and_selects(), test_command_palette_enter_runs_highlighted_item(), test_fuzzy_filter_empty_query_and_no_match() (+22 more)

### Community 173 - "._submit_user_input"
Cohesion: 0.16
Nodes (5): Extract text from the TextArea, clear it, and dispatch., Programmatic send — called by ctrl+enter binding., Focus and open the model select dropdown (model badge click / toolbar)., Posted when the user presses Enter with no active suggestion., SubmitRequested

### Community 174 - "_extract_markdown_skill_metadata"
Cohesion: 0.24
Nodes (11): _extract_markdown_skill_metadata(), parse_frontmatter(), Splits a markdown file into (metadata_dict, body_markdown).     Gracefully falls, Extract (skill_name, description, icon, risk_level, category, tags) from a markd, asyncio, Path, test_extract_markdown_skill_metadata_frontmatter(), test_extract_markdown_skill_metadata_legacy_fallback() (+3 more)

### Community 177 - "test_tui_diff_view.py"
Cohesion: 0.09
Nodes (33): anyio, Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)., A pre-write snapshot (from approval) wins over the already-written disk state., The engine's own CODE_FILE_WRITE approval path is diffable too., The approval modal shows a DIFF PREVIEW section when entries exist., A successful WRITE_FILE step mounts a DiffView card with real content., test_app_write_step_renders_diff_card(), test_approval_modal_omits_diff_when_empty() (+25 more)

### Community 178 - "implementations.py"
Cohesion: 0.06
Nodes (59): Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Th, test_set_ctx_window(), Unit tests for context budget overflow detection and fixes in TieredMemory, RLME, test_tiered_memory_total_tokens_includes_pinned_files(), test_tool_context_window_scaling(), _ddg_search(), _detect_doc_source(), _extract_identifiers() (+51 more)

### Community 179 - "TestApp"
Cohesion: 0.22
Nodes (5): App, ComposeResult, on, Pressed, TestApp

### Community 180 - "MessageCard"
Cohesion: 0.07
Nodes (26): _build_cached_syntax(), escape_markup(), extract_code_blocks(), ImageAttachmentCard, MessageCard, Click, ComposeResult, Container (+18 more)

### Community 182 - "TieredMemory"
Cohesion: 0.04
Nodes (38): ContextSnapshot, Message, MessageRole, Path, Run semantic deduplication on current message history.                  Args:, Enable or disable semantic deduplication., Persist deduplication cache to project memory., Persist user preferences to project memory. (+30 more)

### Community 184 - "test_autonomous_harness.py"
Cohesion: 0.28
Nodes (15): HarnessConfig, main(), CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., create_mock_feedback_loop(), Path, Unit tests for AutonomousHarness module., A task that made no code changes must not be reverted by unrelated /     pre-exi, test_auto_git_init_and_clean_commit() (+7 more)

### Community 188 - "core/compression/summarizer.py"
Cohesion: 0.23
Nodes (8): ConversationSummarizer, Message, Conversation Summarizer for Torchlight.  Extracts key information from conversat, Summarize conversation turns for compression using high-density structured templ, Generate a high-density structured compaction template preserving key context in, Create a compact structured summary of messages., Extract key information from text., _role_label()

### Community 189 - ".__init__"
Cohesion: 0.20
Nodes (6): _is_valid_decision(), Load deduplication cache from project memory., Load user preferences from project memory., Filter out empty, generic, or noisy session summary strings., Load persistent project memory (.context-memory.json) into L0 working state., TokenCounter

### Community 190 - "tui_app.py"
Cohesion: 0.06
Nodes (53): NamedTuple, LlamaCppClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.          Runs the, Step, AgentMemoryWidget, AgentStatusModal, ApprovalModal (+45 more)

### Community 191 - "TestApp"
Cohesion: 0.33
Nodes (3): App, ComposeResult, TestApp

### Community 192 - "ActionEntry"
Cohesion: 0.29
Nodes (3): ActionEntry, A single recorded action with its status and elapsed time., Text

### Community 193 - "🎮 Essential Game Mechanics Checklist"
Cohesion: 0.20
Nodes (9): 1. Fixed Timestep Loop, 2. Input Handling & 180° Lock, 3. Zero-Dependency Web Audio Synth, 4. Particle Effects Engine, 🕹️ Architecture & Core Standards, 🎮 Essential Game Mechanics Checklist, 🚀 Generation Workflow, HTML5 / CSS / JS Snake Game Builder Skill (+1 more)

### Community 195 - "ModalTestApp"
Cohesion: 0.25
Nodes (6): ModalTestApp, App, asyncio, ComposeResult, Pressed, test_skill_upload_modal()

### Community 196 - "llamacpp_client.py"
Cohesion: 0.23
Nodes (8): Verify _strip_multimodal_images flattens image_url blocks into text., test_llamacpp_client_multimodal_image_stripping(), _context_limit_message(), Convert multimodal image_url content blocks to pure text descriptions for text-o, Sanitize message roles and preserve multimodal content blocks., Friendly remediation for llama-server 'context exceeded' errors., _sanitize_messages(), _strip_multimodal_images()

### Community 197 - "Textual & Rich TUI Performance and Design Rules"
Cohesion: 0.29
Nodes (6): 1. Widget Border & Alignment Discipline, 2. Modal Backdrop Opacity, 3. High-Performance Log Rendering, 4. Telemetry & Disk I/O Throttling, 5. Renderable AST Caching & Adaptive Streaming, Textual & Rich TUI Performance and Design Rules

### Community 199 - "Ponytail"
Cohesion: 0.40
Nodes (4): Persistence, Ponytail, Rules, The ladder

### Community 201 - "Ponytail"
Cohesion: 0.40
Nodes (4): Persistence, Ponytail, Rules, The ladder

### Community 207 - "ModalTestApp"
Cohesion: 0.25
Nodes (6): ModalTestApp, App, asyncio, ComposeResult, Pressed, test_skill_upload_modal()

### Community 211 - "core/api/lmstudio.py"
Cohesion: 0.40
Nodes (4): Re-export LMStudioClient from shared core library core.api.lmstudio., get_phase_inference_params(), LM Studio REST client.  Recovered from the original CLI implementation (commit f, Return the inference parameters preset for a named phase.

### Community 212 - ".__init__"
Cohesion: 0.40
Nodes (3): _beam_budget(), Estimate tokens consumed by system prompt, tools, and flashlight beam., Return (max_beam_files, max_lines_per_file) for the given context size.

### Community 215 - "Code Cleaner Skill"
Cohesion: 0.50
Nodes (3): Code Cleaner Skill, Purpose & Triggers, Workflow Instructions

### Community 216 - "sanitize_assistant_text"
Cohesion: 0.18
Nodes (10): Unified system prompts for Torchlight.  Single source of truth for all frontends, Remove raw tool payload dumps (Params:, Result:, Writing code to file: ...) from, sanitize_assistant_text(), build_tool_syntax_prompt(), get_tool_syntax_for_context_size(), Tool syntax instructions for Torchlight.  Generates the appropriate tool calling, Build the complete tool syntax prompt for the system message.      Args:, Return the tool calling syntax instructions appropriate for the model's context (+2 more)

### Community 221 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

## Knowledge Gaps
- **407 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `context-manager-cli`, `run.sh script`, `COLORTERM` (+402 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TorchlightApp` connect `TorchlightApp` to `PromptTextArea`, `CommandPalette`, `test_resizer.py`, `test_tui_trajectory_rail.py`, `AutonomousHarness`, `test_tui_plan_panel.py`, `test_tui_file_tree.py`, `RLMEngineOptimized`, `test_tui_image_viewer.py`, `TranscriptView`, `._apply_pane_widths`, `test_tui_tabbed_editor.py`, `test_tui_transcript_widgets.py`, `._submit_user_input`, `test_tui_diff_view.py`, `MessageCard`, `._handle_slash_command`, `test_tui_accessibility.py`, `tui_app.py`, `Static`, `ToolCallCard`, `ImageViewer`, `EditorTab`, `.append_output_log`, `sanitize_assistant_text`, `CloudClient`, `.update`, `PaneResizer`, `test_tui_theme.py`, `on`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `RLMEngineOptimized` connect `RLMEngineOptimized` to `TrajectoryLock`, `test_plan_execution_loop.py`, `ToolRegistry`, `REPLSandbox`, `test_resizer.py`, `ProjectMemory`, `get_phase_system_prompt`, `test_tui_trajectory_rail.py`, `test_tui_plan_panel.py`, `DebateVerifier`, `context_manager/memory/models.py`, `main_optimized.py`, `context_manager/compression/summarizer.py`, `TorchlightApp`, `test_tui_image_viewer.py`, `context_manager/memory/persistence.py`, `ExecutionFeedbackLoop`, `test_inline_interception.py`, `test_tui_tabbed_editor.py`, `test_tui_transcript_widgets.py`, `get_tool_registry`, `test_tui_diff_view.py`, `ProjectMemory`, `TieredMemory`, `._handle_slash_command`, `core/memory/manager.py`, `tui_app.py`, `ToolCallCard`, `EditorTab`, `.update`, `.solve_async`, `PaneResizer`, `rlm_engine_optimized.py`, `MemoryConfig`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `TieredMemory` connect `TieredMemory` to `test_plan_execution_loop.py`, `TokenCounter`, `AutonomousHarness`, `config.py`, `StreamingChatSession`, `build_agent_memory_scratchpad_text`, `RLMEngineOptimized`, `ContextBudget`, `rlm_engine.py`, `test_multimodal_vision.py`, `test_prompts_and_memory.py`, `implementations.py`, `TestRunResult`, `cli/main.py`, `test_autonomous_harness.py`, `tool_edit_file_impl`, `core/memory/manager.py`, `.__init__`, `tui_app.py`, `DeduplicationEngine`, `.__init__`, `CloudClient`, `.update`, `.solve_async`, `rlm_engine_optimized.py`, `MemoryConfig`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `TorchlightApp` (e.g. with `_StubClient` and `AutonomousHarness`) actually correct?**
  _`TorchlightApp` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `TieredMemory` (e.g. with `StreamingChatSession` and `AutonomousHarness`) actually correct?**
  _`TieredMemory` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `RLMEngineOptimized` (e.g. with `ConversationSummarizer` and `Message`) actually correct?**
  _`RLMEngineOptimized` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `MemoryConfig` (e.g. with `StreamingChatSession` and `ContextBudget`) actually correct?**
  _`MemoryConfig` has 24 INFERRED edges - model-reasoned connections that need verification._