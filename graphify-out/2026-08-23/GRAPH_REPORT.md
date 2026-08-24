# Graph Report - tourchlight v1_i6  (2026-08-23)

## Corpus Check
- 267 files · ~246,891 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4526 nodes · 9250 edges · 270 communities (219 shown, 51 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 820 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4327c5f9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TorchlightApp
- core/execution/__init__.py
- TieredMemory
- RecoveryEngine
- rlm_engine_optimized.py
- test_robust_task_tracking.py
- context_manager/memory/models.py
- implementations.py
- TaskDAG
- MemoryObject
- ContextDashboard
- test_code_quality_harness.py
- on
- BaseSkill
- Message
- RLMEngineOptimized
- TokenCounter
- DeduplicationEngine
- get_tool_registry
- ProjectMemory
- TestRunResult
- config.py
- TokenCounter
- android_ref_build.md
- app.js
- ProjectSnapshot
- SymbolIndex
- test_implementations.py
- ToolRegistry
- test_tui_command_palette.py
- test_tui_diff_view.py
- test_errors.py
- Message
- UI Chat Improvements Plan - Minimal Context & Token Savings
- android_ref_runtime.md
- format.py
- DebateVerifier
- ExecutionFeedbackLoop
- InferenceParams
- LLMClient
- ApprovalModal
- CenterEmptyState
- SymbolIndex
- DirectiveTracker
- test_grammar_parse.py
- tool_edit_file_impl
- test_tui_accessibility.py
- TDDSkill
- .build
- test_tool_parser.py
- test_tui_image_viewer.py
- PlanningSkill
- android_ref_emulator.md
- ContextBudget
- ensure_project_initialized
- TrajectoryLock
- build_agent_memory_scratchpad_text
- test_tui_status_bar.py
- LMStudioClient
- verify_m1_setup.py
- test_model_normalization.py
- StreamingChatSession
- test_enhanced_web_tools.py
- Static
- test_multimodal_vision.py
- Torchlight Architecture
- ProjectGraph
- GitFileTree
- test_tui_transcript_widgets.py
- test_tools_core.py
- ToolCallCard
- CommandPalette
- ._stream_llm_with_retry
- Changelog
- VerbatimCompactor
- Torchlight Rust Port: Performance-Critical Paths
- ImageAttachmentCard
- AutonomousHarness
- VerbatimCompactor
- CloudClient
- main_optimized.py
- test_tui_plan_panel.py
- tui_app.py
- OllamaClient
- android_ref_adb.md
- .load_project_memory
- test_tui_context_breakdown.py
- context_manager/memory/persistence.py
- TranscriptView
- ._run_tests_internal
- TDDSkill
- android_ref_signing.md
- TaskSpec
- Issues Found
- test_turboquant_qwen3b.py
- classify_command
- PyASTVisitor
- ProjectMemory
- test_phase_detection.py
- test_tui_theme.py
- test_resizer.py
- Torchlight Excellence Roadmap
- context_manager/memory/embeddings.py
- Console
- test_surgical_task_verification.py
- model_tester_gui.py
- ActionEntry
- test_tui_file_tree.py
- AGENTS.md
- Checklist
- ._execute_tool_with_approval
- Prompt Templates for 7B Coder Models
- repl_sandbox.py
- test_timeout_retry.py
- Memory System Deep Dive
- _extract_markdown_skill_metadata
- Plan: Non-Security Improvements
- LlamaCppClient
- Execution Feedback Loop
- .format_l0_scratchpad
- test_tui_tool_cards.py
- TrajectoryLogger
- IndexVisitor
- Plan: UI Improvements — Torchlight Codex IDE
- Torchlight — Terminal AI Coding Agent
- ModalTestApp
- TestApp
- Context Manager CLI
- 🎮 Essential Game Mechanics Checklist
- Resource-Adaptive Features
- Execution-Flow Tracing Debugger
- anyio
- Data Flow
- Core Classes
- prompts_minimal.py
- types.py
- web_server.py
- .update_file
- Textual & Rich TUI Performance and Design Rules
- HTMLGameSkill
- context_manager/prompts.py
- PaneResizer
- ModalTestApp
- interactive_model_tester.py
- SkillResult
- start_optimized_local.sh
- TestApp
- tui.sh
- Graphify Codebase Exploration & Dependency Hard Rules
- Ponytail
- P1: Important Follow-On Work
- Future Improvements
- Improvement Recommendations by Resource Tier
- Torchlight Documentation
- run.sh
- test_repeated_edit_loop_fix.py
- setup_optimized.sh
- Ponytail
- Android Troubleshoot — Routing Layer
- Target Quality Tiers
- Compression System
- AgentMemoryWidget
- Memory Tiers
- Persistence
- opencode.json
- Code Cleaner Skill
- TestApp
- graphify.js
- .agents/AGENTS.md
- workflows/graphify.md
- ~350 tokens. Do NOT load other reference files in the same turn.
- Profile: Run -> Profile app -> Memory tab
- at android.app.Activity...          <- framework — ignore
- StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
- Context null in Fragment -> requireContext() (throws if detached, which is correct)
- implementation 'androidx.multidex:multidex:2.0.1'
- Never use StrictMode.allowThreadDiskReads() — it masks the bug
- context_manager/__init__.py
- core/__init__.py
- sync_workspace_tasks
- tui_widgets/__init__.py
- recovery.py
- test_goal_mode_process.py
- ConnectionPill
- AskUserModal
- core/tests/test_models.py
- prompts/__init__.py
- ._is_vision_supported
- command_palette.py
- PromptTextArea
- Flashlight
- iter_project_files
- ConceptTracker
- ._update_params
- check_memory
- .__init__
- ActionTracker
- test_plan_execution_loop.py
- test_engine_code_mode_setting
- context-manager-cli
- torchlight-core
- start_mlx_server.sh
- file_tree.py
- transcript.py
- Retrieval System
- TrajectoryRail
- RLMEngine
- _clean_and_parse_json
- task_tree.py
- .on_tool_executed
- test_autonomous_harness_pipeline.py
- TaskManagerModal
- run_gui.sh
- set_ctx_window
- command
- ._estimate_l0_tokens
- _extract_task_file_and_scope
- ToolValidationError
- thinking_block.py
- test_cli_plan_mode_session
- Schema Reference
- ._calculate_metadata_overhead
- test_engine_parse_markdown_json_block_fallback
- test_engine_parse_bracket_tool_calls
- test_engine_parse_direct_xml_attribute_tool_calls
- test_rlm_engine_plan_mode_normalization
- test_detect_phase_plan_mode_resilience
- test_detect_phase_plan_signals_in_unified_mode
- test_chat_mode_verification_gate_bypassed
- test_verification_gate_single_path_tool_template_and_anti_echo
- .get_locked_phase
- .set_execution_mode_callback
- test_ring_buffer_prompt_dedup_skip
- Panel
- SessionState
- ContextSnapshot
- Protocol
- Message
- MessageRole
- str
- MemoryObject
- SessionState
- HTMLParser
- Step
- Step
- Exception
- Step
- Message
- Message
- Horizontal
- TokenCounter

## God Nodes (most connected - your core abstractions)
1. `TorchlightApp` - 216 edges
2. `TieredMemory` - 174 edges
3. `RLMEngineOptimized` - 140 edges
4. `MemoryConfig` - 100 edges
5. `tool_edit_file_impl()` - 61 edges
6. `ExecutionFeedbackLoop` - 58 edges
7. `LlamaCppClient` - 55 edges
8. `CloudClient` - 48 edges
9. `SkillUploadModal` - 48 edges
10. `Step` - 45 edges

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

## Communities (270 total, 51 thin omitted)

### Community 0 - "TorchlightApp"
Cohesion: 0.03
Nodes (47): Remove raw tool payload dumps (Params:, Result:, Writing code to file: ...) and, sanitize_assistant_text(), test_sanitize_assistant_text(), A successful WRITE_FILE step mounts a DiffView card with real content., test_app_write_step_renders_diff_card(), anyio, Tests for Phase-5 tabbed editor split pane (open_file_tab, dirty marker, keyboar, test_close_file_tab_removes_from_open_tabs() (+39 more)

### Community 1 - "core/execution/__init__.py"
Cohesion: 0.05
Nodes (49): GameInputEvent, GameOutcomeResult, get_process_memory_mb(), HtmlGamePlayer, Path, HTML Game Inspector & Player Harness for Torchlight.  Provides autonomous playin, Autonomous HTML Game Harness & Dynamic Verifier.      Launches an ephemeral brow, Plays the HTML game for duration_ms while simulating inputs and checking frame d (+41 more)

### Community 2 - "TieredMemory"
Cohesion: 0.05
Nodes (68): MemoryConfig, Enable or disable semantic deduplication., Persist user preferences to project memory., Calculate remaining token budget headroom before reaching max_tokens threshold., Predict likely next tools based on current state., Tiered memory system with L0-L3 hierarchy:     - L0: Active prompt (current cont, Return list of (path, content) for pinned files., TieredMemory (+60 more)

### Community 3 - "RecoveryEngine"
Cohesion: 0.15
Nodes (17): get_recovery_hint(), Manages recovery strategies across the agentic loop.      Tracks per-error-type, Reset all retry state (e.g., on new conversation turn)., Reset retry state for a specific error., Return a one-line hint for the LLM on how to recover from this error., RecoveryEngine, test_recovery_engine_reset(), test_recovery_engine_escalation() (+9 more)

### Community 4 - "rlm_engine_optimized.py"
Cohesion: 0.07
Nodes (46): Conversation Summarizer for Torchlight.  Extracts key information from conversat, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, ContentType, ExecutionMode, MemoryEventType, MessageRole (+38 more)

### Community 5 - "test_robust_task_tracking.py"
Cohesion: 0.23
Nodes (11): Tests for robust task and status tracking in LLM context and TUI., test_compact_task_matrix_adaptive_rendering(), test_status_badges_and_boxes(), test_validate_task_transition(), _clean_task_text(), get_compact_task_matrix(), Validate if a task transition is valid according to the status state machine., Generate an ultra-compact visual Task Matrix for LLM context injection.     Adap (+3 more)

### Community 6 - "context_manager/memory/models.py"
Cohesion: 0.05
Nodes (49): ConversationSummarizer, DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer (+41 more)

### Community 7 - "implementations.py"
Cohesion: 0.07
Nodes (53): Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Th, _ddg_search(), _detect_doc_source(), _extract_identifiers(), _extract_symbols(), _git_run(), play_and_verify_game(), Any (+45 more)

### Community 8 - "TaskDAG"
Cohesion: 0.06
Nodes (39): Any, Enum, str, Robust Task Lifecycle and Directed Acyclic Graph (DAG) Engine for Torchlight.  P, Directed Acyclic Graph (DAG) for Task Lifecycle Management., Add a task node to the DAG after verifying cycle safety., Remove a node and strip references to it from dependencies and subtasks., Detect cycles using Kahn's topological sort algorithm. (+31 more)

### Community 9 - "MemoryObject"
Cohesion: 0.11
Nodes (30): build_embedder(), compute_tf_idf_score(), cosine_similarity(), Embedder, HybridEmbedder, HybridMemoryRetriever, _is_low_memory(), KeywordEmbedder (+22 more)

### Community 10 - "ContextDashboard"
Cohesion: 0.10
Nodes (7): ContextDashboard, Panel, Print sub-agent task progress to the console., Return a new ActionTracker bound to this dashboard's console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 11 - "test_code_quality_harness.py"
Cohesion: 0.06
Nodes (54): calculate_in_memory_diff(), Calculate exact lines added and deleted between two string buffers in RAM., Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_compile_gate_rejects_return_outside_function() (+46 more)

### Community 12 - "on"
Cohesion: 0.05
Nodes (15): DirectorySelected, FileSelected, FileActionModal, FolderPickerModal, on, Pressed, Selected, Submitted (+7 more)

### Community 13 - "BaseSkill"
Cohesion: 0.08
Nodes (26): ABC, BaseSkill, CalculatorSkill, create_default_registry(), GitSkill, _LazySkill, Skills — external / plugin capabilities.  Skills are DIFFERENT from core tools:, Evaluate a mathematical expression safely using Python's AST. (+18 more)

### Community 15 - "RLMEngineOptimized"
Cohesion: 0.09
Nodes (28): Verify _detect_phase always returns 'code' in Code Mode., test_code_mode_phase_detection_persistence(), Verify that when a model outputs markdown plan with pseudocode $ WRITE_FILE, it, test_parse_response_auto_intercepts_pseudocode_plan(), test_action_tag_braces_inside_string_values(), test_action_tag_no_json_args(), test_action_tag_unclosed_with_trailing_prose(), test_inline_interception_requires_explicit_file_or_header() (+20 more)

### Community 16 - "TokenCounter"
Cohesion: 0.07
Nodes (32): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing. (+24 more)

### Community 17 - "DeduplicationEngine"
Cohesion: 0.06
Nodes (30): ContentFingerprint, ContentFingerprinter, deduplicate_context(), DeduplicationEngine, DeduplicationStats, Semantic Deduplication Engine for Torchlight.  Provides content-aware deduplicat, Fingerprint explanatory content to track concepts explained., Identify similar content across turns using various similarity metrics. (+22 more)

### Community 18 - "get_tool_registry"
Cohesion: 0.05
Nodes (48): test_search_ast_schema_validation(), test_game_tools_registered(), Verify validate_tool_call auto-heals missing/misplaced path arguments for VIEW_I, test_tool_registry_and_schemas_view_image(), test_validate_tool_call_view_image_auto_healing(), test_edit_file_out_of_bounds_line_range_rejected(), test_edit_file_tail_ultra_compact_directive(), test_identical_old_new_text_preflight() (+40 more)

### Community 19 - "ProjectMemory"
Cohesion: 0.17
Nodes (7): ProjectMemory, Load user preferences from project memory., Save user preferences to project memory., Load deduplication cache from project memory., Save deduplication cache to project memory., Export current context profile and memory config to a file., Import context profile from a file and merge into project memory.

### Community 20 - "TestRunResult"
Cohesion: 0.13
Nodes (12): Re-export ExecutionFeedbackLoop and TestRunResult from shared core library core., Execution feedback loop for Torchlight., Enum, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Return True only if a run succeeded. Uses exit code as the authoritative, TestResultStatus, TestRunResult, Unit tests for ExecutionFeedbackLoop test lifecycle event callbacks and metadata (+4 more)

### Community 21 - "config.py"
Cohesion: 0.15
Nodes (13): ContextProfile, _detect_apple_silicon_ram(), _detect_chip(), get_context_profile(), Enum, Context window profiles with profile-specific budget allocations., Detect total RAM in GB on macOS., Auto-detect profile from context size. (+5 more)

### Community 22 - "TokenCounter"
Cohesion: 0.07
Nodes (30): count_tokens(), Count tokens in text., Manage saved sessions., sessions(), Re-export TieredMemory and MemoryConfig from shared core library core.memory.man, Load deduplication cache from project memory., Load user preferences from project memory., CompressionConfig (+22 more)

### Community 23 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 24 - "app.js"
Cohesion: 0.07
Nodes (33): appendResultRow(), appState, astBadge, btnClearHistory, btnCopyCode, btnExportJson, btnRefreshModels, btnRunTest (+25 more)

### Community 25 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 26 - "SymbolIndex"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 27 - "test_implementations.py"
Cohesion: 0.07
Nodes (42): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_read_symbols_indented_methods_and_duplicate_names(), test_run_command_intercept_ast_functions(), test_search_ast_action_aliases(), test_search_ast_after_writing_file(), test_search_ast_impl_fallback(), test_verify_compile_param(), test_edit_file_impl() (+34 more)

### Community 28 - "ToolRegistry"
Cohesion: 0.08
Nodes (26): test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command(), test_tool_result_failure(), test_tool_result_success() (+18 more)

### Community 29 - "test_tui_command_palette.py"
Cohesion: 0.22
Nodes (12): anyio, Tests for Phase-4 command palette + prompt autocomplete., test_add_context_chip_image_prefix(), test_command_palette_composes_filters_and_selects(), test_command_palette_enter_runs_highlighted_item(), test_fuzzy_filter_empty_query_and_no_match(), test_fuzzy_filter_prefix_beats_substring(), test_prompt_text_area_enter_submits_and_accepts_suggestion() (+4 more)

### Community 30 - "test_tui_diff_view.py"
Cohesion: 0.11
Nodes (31): anyio, Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)., A pre-write snapshot (from approval) wins over the already-written disk state., The engine's own CODE_FILE_WRITE approval path is diffable too., The approval modal shows a DIFF PREVIEW section when entries exist., test_approval_modal_omits_diff_when_empty(), test_approval_modal_renders_diff(), test_build_diff_preview_code_file_write() (+23 more)

### Community 31 - "test_errors.py"
Cohesion: 0.14
Nodes (16): ConnectionError, ParseError, Exception, Base error with structured context., Tool execution failed., LLM output could not be parsed into a valid tool call or response., LLM backend unreachable., ToolError (+8 more)

### Community 32 - "Message"
Cohesion: 0.05
Nodes (28): extract_modified_symbols(), is_valid_file_path(), Path, Run semantic deduplication on current message history.                  Args:, Persist deduplication cache to project memory., Record an explicit memory entry into SessionState and persist to project memory., Trim SessionState lists to configured maximum to prevent unbounded growth., Explicitly record a modified file, Net Delta line stats, and touched symbols in (+20 more)

### Community 33 - "UI Chat Improvements Plan - Minimal Context & Token Savings"
Cohesion: 0.05
Nodes (36): 1.1 Rich Message Card Component, 1.2 Streaming Experience Improvements, 1.3 Transcript Container Enhancements, 1. Message Rendering & Formatting (Claude Code-like Experience), 2.1 Content Fingerprinting System, 2.2 Deduplication-Aware Compression, 2.3 Tool Result Deduplication, 2. Semantic Deduplication for Token Savings (+28 more)

### Community 34 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 35 - "format.py"
Cohesion: 0.10
Nodes (32): get_skill_directories(), Return candidate directories containing skills in priority order:     1. <worksp, discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any (+24 more)

### Community 36 - "DebateVerifier"
Cohesion: 0.09
Nodes (23): Adversarial critique / debate. Focused flaw identification., Synthesis and refinement following critique. Deterministic., Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., CritiqueResult, DebateVerifier, DebateVerifier implementation: orchestrates adversarial critique and refinement, Synthesize refined output incorporating valid critiques using InferenceParams.fo (+15 more)

### Community 37 - "ExecutionFeedbackLoop"
Cohesion: 0.09
Nodes (32): ExecutionFeedbackLoop, extract_surgical_traceback(), Auto-run tests and web outcome inspection after code changes and inject feedback, Convert current failing TestRunResult into a structured TestFailureError for Rec, Build feedback context string for the LLM with surgical error injection., Extract strictly surgical failure traceback from test output, removing passing t, Project with nothing to verify must not trip the verification gate., A stored non-run must never be reported as failing, regardless of exit code. (+24 more)

### Community 38 - "InferenceParams"
Cohesion: 0.07
Nodes (27): detect_model_traits(), InferenceParams, Detect architecture traits (size, reasoning status, vision capability) from mode, One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters., Reasoning through plans. Moderate creativity. All tools remain available., Diagnosing errors. Slightly more exploration. (+19 more)

### Community 39 - "LLMClient"
Cohesion: 0.08
Nodes (22): LLMClient, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Send messages and return the full response., Send messages and yield response chunks., Check if the backend is reachable., List available models., Simple query interface (for backward compatibility). (+14 more)

### Community 40 - "ApprovalModal"
Cohesion: 0.04
Nodes (33): NamedTuple, AgentStatusModal, ApprovalModal, CopySelectionModal, EditorTab, MouseDown, Modal dialog to select and copy specific messages, code blocks, or text turns., Modal dialog for complete visibility into background agent actions & status tele (+25 more)

### Community 41 - "CenterEmptyState"
Cohesion: 0.18
Nodes (7): CenterEmptyState, Container, Pressed, CenterEmptyState — the welcome / idle screen shown in the editor pane.  Replaces, Switch displayed content based on connection state., Route chip buttons to app-level actions., Full-pane empty state widget for the editor / center area.      Mount this insid

### Community 42 - "SymbolIndex"
Cohesion: 0.15
Nodes (9): BeamResult, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build() (+1 more)

### Community 43 - "DirectiveTracker"
Cohesion: 0.16
Nodes (9): DirectiveTracker, Any, Directive tracker and constraint violation reinforcement module for Torchlight., Record a directive violation (e.g. 'cd_command', 'test_assertion_delete'), Reset violation counts., Tracks model constraint violations during execution turns and dynamically     in, Unit tests for CRITICAL_DIRECTIVES system prompt lock and DirectiveTracker., test_critical_directives_in_system_prompt() (+1 more)

### Community 44 - "test_grammar_parse.py"
Cohesion: 0.11
Nodes (29): _code_lines(), _grammar_text(), _grammar_tool_names(), _parse_rules(), Regression guard for the TurboQuant GBNF grammar-parser incompatibility.  The Tu, Return ``body`` up to (but not including) a top-level '#' comment,     ignoring, Map rule name -> raw (comment-stripped) rule body., TurboQuant parser rejects rule continuations that START with '|'. (+21 more)

### Community 45 - "tool_edit_file_impl"
Cohesion: 0.07
Nodes (47): Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_allows_shorter_content_with_force(), test_edit_file_auto_fallback_to_write(), test_edit_file_auto_strips_read_file_line_numbers(), test_edit_file_copied_line_numbers_in_new_text_stripped(), test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_disambiguates_multi_match_via_start_line() (+39 more)

### Community 46 - "test_tui_accessibility.py"
Cohesion: 0.10
Nodes (28): _make_app(), anyio, Tests for Phase-6 accessibility and keyboard navigation.  Covers: - Tab bar keyb, Arrow navigation wraps around at the ends., Arrow keys don't do anything when no tabs are open., Verify :focus rules exist for tab items in the .tcss file., Verify responsive @media-equivalent class rules exist., Verify no #hex color values appear in the .tcss file. (+20 more)

### Community 47 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 48 - ".build"
Cohesion: 0.14
Nodes (10): Any, Scan project files incrementally using st_mtime and construct/update the AST gra, Remove all nodes and edges referencing a deleted file., Save graph data to JSON and markdown report., Load graph from JSON file if available., Search nodes matching search_term. Returns code snippets alongside names., Extract up to _MAX_SNIPPET_LINES lines for preview in graph query., Find relationship path between source and target symbols. (+2 more)

### Community 49 - "test_tool_parser.py"
Cohesion: 0.07
Nodes (44): Unit tests for core/tools/parser.py tolerant tool parser & fuzzy repair engine., test_extract_balanced_json_object(), test_parse_bare_markdown_json_and_truncated_content(), test_parse_tool_call_payload(), test_repair_unclosed_action_tags(), test_repair_unclosed_tool_call_tag(), test_single_quoted_dict_parsing(), test_strip_interleaved_prose() (+36 more)

### Community 50 - "test_tui_image_viewer.py"
Cohesion: 0.10
Nodes (26): anyio, fixture, Tests for TUI ImageViewer, BinaryFileViewer, and ImageAttachmentCard.  Verifies:, Create a temporary PNG image file for testing., Test save_clipboard_image when PIL ImageGrab returns a PIL Image., Test save_clipboard_image when PIL ImageGrab returns list of copied file paths., Test save_clipboard_image when clipboard is empty / contains no image., Test PromptTextArea pasting image path or clipboard image emits ContextFileAttac (+18 more)

### Community 51 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 52 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 53 - "ContextBudget"
Cohesion: 0.10
Nodes (12): _clamp(), ContextBudget, Adaptive, headroom-driven context budget coordinator for Torchlight.  Static res, Token reserve kept for the recent-message window., Current fraction of the target window in use., Effective budget allocations for the current turn.      `used_tokens` is the liv, Token allowance for the L0 working memory scratchpad this turn., Max characters per scratchpad entry (longer when headroom is ample). (+4 more)

### Community 54 - "ensure_project_initialized"
Cohesion: 0.09
Nodes (25): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, Ensure target project directory exists and has a local Git repository initialize, Write a marker proving the harness itself initialized this git repo.      Only w, Ensure target project directory exists and has `.context-memory.json` persistent, Explicitly initialize a new project directory with both persistent memory files (+17 more)

### Community 55 - "TrajectoryLock"
Cohesion: 0.11
Nodes (24): Unit tests for core/tools/dedup.py argument normalization & TrajectoryLock., test_compute_payload_hash(), test_duplicate_new_text_payload_blocked(), test_edit_file_alternate_trajectory_hint(), test_normalize_tool_args(), test_sequential_1line_edit_stepping_blocked(), test_sequential_range_stepping_blocked(), test_trajectory_lock() (+16 more)

### Community 56 - "build_agent_memory_scratchpad_text"
Cohesion: 0.15
Nodes (13): Verify that square brackets and special markup characters in code/errors are esc, Empty memory renders a clean, friendly idle state., Verify long error messages are preserved in full without 75-char ellipsis trunca, Scratchpad formats structured SessionState into distinct, styled UI cards., Scratchpad gracefully falls back to parsing raw prompt strings., test_scratchpad_empty_state(), test_scratchpad_escapes_rich_special_characters(), test_scratchpad_parses_raw_prompt_string() (+5 more)

### Community 57 - "test_tui_status_bar.py"
Cohesion: 0.15
Nodes (18): anyio, Tests for Phase-4 consolidated status bar (gauge + segments widget)., test_build_status_segments_defaults(), test_build_status_segments_populated(), test_build_status_segments_running_no_tps_yet(), test_build_status_segments_server_offline_and_branch_escape(), test_gauge_markup_clamps_out_of_range(), test_gauge_markup_color_escalation() (+10 more)

### Community 58 - "LMStudioClient"
Cohesion: 0.11
Nodes (12): Re-export LMStudioClient from shared core library core.api.lmstudio., _friendly_timeout_msg(), get_phase_inference_params(), LMStudioClient, LM Studio REST client.  Recovered from the original CLI implementation (commit f, Synchronous streaming generator — yields tokens one-by-one.          Uses DEFAUL, Async streaming generator. Uses per-chunk read timeout (DEFAULT_TIMEOUT)., Simple synchronous query interface (LLMClient protocol compatibility). (+4 more)

### Community 59 - "verify_m1_setup.py"
Cohesion: 0.32
Nodes (15): check_hardware(), check_inference(), check_llama_server_binary(), check_model(), check_server_health(), fail(), info(), main() (+7 more)

### Community 60 - "test_model_normalization.py"
Cohesion: 0.15
Nodes (18): test_format_model_display_names(), test_is_valid_mlx_directory(), test_list_available_draft_models(), test_list_available_models_includes_gemma(), test_normalize_gemma_2_and_3_variants(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), format_model_display_name() (+10 more)

### Community 61 - "StreamingChatSession"
Cohesion: 0.16
Nodes (9): get_phase_system_prompt(), Build the final message list for the LLM, respecting the context budget., /params                    — show current params         /params auto, Re-append closing tags and unclosed JSON braces that were consumed as stop token, Auto-switch _params based on detected phase.  No-op when locked., Run out-of-band DebateVerifier pass if candidate proposal needs verification., Step function for AutonomousHarness - executes a single task iteration., Async implementation of harness step function. (+1 more)

### Community 62 - "test_enhanced_web_tools.py"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 63 - "Static"
Cohesion: 0.06
Nodes (27): DirectoryTree, Horizontal, EngineConfigModal, ComposeResult, VerticalScroll, Modal dialog for selecting Inference Engine and TurboQuant KV Cache mode., Get model choices tailored to the selected inference backend., Modal dialog displaying keyboard shortcuts and slash commands. (+19 more)

### Community 64 - "test_multimodal_vision.py"
Cohesion: 0.07
Nodes (54): Any, Convert Message to provider-compatible API payload dictionary., fixture, Path, Unit and integration tests for multimodal vision capabilities (Gemma 3, Qwen VL,, Verify Message.to_dict generates rich text description when vision_supported is, Verify format_image_text_summary extracts metadata and embeds exact calling cont, Create a minimal 1x1 valid PNG image. (+46 more)

### Community 65 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 66 - "ProjectGraph"
Cohesion: 0.18
Nodes (20): get_project_graph(), ProjectGraph, Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Get or create the ProjectGraph instance for a given root directory., Incrementally update the AST graph for a single modified file., update_project_graph_file(), Unit tests for incremental O(1) AST graph delta updates. (+12 more)

### Community 67 - "GitFileTree"
Cohesion: 0.17
Nodes (12): DirEntry, FileRightClicked, GitFileTree, Click, MouseDown, Path, Filter out OS noise, cache directories, and internal state files., DirectoryTree whose file labels carry git status decorations. (+4 more)

### Community 68 - "test_tui_transcript_widgets.py"
Cohesion: 0.14
Nodes (19): anyio, Tests for Phase-1 transcript widgets (message cards, streaming, thinking)., Smoke test: the real app mounts MessageCards and drives the streaming view., Verify MessageCard copy and reuse actions work for user and assistant messages., Verify MessageCard duration formatting, empty user headers, and timestamp overri, test_app_transcript_wiring(), test_card_meta_for(), test_estimate_token_count() (+11 more)

### Community 69 - "test_tools_core.py"
Cohesion: 0.13
Nodes (18): CoreToolRegistry, get_core_registry(), Any, Compatibility subclass of ToolRegistry providing CLI-specific execute/dangerous_, test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command() (+10 more)

### Community 70 - "ToolCallCard"
Cohesion: 0.15
Nodes (8): Any, Click, on, A status-aware tool call card.      Header shows the risk-tier icon, tool name,, Derive target file path, AST search query, or command from tool args., Refresh the elapsed counter while the tool is still running., Flip the card from running to done and fill params + output.          Re-derives, ToolCallCard

### Community 71 - "CommandPalette"
Cohesion: 0.11
Nodes (9): Highlighted, AttachContextModal, CommandPalette, Changed, on, Selected, Submitted, Ctrl+P modal: fuzzy-search actions, slash commands, and files. (+1 more)

### Community 72 - "._stream_llm_with_retry"
Cohesion: 0.14
Nodes (7): Notify listeners of real-time background status and action telemetry., Notify listeners (dashboard/TUI) that task state changed after a tool call., Truncate any trailing rambling/hallucinated text after the first closed action t, Re-append closing tags that were consumed as stop tokens by llama-server,, Stream LLM response token-by-token cleanly without thread deadlocks., True when an LLM error string looks like a transient server stall that         a, Stream an LLM response, retrying up to ``retries`` times on transient         se

### Community 73 - "Changelog"
Cohesion: 0.06
Nodes (34): Added, Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+26 more)

### Community 74 - "VerbatimCompactor"
Cohesion: 0.14
Nodes (6): CompressionConfig, Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 75 - "Torchlight Rust Port: Performance-Critical Paths"
Cohesion: 0.10
Nodes (20): 1. `token_counter` → `torchlight_core::token_counter` (Week 1), 2. `flashlight/indexer.py` → `torchlight_core::ast_indexer` (Week 2), 3. `graph_engine.py` → `torchlight_core::graph_engine` (Week 3), 4. `memory/manager.py` → `torchlight_core::memory::tiered` (Week 4), 5. `memory/selective_compression.py` → `torchlight_core::memory::selective` (Week 5), 6. `memory/budget.py` → `torchlight_core::memory::budget` (Week 5), 7. `compression/summarizer.py` → `torchlight_core::compression::summarizer` (Week 6), 8. `tools/parser.py` → `torchlight_core::tools::parser` (Week 6) (+12 more)

### Community 76 - "ImageAttachmentCard"
Cohesion: 0.26
Nodes (4): ImageAttachmentCard, Click, on, Visual card displaying image metadata and a 24-bit ANSI terminal color preview.

### Community 77 - "AutonomousHarness"
Cohesion: 0.25
Nodes (18): AutonomousHarness, HarnessConfig, Path, Ensure target project has local git repository and persistent memory initialized, Autonomous Harness Engine driving long-running continuous execution., main(), create_mock_feedback_loop(), Path (+10 more)

### Community 78 - "VerbatimCompactor"
Cohesion: 0.11
Nodes (15): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, ConversationSummarizer, Message, Summarize conversation turns for compression using high-density structured templ, Generate a high-density structured compaction template preserving key context in (+7 more)

### Community 79 - "CloudClient"
Cohesion: 0.12
Nodes (10): CloudClient, _HttpxOpenAIChatCompletions, _HttpxOpenAIClient, _HttpxOpenAIModels, Return the ids of models the provider currently reports as available.         Us, Resolve requested self.model against live models to prevent 404 mismatches., Sanitize message roles. Convert system role to user role for models (e.g. Gemma), Async implementation of chat protocol method required by LLMClient and DebateVer (+2 more)

### Community 80 - "main_optimized.py"
Cohesion: 0.19
Nodes (20): Panel, create_client(), display_step(), get_depth_style(), main(), amain(), approval_prompt(), create_client() (+12 more)

### Community 81 - "test_tui_plan_panel.py"
Cohesion: 0.14
Nodes (20): Verify TUI format helpers render CODE MODE badge with task checklist., test_code_mode_badge_in_tui_format(), _build_plan_text(), _make_app(), anyio, Delegate to the real TUI plan-builder helper., Verify build_plan_text handles bulleted plan lists without explicit checkboxes., Repeated checklist entries (summary + detailed sections) must not duplicate. (+12 more)

### Community 82 - "tui_app.py"
Cohesion: 0.05
Nodes (36): Infer the current agent phase from user input and the last model response., test_parse_plan_review_questions_radio_and_checkbox(), parse_plan_review_questions(), Utilities for parsing structured implementation plans and review questions., Parse structured review questions with radio/checkbox options from a markdown pl, fetch_provider_models(), is_port_in_use(), Query an OpenAI-compatible /models endpoint (LM Studio, Ollama, llama.cpp)     o (+28 more)

### Community 83 - "OllamaClient"
Cohesion: 0.22
Nodes (4): _normalize_messages_for_ollama(), OllamaClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.

### Community 84 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 85 - ".load_project_memory"
Cohesion: 0.50
Nodes (3): _is_valid_decision(), Filter out empty, generic, or noisy session summary strings., Load persistent project memory (.context-memory.json) into L0 working state.

### Community 86 - "test_tui_context_breakdown.py"
Cohesion: 0.40
Nodes (4): Unit tests for context breakdown performance and TUI on-demand trigger., test_context_breakdown_sections_and_accuracy(), test_total_tokens_performance_o1(), test_tui_breakdown_toggle_state()

### Community 87 - "context_manager/memory/persistence.py"
Cohesion: 0.29
Nodes (5): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, SessionPersistence

### Community 88 - "TranscriptView"
Cohesion: 0.11
Nodes (11): VerticalScroll, Bounded scroll container hosting the transcript.      Encapsulates the 120-child, Clear all cards from the transcript., Mount a card, prune the oldest when over the cap, and scroll., Scroll the transcript to the bottom without animation., Navigate up (vim-style)., Navigate down (vim-style)., Focus a specific card by index. (+3 more)

### Community 89 - "._run_tests_internal"
Cohesion: 0.14
Nodes (10): Any, Path, Register a callback for test lifecycle events (e.g. 'test_started', 'test_comple, Safely invoke registered event callback., Run fast pre-flight auto-fixer/linter on modified files before test execution., Store test result and dispatch UI notification event if tests were executed., Detect and run the project's test suite or web inspector., TestResult (+2 more)

### Community 90 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 91 - "android_ref_signing.md"
Cohesion: 0.12
Nodes (16): ~200 tokens. Do NOT load other reference files in the same turn., Android Signing Reference — Keystore, Certificates, Google Play, app/build.gradle:, Common errors, Enroll: Play Console -> App -> Setup -> App signing, Generate a new debug keystore (if lost), Google manages the release key; you upload with a separate upload key, Google Play App Signing (recommended) (+8 more)

### Community 92 - "TaskSpec"
Cohesion: 0.10
Nodes (13): GoalSpec, Enum, str, Ensure a goal spec exists on disk in .torchlight, initializing a default workspa, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks., Construct inter-task memory prompt summarizing prior verified tasks and dependen, Run a single micro-epoch for a target task. (+5 more)

### Community 93 - "Issues Found"
Cohesion: 0.12
Nodes (16): 1. **ExecutionMode Enum Mismatch**, 2. **Phase Detection Not Integrated with Goal Mode**, 3. **Goal Spec Initialization Race Condition**, 4. **Missing Verification Gate in CLI Goal Mode**, 5. **AutonomousHarness Not Wired to LLM Engine in CLI**, 6. **Inconsistent ExecutionMode Default**, 7. **Memory State Sync Issues**, Fix Plan (+8 more)

### Community 94 - "test_turboquant_qwen3b.py"
Cohesion: 0.17
Nodes (13): BenchmarkResult, get_process_rss_mb(), LlamaCppTurboRunner, main(), MlxTurboRunner, Run micro-benchmark via llama-bench (measures raw Metal kernel throughput)., Run real code generation using llama-cli and test Python AST syntax., Run token generation with MLX Quantized KV Cache. (+5 more)

### Community 95 - "classify_command"
Cohesion: 0.18
Nodes (15): test_classify_confirm_commands(), test_classify_destructive_commands(), test_classify_empty_command(), test_classify_safe_commands(), test_classify_unknown_defaults_to_confirm(), test_classify_whitespace_handling(), test_risk_for_tool(), classify_command() (+7 more)

### Community 96 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 97 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 98 - "test_phase_detection.py"
Cohesion: 0.12
Nodes (24): _make_session(), asyncio, Troubleshoot wins over code when both signals are present in unified mode., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., Verify that in Goal Mode with no implementation_plan.md, _generate_response reje, Verify that when session is explicitly in Chat Mode, _detect_phase returns 'chat, Create a StreamingChatSession with mocked heavy dependencies. (+16 more)

### Community 99 - "test_tui_theme.py"
Cohesion: 0.18
Nodes (15): _make_app(), anyio, Tests for Phase-6 theme consistency and responsive layout classes.  Covers: - CS, Ensure CSS doesn't contain hardcoded hex colors., Ensure CSS uses theme variables like $background., Ensure CSS has rules for responsive terminal classes., Responsive classes are applied when terminal is narrow., Short-terminal class applied when height < 24. (+7 more)

### Community 100 - "test_resizer.py"
Cohesion: 0.26
Nodes (15): _build_app(), _click_resizer(), _drag_resizer(), Regression tests for the PaneResizer drag/click resizing in tui_app.py.  The Pan, No-op client so the engine never touches LM Studio / Ollama / cloud., Simulate a real drag: mouse_down -> captured MouseMove -> mouse_up., _resize_to(), _start_app() (+7 more)

### Community 101 - "Torchlight Excellence Roadmap"
Cohesion: 0.13
Nodes (15): 1. Execution Policy Router, 1. Smarter Retrieval, 2. Adaptive Prompt Compression, 2. Explicit Working-Set Builder, 3. Stronger Action Extraction, 4. Provider and Model Truth Model, 4. Terminal UX Polish, 5. Failure-Classified Retries (+7 more)

### Community 102 - "context_manager/memory/embeddings.py"
Cohesion: 0.21
Nodes (9): build_embedder(), Embedder, FallbackEmbedder, HashEmbedder, _normalize(), ProviderEmbedder, any, Protocol (+1 more)

### Community 103 - "Console"
Cohesion: 0.24
Nodes (7): Console, test_render_task_progress_empty(), test_render_task_progress_with_tasks(), test_action_entry_markup_safety(), test_action_tracker_print_action_safety(), test_escape_raw_brackets_and_json(), test_tui_markup_escaping_safety()

### Community 104 - "test_surgical_task_verification.py"
Cohesion: 0.24
Nodes (11): Unit tests for Surgical Targeted Task Verification in Torchlight., test_verify_task_preflight_invalid_json(), test_verify_task_preflight_syntax_error(), test_verify_task_preflight_valid_python(), test_verify_task_targeted_command(), _find_file_in_project(), Locate a file by basename in the project, skipping junk/venv dirs., Zero-overhead in-memory syntax validation (<5ms).     Checks Python files with a (+3 more)

### Community 105 - "model_tester_gui.py"
Cohesion: 0.17
Nodes (13): execute_llama_run(), execute_mlx_run(), Any, Validate python code block syntax., Execute llama-completion generation with custom TurboQuant / KV mode., Execute MLX generation in venv_mlx environment., Scan local models directory and HuggingFace/LMStudio caches for models., Start local Studio GUI server. (+5 more)

### Community 106 - "ActionEntry"
Cohesion: 0.29
Nodes (3): ActionEntry, A single recorded action with its status and elapsed time., Text

### Community 107 - "test_tui_file_tree.py"
Cohesion: 0.15
Nodes (13): _FakeProc, anyio, Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)., test_git_tree_decorates_file_labels(), test_git_tree_right_click_posts_message(), test_normalize_status_code(), test_parse_git_status_porcelain_basic(), test_parse_git_status_porcelain_quoted_path() (+5 more)

### Community 108 - "AGENTS.md"
Cohesion: 0.14
Nodes (13): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Hard Rules, Commands, Context Budget Breakdown, Deterministic Trajectory & SLM Reliability Hard Rules (99%+ Accuracy for Small Models) (+5 more)

### Community 109 - "Checklist"
Cohesion: 0.15
Nodes (13): 1. Slash Command Verification, 2. Runtime Hardening, 3. Process Hygiene, 4. Provider and Model Verification, 5. Local-Model Efficiency, 6. Context-Rot and Memory Durability, 7. Retry And Cancel Semantics, Already Completed (+5 more)

### Community 110 - "._execute_tool_with_approval"
Cohesion: 0.17
Nodes (7): ActionTracker, Lock phase based on concrete execution events., _risk_tier(), _tool_kind(), _tool_label(), Return True if the most recent test run actually ran and has failing or, Build an explicit warning attached to an accepted final answer when the

### Community 111 - "Prompt Templates for 7B Coder Models"
Cohesion: 0.13
Nodes (14): Breaking Complex Tasks into Chained Prompts, General Rules for 7B Models, Key Characteristics of 7B Models, Prompt Pattern: Chained Development, Prompt Templates for 7B Coder Models, Structure, Structure, Structure (+6 more)

### Community 112 - "repl_sandbox.py"
Cohesion: 0.16
Nodes (18): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+10 more)

### Community 113 - "test_timeout_retry.py"
Cohesion: 0.17
Nodes (14): Exception, _bare_engine(), _FailingStreamEngine, Unit tests for transient LLM timeout/connection retry behavior in the solve loop, Construct an engine without the heavy __init__ (client/sandbox setup)., Engine whose _stream_llm fails transiently N times then succeeds., test_backoff_grows_exponentially(), test_classifies_fatal_errors_as_non_transient() (+6 more)

### Community 114 - "Memory System Deep Dive"
Cohesion: 0.15
Nodes (12): Allocation for 4k Context, Architecture Overview, Auto-tuned Budgets by Context Size, Auto-tuning, CLI Integration, Configuration Commands, Configuration Commands, File Locations (+4 more)

### Community 115 - "_extract_markdown_skill_metadata"
Cohesion: 0.15
Nodes (13): _extract_markdown_skill_metadata(), MarkdownDocumentSkill, parse_frontmatter(), Splits a markdown file into (metadata_dict, body_markdown).     Gracefully falls, Lightweight skill backed by SKILL.md.      This lets users add modular markdown, Extract (skill_name, description, icon, risk_level, category, tags) from a markd, asyncio, Path (+5 more)

### Community 116 - "Plan: Non-Security Improvements"
Cohesion: 0.17
Nodes (11): Decisions, Out of Scope, Plan: Non-Security Improvements, Task 1: Frontend Consolidation, Task 2: Split `implementations.py` into Sub-Modules, Task 3: Cache `SymbolIndex` Across Micro-Epochs, Task 4: Extract Tool Execution Pipeline, Task 5: Fix Error Handling Gaps (+3 more)

### Community 117 - "LlamaCppClient"
Cohesion: 0.09
Nodes (20): test_llamacpp_client_503_loading_model_auto_wait(), test_llamacpp_client_503_streaming_auto_wait(), test_llamacpp_client_stream_repetition_breaker(), Verify _strip_multimodal_images flattens image_url blocks into text., test_llamacpp_client_multimodal_image_stripping(), HTTPError, _context_limit_message(), _is_model_loading_error() (+12 more)

### Community 118 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

### Community 119 - ".format_l0_scratchpad"
Cohesion: 0.13
Nodes (10): ContextBudget, Build the message list for the LLM.          Pinned files and dynamic L0 Scratch, Format current SessionState into a dynamic L0 working memory scratchpad., Build critical context block from session state., Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length., Return headroom-aware budget allocations for the current turn., Pin a recently-read file slice so it survives compression without bloating conte, Remove a file from pinned memory if deleted or stale. (+2 more)

### Community 120 - "test_tui_tool_cards.py"
Cohesion: 0.13
Nodes (22): anyio, Tests for Phase-2 tool call cards (risk badge, status, timing, sections)., The streamed <tool_call> mounts a pending card completed by the step., Verify tool calls with <= 10 lines of output default to expanded., Verify tool calls with > 10 lines of output default to collapsed., Verify ToolCallCard.action_copy extracts result/payload and triggers copy., test_app_pending_card_wiring(), test_summarize_args() (+14 more)

### Community 121 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 122 - "IndexVisitor"
Cohesion: 0.27
Nodes (4): index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings.

### Community 123 - "Plan: UI Improvements — Torchlight Codex IDE"
Cohesion: 0.18
Nodes (10): Decisions, Effort & Sequencing, Non-Goals, Plan: UI Improvements — Torchlight Codex IDE, Task 1: Fix Latent Bugs (prerequisite), Task 2: Phase 5 — Tabbed Editor Split Pane, Task 3: Phase 6a — Accessibility & Focus Management, Task 4: Phase 6b — Performance & Streaming Polish (+2 more)

### Community 124 - "Torchlight — Terminal AI Coding Agent"
Cohesion: 0.18
Nodes (11): Architecture, CLI Commands, Core Flow, Development, Error Handling, Key Features, Memory Files, Module Structure (+3 more)

### Community 125 - "ModalTestApp"
Cohesion: 0.25
Nodes (6): ModalTestApp, App, asyncio, ComposeResult, Pressed, test_skill_upload_modal()

### Community 126 - "TestApp"
Cohesion: 0.22
Nodes (5): App, ComposeResult, on, Pressed, TestApp

### Community 127 - "Context Manager CLI"
Cohesion: 0.20
Nodes (9): Architecture, CLI Options, Commands (in CLI), Context Manager CLI, Features, How It Works, Installation, Requirements (+1 more)

### Community 128 - "🎮 Essential Game Mechanics Checklist"
Cohesion: 0.20
Nodes (9): 1. Fixed Timestep Loop, 2. Input Handling & 180° Lock, 3. Zero-Dependency Web Audio Synth, 4. Particle Effects Engine, 🕹️ Architecture & Core Standards, 🎮 Essential Game Mechanics Checklist, 🚀 Generation Workflow, HTML5 / CSS / JS Snake Game Builder Skill (+1 more)

### Community 129 - "Resource-Adaptive Features"
Cohesion: 0.29
Nodes (7): Compression Cooldown, Embedding Cache, LLM State Extraction, Resource-Adaptive Configuration, Resource-Adaptive Features, Resource Tiers, Tool Result Budget

### Community 130 - "Execution-Flow Tracing Debugger"
Cohesion: 0.08
Nodes (23): Anti-Patterns (What This Skill Prevents), AST-first for large codebases, Core Principle, Example: Empty Answer Card After LLM Agent Loop, Execution-Flow Tracing Debugger, Hard Rules, Instrument with breadcrumbs, Multi-Component Trace Patterns (+15 more)

### Community 131 - "anyio"
Cohesion: 0.22
Nodes (9): anyio, Verify that in Plan Mode, tool executions targeting non-plan files (e.g. index.h, Verify that ASK_USER delegates to engine.ask_user_fn when registered., Verify that in Plan Mode, pending - [ ] tasks in implementation_plan.md do not b, Verify that in Plan Mode with no implementation_plan.md, premature FINAL_ANSWER, test_ask_user_fn_modal_delegation(), test_plan_mode_guard_blocks_non_plan_files(), test_solve_async_plan_mode_allows_final_answer_with_pending_tasks() (+1 more)

### Community 132 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 133 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 134 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 135 - "types.py"
Cohesion: 0.17
Nodes (11): ContextOverflowError, Enum, Structured error types for Torchlight.  Every error carries context for automate, Post-edit auto-run test suite failure., What the recovery engine should do after an error., Context window exceeded., Path or command outside allowed scope., RecoveryAction (+3 more)

### Community 136 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 137 - ".update_file"
Cohesion: 0.32
Nodes (3): Path, Parse file via Tree-Sitter when tree_sitter library is installed., Perform an incremental O(1) AST update for a single modified file.

### Community 138 - "Textual & Rich TUI Performance and Design Rules"
Cohesion: 0.29
Nodes (6): 1. Widget Border & Alignment Discipline, 2. Modal Backdrop Opacity, 3. High-Performance Log Rendering, 4. Telemetry & Disk I/O Throttling, 5. Renderable AST Caching & Adaptive Streaming, Textual & Rich TUI Performance and Design Rules

### Community 139 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

### Community 140 - "context_manager/prompts.py"
Cohesion: 0.29
Nodes (4): verify_cli_prompt(), build_default_system_prompt(), Torchlight prompt stack — single source of truth.  V2: Optimized for local LLMs, Build system prompt. Use V2 for small contexts.

### Community 141 - "PaneResizer"
Cohesion: 0.17
Nodes (5): MouseMove, MouseUp, PaneResizer, Click, Interactive splitter bar to resize the left/right side panes.      Drag the bar

### Community 143 - "ModalTestApp"
Cohesion: 0.25
Nodes (6): ModalTestApp, App, asyncio, ComposeResult, Pressed, test_skill_upload_modal()

### Community 144 - "interactive_model_tester.py"
Cohesion: 0.23
Nodes (15): BenchmarkRecord, interactive_menu(), main(), Path, Validate python code block syntax., Run llama-bench throughput evaluation., Run MLX generation in venv_mlx environment., Render comparison results table. (+7 more)

### Community 145 - "SkillResult"
Cohesion: 0.13
Nodes (10): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi, Any, ReproSkill, Any, Synchronous wrapper for use from non-async contexts., Trigger real load on first call, then delegate. (+2 more)

### Community 146 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

### Community 147 - "TestApp"
Cohesion: 0.33
Nodes (3): App, ComposeResult, TestApp

### Community 148 - "tui.sh"
Cohesion: 0.40
Nodes (5): cleanup(), COLORTERM, PYTHONPATH, tui.sh script, TERM

### Community 149 - "Graphify Codebase Exploration & Dependency Hard Rules"
Cohesion: 0.40
Nodes (4): 1. Mandatory Graphify-First Codebase Search, 2. Dependency & Relationship Analysis, 3. Graph Synchronization, Graphify Codebase Exploration & Dependency Hard Rules

### Community 150 - "Ponytail"
Cohesion: 0.40
Nodes (4): Persistence, Ponytail, Rules, The ladder

### Community 151 - "P1: Important Follow-On Work"
Cohesion: 0.40
Nodes (5): 1. Runtime Presets for Small Models, 2. Richer Memory Inspection, 3. Better Verification Loops, 4. Better Activity Semantics, P1: Important Follow-On Work

### Community 152 - "Future Improvements"
Cohesion: 0.40
Nodes (5): Future Improvements, Phase 1: Quick Wins (Done ✓), Phase 2: Medium Effort, Phase 3: Advanced (Requires Resources), Phase 4: Claude-Level (Heavy Resources Only)

### Community 153 - "Improvement Recommendations by Resource Tier"
Cohesion: 0.40
Nodes (5): Generous (16-32GB RAM, 8k-16k context), Heavy (32GB+ RAM, 16k+ context), Improvement Recommendations by Resource Tier, Minimal (8GB RAM, 4k context), Standard (8-16GB RAM, 4k-8k context)

### Community 154 - "Torchlight Documentation"
Cohesion: 0.40
Nodes (5): Coverage, How To Use These Docs, Recent Runtime Progress, Recommended Reading Order For A New Contributor, Torchlight Documentation

### Community 155 - "run.sh"
Cohesion: 0.40
Nodes (4): COLORTERM, PYTHONPATH, run.sh script, TERM

### Community 156 - "test_repeated_edit_loop_fix.py"
Cohesion: 0.06
Nodes (37): End-to-end verification tests for preventing repeated edit loops, out-of-bounds, Verifies that calling WRITE_FILE with a tiny snippet on an established file, Verifies that calling EDIT_FILE with start_line beyond file length     does NOT, Verifies that 'L106' and start_line without end_line are safely parsed and bound, Verifies that a valid in-bounds single line edit (e.g. line 2) without old_text, Verifies TrajectoryLock catches sequential range stepping when line numbers use, Verifies that target file path aliases (target, file, filename, file_path)     a, Verifies that when a target file already exists on disk, the verification gate (+29 more)

### Community 157 - "setup_optimized.sh"
Cohesion: 0.60
Nodes (3): info(), ok(), setup_optimized.sh script

### Community 158 - "Ponytail"
Cohesion: 0.40
Nodes (4): Persistence, Ponytail, Rules, The ladder

### Community 159 - "Android Troubleshoot — Routing Layer"
Cohesion: 0.50
Nodes (3): Android Troubleshoot — Routing Layer, Step 1 — Call the tool, Step 2 — Read ONE reference file only if deeper guidance is needed

### Community 160 - "Target Quality Tiers"
Cohesion: 0.50
Nodes (4): Target Quality Tiers, Tier A: Constrained local mode, Tier B: Balanced local mode, Tier C: Strong local mode

### Community 161 - "Compression System"
Cohesion: 0.40
Nodes (5): Compression Flow, Compression System, LLM State Extractor, Summary Merge Logic, Trigger Conditions

### Community 162 - "AgentMemoryWidget"
Cohesion: 0.17
Nodes (5): AgentMemoryWidget, Displays the live L0 Agent Brain Scratchpad in UI/UX Pro format with scrollbars., Return the current project root path from engine or working directory., build_plan_overview_text(), Render Implementation Plan overview (title & mode badge).

### Community 163 - "Memory Tiers"
Cohesion: 0.50
Nodes (4): Disk Tiers (ProjectMemory), In-Memory Tiers (TieredMemory.messages), Memory Tiers, Session State Tiers

### Community 164 - "Persistence"
Cohesion: 0.50
Nodes (4): Loading Session State, Persistence, Project Memory Persistence, Session Persistence

### Community 165 - "opencode.json"
Cohesion: 0.50
Nodes (3): plugin, $schema, .opencode/plugins/graphify.js

### Community 166 - "Code Cleaner Skill"
Cohesion: 0.50
Nodes (3): Code Cleaner Skill, Purpose & Triggers, Workflow Instructions

### Community 185 - "sync_workspace_tasks"
Cohesion: 0.13
Nodes (29): test_is_task_match_precision(), test_mark_task_status_by_number(), test_phase_wise_tasks_and_hierarchical_marking(), test_plan_prompt_contract(), test_status_summary_counts_verified_and_completed(), test_add_subtask_survives_sync_and_lands_in_plan(), test_insert_task_into_plan_section(), test_update_task_graph_syncs_plan() (+21 more)

### Community 189 - "recovery.py"
Cohesion: 0.17
Nodes (11): inject_recovery_into_memory(), Any, Recovery engine for Torchlight errors.  Provides structured recovery strategies, Push recovery hint into memory state's tried_and_failed scratchpad list     to e, Tracks retry state for a specific error pattern., Generate a dedup key for this error type., Decide what to do after an error.          Returns a RecoveryAction indicating t, Check if we should escalate to the user after exhausting retries. (+3 more)

### Community 192 - "test_goal_mode_process.py"
Cohesion: 0.22
Nodes (9): anyio, Verify Goal mode detects 'goal' phase., Verify Goal mode rejects premature FINAL_ANSWER on turn 1 when implementation_pl, Verify solve_async in Goal Mode initializes phase to 'goal'., Verify bare JSON tool calls without <tool_call> tags are correctly parsed as too, test_detect_phase_goal_mode_detects_goal_phase(), test_parse_response_bare_json_tool_call(), test_solve_async_goal_mode_missing_plan_rejects_premature_final_answer() (+1 more)

### Community 195 - "ConnectionPill"
Cohesion: 0.18
Nodes (7): ConnectionPill, ComposeResult, Horizontal, Pressed, ConnectionPill — compact header widget showing live model/server status.  Replac, Compact connection status pill for the top HUD header.      Usage in compose()::, Update the pill's connected state and model name.

### Community 196 - "AskUserModal"
Cohesion: 0.12
Nodes (11): AskUserModal, Interactive modal dialog for structured user review options and custom input., BinaryFileViewer, ImageViewer, open_file_in_system_app(), on, Pressed, VerticalScroll (+3 more)

### Community 198 - "core/tests/test_models.py"
Cohesion: 0.16
Nodes (13): ContentChunk, ContextSnapshot, Snapshot of current memory state for display., WorkingSetSnapshot, test_content_chunk(), test_context_snapshot(), test_memory_needle(), test_memory_object() (+5 more)

### Community 199 - "prompts/__init__.py"
Cohesion: 0.43
Nodes (5): build_tool_syntax_prompt(), get_tool_syntax_for_context_size(), Tool syntax instructions for Torchlight.  Generates the appropriate tool calling, Build the complete tool syntax prompt for the system message.      Args:, Return the tool calling syntax instructions appropriate for the model's context

### Community 201 - "command_palette.py"
Cohesion: 0.16
Nodes (11): test_slash_command_list_has_wipe_and_compact(), test_match_prompt_suggestions_file_at(), test_match_prompt_suggestions_slash(), test_slash_command_list_shape(), _fuzzy_score(), match_prompt_suggestions(), Command palette + slash-command autocomplete for the Torchlight TUI.  Phase 4: *, Suggest completions for a single-token ``/cmd`` or ``@file`` prefix. (+3 more)

### Community 202 - "PromptTextArea"
Cohesion: 0.16
Nodes (7): ContextFileAttached, PromptTextArea, TextArea whose Enter submits instead of inserting a newline.      Hooks ``update, Posted when the user presses Enter with no active suggestion., Posted when the user accepts an @file suggestion., SubmitRequested, TextArea

### Community 203 - "Flashlight"
Cohesion: 0.26
Nodes (4): _beam_config_for_context(), Flashlight, FileEntry, SymbolIndex

### Community 204 - "iter_project_files"
Cohesion: 0.24
Nodes (9): Binding, test_build_palette_items_kinds_and_visibility(), test_iter_project_files_caps(), test_iter_project_files_skips_dot_and_vendor_dirs(), build_palette_items(), iter_project_files(), Path, Build ``(label, detail, kind, value)`` entries for the palette. (+1 more)

### Community 205 - "ConceptTracker"
Cohesion: 0.18
Nodes (6): ConceptTracker, Track explained concepts to avoid repetition., Extract and track concepts from an explanation., Check if a concept has been explained before., Get the context where a concept was first explained., Get concepts in content that haven't been explained yet.

### Community 207 - "check_memory"
Cohesion: 0.29
Nodes (9): format_memory_status(), get_memory_pressure(), is_memory_safe(), Memory pressure monitor for macOS Apple Silicon.  Provides real-time memory pres, Return a human-readable one-line memory status string., Get current macOS memory pressure level and stats.      Returns:         dict wi, Quick check: is it safe to run inference without swap thrashing?      Args:, check_memory() (+1 more)

### Community 208 - ".__init__"
Cohesion: 0.40
Nodes (4): _beam_budget(), Return (max_beam_files, max_lines_per_file) for the given context size., create_unified_registry(), Factory to create and bootstrap the unified registry.      Reuses create_default

### Community 209 - "ActionTracker"
Cohesion: 0.16
Nodes (8): _ActionContext, ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 211 - "test_plan_execution_loop.py"
Cohesion: 0.08
Nodes (42): test_parse_numbered_tasks_from_markdown(), anyio, test_auto_mark_does_not_complete_stub_or_missing_file(), test_auto_mark_does_not_overmark_unrelated_tasks(), test_auto_mark_matches_target_files_exact_basename(), test_auto_mark_multi_file_task_in_progress(), test_auto_mark_no_false_positive_substring(), test_auto_mark_pending_task_becomes_in_progress_without_verification() (+34 more)

### Community 218 - "start_mlx_server.sh"
Cohesion: 0.48
Nodes (5): is_valid_mlx_dir(), log_info(), log_success(), log_warn(), start_mlx_server.sh script

### Community 219 - "file_tree.py"
Cohesion: 0.20
Nodes (8): git_status_for_tree(), Git-aware file tree for the Torchlight TUI.  Phase 4: the explorer's ``Directory, Check if a directory name should be skipped from exploration., Re-run ``git status --porcelain`` for the current root., Undo git's C-style quoting for paths with special characters., Run ``git status --porcelain`` once for the given root.      Returns ``{}`` when, _should_skip_dir(), _unquote_c_style()

### Community 220 - "transcript.py"
Cohesion: 0.13
Nodes (16): _build_cached_syntax(), escape_markup(), extract_code_blocks(), Container, Rich transcript widgets for the Torchlight TUI.  Phase 1 of the UI-improvements, Truncate tool output for the UI: hard char + line caps., Current time as a compact HH:MM label (local time, display only)., Cache Pygments syntax objects to avoid re-parsing identical code blocks. (+8 more)

### Community 221 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 222 - "TrajectoryRail"
Cohesion: 0.09
Nodes (16): anyio, Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)., The streamed <tool_call> adds a dot; the completing step flips it., test_app_pending_step_updates_rail(), test_rail_add_pending_and_complete_ok(), test_rail_clear_removes_dots(), test_rail_complete_error_and_denied(), test_rail_complete_without_pending_is_noop() (+8 more)

### Community 223 - "RLMEngine"
Cohesion: 0.28
Nodes (4): test_rlm_engine_solve_method(), RLMEngine, SolveResult, Step

### Community 224 - "_clean_and_parse_json"
Cohesion: 0.50
Nodes (3): test_clean_and_parse_json_tolerant_multiline_content(), test_clean_and_parse_json_trailing_unterminated_string(), _clean_and_parse_json()

### Community 225 - "task_tree.py"
Cohesion: 0.32
Nodes (6): build_task_tree_markup(), _clean_task_text(), escape_markup(), TaskTreeWidget: High-performance, non-blocking task tree widget for Torchlight T, Safely escape text for Textual markup parsing., Build a Rich markup string representing the active task breakdown.

### Community 227 - ".on_tool_executed"
Cohesion: 0.29
Nodes (3): Called after a tool is executed. Returns test results if tests were run., Freshly verify any modified-but-unverified files and return True if         ever, Fetch speculative background test result if running, else execute tests synchron

### Community 228 - "test_autonomous_harness_pipeline.py"
Cohesion: 0.52
Nodes (6): create_mock_feedback_loop(), Path, Unit tests for Inter-Task Context Pipeline, Dependencies, and File Collision Gua, test_inter_task_output_summary_injection(), test_target_file_collision_detection(), test_task_dependencies_and_execution_ordering()

### Community 229 - "TaskManagerModal"
Cohesion: 0.24
Nodes (5): get_active_task_description(), Retrieve the title/description of the current active (in_progress) task, or firs, Modal dialog for interactive workspace task management & inspection., Open the interactive Task Manager modal screen., TaskManagerModal

### Community 231 - "set_ctx_window"
Cohesion: 0.40
Nodes (5): Unit tests for context budget overflow detection and fixes in TieredMemory, RLME, test_tiered_memory_total_tokens_includes_pinned_files(), test_tool_context_window_scaling(), Tell the tool layer what context window the current model has., set_ctx_window()

### Community 232 - "command"
Cohesion: 0.22
Nodes (9): command, chat(), compress_file(), goal(), plan(), Start an interactive chat session with context management and flashlight., Start a planning session to brainstorm and write/update implementation_plan.md., Start an autonomous goal execution session driven by .torchlight task tracking. (+1 more)

### Community 233 - "._estimate_l0_tokens"
Cohesion: 0.25
Nodes (3): Return a compact Rich markup string showing per-section token estimates., Fast O(1) estimate of dynamic L0 scratchpad tokens without disk I/O or recursion, Manually compact context memory and return (before, after, freed).

### Community 234 - "_extract_task_file_and_scope"
Cohesion: 0.33
Nodes (6): Verifies that _extract_task_file_and_scope correctly extracts filepaths, line ra, test_extract_task_file_and_scope(), _extract_referenced_files(), _extract_task_file_and_scope(), Extract distinct code/markup filepaths referenced in task description., Extract file path, line range, AST symbol anchor, and [NEW] flag from a task des

### Community 235 - "ToolValidationError"
Cohesion: 0.50
Nodes (3): Tool call failed schema validation., ToolValidationError, test_tool_validation_error()

### Community 236 - "thinking_block.py"
Cohesion: 0.50
Nodes (3): Per-step thinking blocks for the Torchlight TUI.  Phase 1 of the UI-improvements, Build a per-step thinking ``Collapsible``.      Falls back to a plain ``Static``, thinking_block()

### Community 237 - "test_cli_plan_mode_session"
Cohesion: 0.67
Nodes (3): asyncio, Verify StreamingChatSession in Plan Mode correctly handles plan creation and ver, test_cli_plan_mode_session()

### Community 239 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

## Knowledge Gaps
- **457 isolated node(s):** `Codebase Exploration & Token Optimization Hard Rules`, `Deterministic Trajectory & SLM Reliability Hard Rules (99%+ Accuracy for Small Models)`, `1. Mandatory Graphify-First Codebase Search`, `2. Dependency & Relationship Analysis`, `3. Graph Synchronization` (+452 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TorchlightApp` connect `TorchlightApp` to `TieredMemory`, `rlm_engine_optimized.py`, `on`, `PaneResizer`, `RLMEngineOptimized`, `test_tui_diff_view.py`, `AgentMemoryWidget`, `ApprovalModal`, `test_tui_accessibility.py`, `test_tui_image_viewer.py`, `test_model_normalization.py`, `Static`, `GitFileTree`, `test_tui_transcript_widgets.py`, `AskUserModal`, `ToolCallCard`, `CommandPalette`, `PromptTextArea`, `CloudClient`, `test_tui_plan_panel.py`, `tui_app.py`, `OllamaClient`, `test_tui_context_breakdown.py`, `TranscriptView`, `TrajectoryRail`, `test_tui_theme.py`, `test_resizer.py`, `TaskManagerModal`, `LlamaCppClient`, `test_tui_tool_cards.py`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `RLMEngineOptimized` connect `RLMEngineOptimized` to `TorchlightApp`, `TieredMemory`, `anyio`, `rlm_engine_optimized.py`, `on`, `PaneResizer`, `get_tool_registry`, `test_repeated_edit_loop_fix.py`, `ToolRegistry`, `test_tui_diff_view.py`, `Message`, `AgentMemoryWidget`, `ExecutionFeedbackLoop`, `InferenceParams`, `ApprovalModal`, `test_tool_parser.py`, `test_tui_image_viewer.py`, `ensure_project_initialized`, `TrajectoryLock`, `test_timeout_retry.py`, `Static`, `test_goal_mode_process.py`, `test_multimodal_vision.py`, `test_tui_transcript_widgets.py`, `AskUserModal`, `._stream_llm_with_retry`, `._is_vision_supported`, `._update_params`, `main_optimized.py`, `test_tui_plan_panel.py`, `tui_app.py`, `test_plan_execution_loop.py`, `test_engine_code_mode_setting`, `test_tui_context_breakdown.py`, `test_tui_tool_cards.py`, `TrajectoryRail`, `ProjectMemory`, `test_resizer.py`, `.get_locked_phase`, `TaskManagerModal`, `._estimate_l0_tokens`, `._execute_tool_with_approval`, `test_engine_parse_markdown_json_block_fallback`, `test_engine_parse_bracket_tool_calls`, `test_engine_parse_direct_xml_attribute_tool_calls`, `test_rlm_engine_plan_mode_normalization`, `test_detect_phase_plan_mode_resilience`, `test_detect_phase_plan_signals_in_unified_mode`, `test_chat_mode_verification_gate_bypassed`, `test_verification_gate_single_path_tool_template_and_anti_echo`, `LlamaCppClient`, `.set_execution_mode_callback`, `test_ring_buffer_prompt_dedup_skip`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `TieredMemory` connect `TieredMemory` to `TorchlightApp`, `rlm_engine_optimized.py`, `test_robust_task_tracking.py`, `MemoryObject`, `RLMEngineOptimized`, `DeduplicationEngine`, `config.py`, `TokenCounter`, `Message`, `tool_edit_file_impl`, `build_agent_memory_scratchpad_text`, `StreamingChatSession`, `test_multimodal_vision.py`, `core/tests/test_models.py`, `AutonomousHarness`, `.__init__`, `tui_app.py`, `test_plan_execution_loop.py`, `.load_project_memory`, `test_tui_context_breakdown.py`, `TaskSpec`, `RLMEngine`, `test_autonomous_harness_pipeline.py`, `set_ctx_window`, `._estimate_l0_tokens`, `.format_l0_scratchpad`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `TorchlightApp` (e.g. with `DummyClient` and `_StubClient`) actually correct?**
  _`TorchlightApp` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `TieredMemory` (e.g. with `StreamingChatSession` and `AutonomousHarness`) actually correct?**
  _`TieredMemory` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `RLMEngineOptimized` (e.g. with `DummyClient` and `ProjectMemory`) actually correct?**
  _`RLMEngineOptimized` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `MemoryConfig` (e.g. with `StreamingChatSession` and `DeduplicationEngine`) actually correct?**
  _`MemoryConfig` has 21 INFERRED edges - model-reasoned connections that need verification._