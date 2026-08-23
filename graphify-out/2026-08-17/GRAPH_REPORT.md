# Graph Report - tourchlight v1_i6  (2026-08-17)

## Corpus Check
- 275 files · ~223,469 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4333 nodes · 8983 edges · 243 communities (204 shown, 39 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 880 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `363fe600`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TorchlightApp
- HtmlGamePlayer
- TieredMemory
- RecoveryEngine
- MemoryObject
- task_helpers.py
- context_manager/compression/summarizer.py
- implementations.py
- TaskDAG
- test_multimodal_vision.py
- ContextDashboard
- test_code_quality_harness.py
- on
- BaseSkill
- WebOutcomeInspector
- RLMEngineOptimized
- TokenCounter
- DeduplicationEngine
- validate_tool_call
- GitFileTree
- ToolCallCard
- test_timeout_retry.py
- cli/main.py
- android_ref_build.md
- app.js
- ProjectSnapshot
- SymbolIndex
- test_implementations.py
- ToolRegistry
- test_tui_command_palette.py
- test_tui_diff_view.py
- config.py
- ._append_message
- UI Chat Improvements Plan - Minimal Context & Token Savings
- android_ref_runtime.md
- import_skill_file
- DebateVerifier
- ExecutionFeedbackLoop
- InferenceParams
- LLMClient
- Step
- CommandPalette
- SymbolIndex
- get_phase_system_prompt
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
- ProjectMemory
- test_optimization_fixes.py
- EngineConfigModal
- test_tui_status_bar.py
- LMStudioClient
- verify_m1_setup.py
- get_tool_registry
- StreamingChatSession
- StructurePreservingHTMLParser
- Static
- transcript.py
- Torchlight Architecture
- ProjectGraph
- detect_model_traits
- test_tui_transcript_widgets.py
- classify_command
- context_manager/memory/models.py
- llamacpp_client.py
- .solve_async
- Changelog
- VerbatimCompactor
- Torchlight Rust Port: Performance-Critical Paths
- Console
- TestRunResult
- VerbatimCompactor
- .__init__
- main_optimized.py
- test_tui_plan_panel.py
- ActionTracker
- PaneResizer
- android_ref_adb.md
- CloudClient
- test_inline_interception.py
- save_clipboard_image
- TranscriptView
- test_tui_tabbed_editor.py
- TDDSkill
- android_ref_signing.md
- AutonomousHarness
- Issues Found
- test_turboquant_qwen3b.py
- OllamaClient
- PyASTVisitor
- ProjectMemory
- test_phase_detection.py
- test_tui_theme.py
- test_resizer.py
- Torchlight Excellence Roadmap
- context_manager/memory/embeddings.py
- rlm_engine_optimized.py
- test_surgical_task_verification.py
- model_tester_gui.py
- ImageAttachmentCard
- interactive_model_tester.py
- Architecture
- Checklist
- ToolResult
- Prompt Templates for 7B Coder Models
- REPLSandbox
- tui_app.py
- Memory System Deep Dive
- discovery.py
- Plan: Non-Security Improvements
- MessageCard
- Execution Feedback Loop
- context_manager/memory/persistence.py
- context-manager-cli/tests/test_models.py
- TrajectoryLogger
- ValueError
- Plan: UI Improvements — Torchlight Codex IDE
- Torchlight — Terminal AI Coding Agent
- IndexVisitor
- TestApp
- Context Manager CLI
- 🎮 Essential Game Mechanics Checklist
- Resource-Adaptive Features
- TrajectoryRail
- .from_dict
- Data Flow
- Core Classes
- prompts_minimal.py
- sync_workspace_tasks
- web_server.py
- command
- Textual & Rich TUI Performance and Design Rules
- HTMLGameSkill
- context_manager/prompts.py
- AgentMemoryWidget
- core/api/lmstudio.py
- .action_tracker
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
- task_graph.py
- setup_optimized.sh
- Ponytail
- Android Troubleshoot — Routing Layer
- Target Quality Tiers
- Compression System
- test_tui_trajectory_rail.py
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
- _clean_and_parse_json
- tui_widgets/__init__.py
- ConversationSummarizer
- iter_project_files
- test_goal_mode_process.py
- test_ring_buffer_prompt_dedup_skip
- ._execute_tool_with_approval
- prompts/__init__.py
- ._build_messages
- set_ctx_window
- context_manager/compression/compactor.py
- Flashlight
- .update_file
- fuzzy_filter
- MyCustomSkill
- .pin_file
- ._repair_stop_tokens
- ActionEntry
- test_plan_execution_loop.py
- test_solve_async_plan_mode_allows_final_answer_with_pending_tasks
- context-manager-cli
- torchlight-core
- start_mlx_server.sh
- test_chat_mode_verification_gate_bypassed
- Schema Reference
- Retrieval System
- test_cli_plan_mode_session
- .remove_node
- ._update_params
- .print_action
- ._calculate_metadata_overhead
- run_gui.sh
- f2py
- hf
- huggingface-cli
- idna
- markdown-it
- mlx_lm
- numpy-config
- pip
- pip3
- pygmentize
- tiny-agents
- tqdm
- transformers

## God Nodes (most connected - your core abstractions)
1. `TorchlightApp` - 208 edges
2. `TieredMemory` - 167 edges
3. `RLMEngineOptimized` - 117 edges
4. `MemoryConfig` - 95 edges
5. `AutonomousHarness` - 69 edges
6. `ExecutionFeedbackLoop` - 54 edges
7. `LlamaCppClient` - 54 edges
8. `SkillUploadModal` - 49 edges
9. `CloudClient` - 46 edges
10. `Step` - 44 edges

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

## Communities (243 total, 39 thin omitted)

### Community 0 - "TorchlightApp"
Cohesion: 0.04
Nodes (38): asyncio, Tests for TorchlightApp project_root property and task manager modal integration, test_action_task_manager_pushes_screen(), test_torchlight_app_project_root_fallback(), test_torchlight_app_project_root_property(), is_port_in_use(), Check if server port 8080 is actively listening., copy_to_clipboard() (+30 more)

### Community 1 - "HtmlGamePlayer"
Cohesion: 0.10
Nodes (29): GameInputEvent, GameOutcomeResult, get_process_memory_mb(), HtmlGamePlayer, Path, HTML Game Inspector & Player Harness for Torchlight.  Provides autonomous playin, Autonomous HTML Game Harness & Dynamic Verifier.      Launches an ephemeral brow, Plays the HTML game for duration_ms while simulating inputs and checking frame d (+21 more)

### Community 2 - "TieredMemory"
Cohesion: 0.05
Nodes (59): ContextSnapshot, MemoryConfig, Enable or disable semantic deduplication., Persist user preferences to project memory., Calculate remaining token budget headroom before reaching max_tokens threshold., Predict likely next tools based on current state., Tiered memory system with L0-L3 hierarchy:     - L0: Active prompt (current cont, Return list of (path, content) for pinned files. (+51 more)

### Community 3 - "RecoveryEngine"
Cohesion: 0.06
Nodes (57): get_recovery_hint(), inject_recovery_into_memory(), Any, Recovery engine for Torchlight errors.  Provides structured recovery strategies, Push recovery hint into memory state's tried_and_failed scratchpad list     to e, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type. (+49 more)

### Community 4 - "MemoryObject"
Cohesion: 0.10
Nodes (32): build_embedder(), compute_tf_idf_score(), cosine_similarity(), Embedder, HybridEmbedder, HybridMemoryRetriever, _is_low_memory(), KeywordEmbedder (+24 more)

### Community 5 - "task_helpers.py"
Cohesion: 0.12
Nodes (27): test_task_matrix_compress_over_45_percent_context(), Tests for robust task and status tracking in LLM context and TUI., test_compact_task_matrix_adaptive_rendering(), test_status_badges_and_boxes(), test_validate_task_transition(), _clean_task_text(), _file_looks_complete(), get_compact_task_matrix() (+19 more)

### Community 6 - "context_manager/compression/summarizer.py"
Cohesion: 0.19
Nodes (14): DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer, Message (+6 more)

### Community 7 - "implementations.py"
Cohesion: 0.07
Nodes (52): Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Th, test_list_dir_impl(), _ddg_search(), _detect_doc_source(), _extract_identifiers(), _extract_symbols(), _git_run(), play_and_verify_game() (+44 more)

### Community 8 - "TaskDAG"
Cohesion: 0.23
Nodes (13): Directed Acyclic Graph (DAG) for Task Lifecycle Management., Restore DAG state to a previous snapshot., TaskDAG, TaskNode, Unit tests for Task Lifecycle and Directed Acyclic Graph (DAG) Engine., test_checkpoint_and_rollback(), test_cycle_detection_raises_error(), test_dag_topological_sort_and_ready_tasks() (+5 more)

### Community 9 - "test_multimodal_vision.py"
Cohesion: 0.07
Nodes (55): Any, Convert Message to provider-compatible API payload dictionary., fixture, Path, Unit and integration tests for multimodal vision capabilities (Gemma 3, Qwen VL,, Verify Message.to_dict generates rich text description when vision_supported is, Verify format_image_text_summary extracts metadata and embeds exact calling cont, Create a minimal 1x1 valid PNG image. (+47 more)

### Community 10 - "ContextDashboard"
Cohesion: 0.11
Nodes (6): ContextDashboard, Panel, Print sub-agent task progress to the console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 11 - "test_code_quality_harness.py"
Cohesion: 0.09
Nodes (37): Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_compile_gate_rejects_return_outside_function(), test_detect_symptom_patching(), test_edit_file_blocks_broken_syntax() (+29 more)

### Community 12 - "on"
Cohesion: 0.04
Nodes (14): DirectorySelected, FileSelected, NodeSelected, FolderPickerModal, on, Pressed, Selected, Submitted (+6 more)

### Community 13 - "BaseSkill"
Cohesion: 0.08
Nodes (28): ABC, BaseSkill, CalculatorSkill, create_default_registry(), GitSkill, _LazySkill, Skills — external / plugin capabilities.  Skills are DIFFERENT from core tools:, Evaluate a mathematical expression safely using Python's AST. (+20 more)

### Community 14 - "WebOutcomeInspector"
Cohesion: 0.09
Nodes (22): EphemeralHTTPServer, Any, HTMLParser, Path, QuietHTTPRequestHandler, Web Outcome Inspector for Torchlight.  Provides low-memory, ephemeral runtime an, Spins up a lightweight local HTTP server for static file inspection., Tier 1: Static HTML syntax and asset path validator. (+14 more)

### Community 15 - "RLMEngineOptimized"
Cohesion: 0.07
Nodes (35): anyio, test_verification_gate_allows_final_answer_when_all_done(), test_verification_gate_rejects_premature_final_answer(), test_verification_gate_rejects_resume_work_without_tools(), test_verification_gate_rejects_zero_tool_in_goal_mode(), Verify RLMEngineOptimized normalizes PLAN mode string and Enum., Verify _detect_phase returns 'plan' when execution_mode is 'plan' regardless of, Verify phase auto-detection detects 'plan' from brainstorming and planning signa (+27 more)

### Community 16 - "TokenCounter"
Cohesion: 0.07
Nodes (32): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing. (+24 more)

### Community 17 - "DeduplicationEngine"
Cohesion: 0.05
Nodes (36): ConceptTracker, ContentFingerprint, ContentFingerprinter, deduplicate_context(), DeduplicationEngine, DeduplicationStats, Semantic Deduplication Engine for Torchlight.  Provides content-aware deduplicat, Fingerprint explanatory content to track concepts explained. (+28 more)

### Community 18 - "validate_tool_call"
Cohesion: 0.09
Nodes (28): Verify validate_tool_call auto-heals missing/misplaced path arguments for VIEW_I, test_validate_tool_call_view_image_auto_healing(), test_schema_target_alias_no_collision(), test_get_openai_tools_schema(), test_get_schemas_for_phase(), test_validate_tool_call_alias(), test_validate_tool_call_coercion(), test_validate_tool_call_list_dir_optional_path() (+20 more)

### Community 19 - "GitFileTree"
Cohesion: 0.07
Nodes (34): _FakeProc, anyio, Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)., test_git_tree_decorates_file_labels(), test_git_tree_right_click_posts_message(), test_normalize_status_code(), test_parse_git_status_porcelain_basic(), test_parse_git_status_porcelain_quoted_path() (+26 more)

### Community 20 - "ToolCallCard"
Cohesion: 0.06
Nodes (38): anyio, Tests for Phase-2 tool call cards (risk badge, status, timing, sections)., The streamed <tool_call> mounts a pending card completed by the step., Verify tool calls with <= 10 lines of output default to expanded., Verify tool calls with > 10 lines of output default to collapsed., Verify ToolCallCard.action_copy extracts result/payload and triggers copy., test_app_pending_card_wiring(), test_risk_for_tool() (+30 more)

### Community 21 - "test_timeout_retry.py"
Cohesion: 0.16
Nodes (15): Exception, TimeoutError, _bare_engine(), _FailingStreamEngine, Exception, Unit tests for transient LLM timeout/connection retry behavior in the solve loop, Construct an engine without the heavy __init__ (client/sandbox setup)., Engine whose _stream_llm fails transiently N times then succeeds. (+7 more)

### Community 22 - "cli/main.py"
Cohesion: 0.06
Nodes (36): Re-export TieredMemory and MemoryConfig from shared core library core.memory.man, _is_valid_decision(), Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, Load deduplication cache from project memory., Load user preferences from project memory., Filter out empty, generic, or noisy session summary strings., Load persistent project memory (.context-memory.json) into L0 working state., Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length. (+28 more)

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
Nodes (41): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_read_symbols_indented_methods_and_duplicate_names(), test_run_command_intercept_ast_functions(), test_search_ast_action_aliases(), test_search_ast_after_writing_file(), test_search_ast_impl_fallback(), test_search_ast_schema_validation(), test_verify_compile_param() (+33 more)

### Community 28 - "ToolRegistry"
Cohesion: 0.13
Nodes (16): test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command(), Generate tool descriptions for injection into the system prompt.          Scales, Definition of a registered tool. (+8 more)

### Community 29 - "test_tui_command_palette.py"
Cohesion: 0.19
Nodes (15): anyio, Tests for Phase-4 command palette + prompt autocomplete., test_add_context_chip_image_prefix(), test_command_palette_composes_filters_and_selects(), test_command_palette_enter_runs_highlighted_item(), test_match_prompt_suggestions_file_at(), test_match_prompt_suggestions_slash(), test_prompt_text_area_enter_submits_and_accepts_suggestion() (+7 more)

### Community 30 - "test_tui_diff_view.py"
Cohesion: 0.09
Nodes (34): anyio, Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)., A pre-write snapshot (from approval) wins over the already-written disk state., The engine's own CODE_FILE_WRITE approval path is diffable too., The approval modal shows a DIFF PREVIEW section when entries exist., A successful WRITE_FILE step mounts a DiffView card with real content., test_app_write_step_renders_diff_card(), test_approval_modal_omits_diff_when_empty() (+26 more)

### Community 31 - "config.py"
Cohesion: 0.10
Nodes (22): ConversationSummarizer, Summarizer with LLM-powered and rule-based fallback paths.      When an llm_clie, Message, ContextProfile, _detect_apple_silicon_ram(), _detect_chip(), estimate_metadata_overhead(), get_context_profile() (+14 more)

### Community 32 - "._append_message"
Cohesion: 0.06
Nodes (28): extract_modified_symbols(), is_valid_file_path(), Message, MessageRole, Path, Run semantic deduplication on current message history.                  Args:, Persist deduplication cache to project memory., Trim SessionState lists to configured maximum to prevent unbounded growth. (+20 more)

### Community 33 - "UI Chat Improvements Plan - Minimal Context & Token Savings"
Cohesion: 0.05
Nodes (36): 1.1 Rich Message Card Component, 1.2 Streaming Experience Improvements, 1.3 Transcript Container Enhancements, 1. Message Rendering & Formatting (Claude Code-like Experience), 2.1 Content Fingerprinting System, 2.2 Deduplication-Aware Compression, 2.3 Tool Result Deduplication, 2. Semantic Deduplication for Token Savings (+28 more)

### Community 34 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 35 - "import_skill_file"
Cohesion: 0.08
Nodes (29): ModalTestApp, App, asyncio, ComposeResult, Pressed, Tests for skill upload/import and TUI skills overview formatting in context-mana, test_import_markdown_skill_file(), test_import_python_skill_file() (+21 more)

### Community 36 - "DebateVerifier"
Cohesion: 0.09
Nodes (23): Adversarial critique / debate. Focused flaw identification., Synthesis and refinement following critique. Deterministic., Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., CritiqueResult, DebateVerifier, DebateVerifier implementation: orchestrates adversarial critique and refinement, Synthesize refined output incorporating valid critiques using InferenceParams.fo (+15 more)

### Community 37 - "ExecutionFeedbackLoop"
Cohesion: 0.06
Nodes (42): Re-export ExecutionFeedbackLoop and TestRunResult from shared core library core., Execution feedback loop for Torchlight., ExecutionFeedbackLoop, extract_surgical_traceback(), Enum, Path, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Auto-run tests and web outcome inspection after code changes and inject feedback (+34 more)

### Community 38 - "InferenceParams"
Cohesion: 0.08
Nodes (21): InferenceParams, One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters., Reasoning through plans. Moderate creativity. All tools remain available., Diagnosing errors. Slightly more exploration., General conversation., Send messages and return the full response. (+13 more)

### Community 39 - "LLMClient"
Cohesion: 0.09
Nodes (20): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client() (+12 more)

### Community 40 - "Step"
Cohesion: 0.03
Nodes (57): test_dirty_marker_not_set_for_non_tab_file(), test_dirty_marker_set_on_write_step(), NamedTuple, Step, AgentStatusModal, ApprovalModal, CopySelectionModal, EditorTab (+49 more)

### Community 41 - "CommandPalette"
Cohesion: 0.10
Nodes (10): Highlighted, AttachContextModal, CommandPalette, Changed, on, Selected, Submitted, Command palette + slash-command autocomplete for the Torchlight TUI.  Phase 4: * (+2 more)

### Community 42 - "SymbolIndex"
Cohesion: 0.15
Nodes (9): BeamResult, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build() (+1 more)

### Community 43 - "get_phase_system_prompt"
Cohesion: 0.08
Nodes (22): DirectiveTracker, Any, Directive tracker and constraint violation reinforcement module for Torchlight., Record a directive violation (e.g. 'cd_command', 'test_assertion_delete'), Reset violation counts., Tracks model constraint violations during execution turns and dynamically     in, get_phase_system_prompt(), Unified system prompts for Torchlight.  Single source of truth for all frontends (+14 more)

### Community 44 - "test_grammar_parse.py"
Cohesion: 0.11
Nodes (29): _code_lines(), _grammar_text(), _grammar_tool_names(), _parse_rules(), Regression guard for the TurboQuant GBNF grammar-parser incompatibility.  The Tu, Return ``body`` up to (but not including) a top-level '#' comment,     ignoring, Map rule name -> raw (comment-stripped) rule body., TurboQuant parser rejects rule continuations that START with '|'. (+21 more)

### Community 45 - "tool_edit_file_impl"
Cohesion: 0.06
Nodes (51): calculate_in_memory_diff(), Calculate exact lines added and deleted between two string buffers in RAM., test_detect_stubs(), test_tool_write_file_integration(), test_write_file_blocks_broken_syntax_and_truncation(), Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_allows_shorter_content_with_force(), test_edit_file_auto_fallback_to_write() (+43 more)

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
Cohesion: 0.13
Nodes (27): Unit tests for core/tools/parser.py tolerant tool parser & fuzzy repair engine., test_extract_balanced_json_object(), test_parse_tool_call_payload(), test_repair_unclosed_action_tags(), test_repair_unclosed_tool_call_tag(), test_single_quoted_dict_parsing(), test_strip_interleaved_prose(), test_strip_thinking_tags() (+19 more)

### Community 50 - "test_tui_image_viewer.py"
Cohesion: 0.14
Nodes (19): anyio, fixture, Tests for TUI ImageViewer, BinaryFileViewer, and ImageAttachmentCard.  Verifies:, Create a temporary PNG image file for testing., Test save_clipboard_image when clipboard is empty / contains no image., Test PromptTextArea pasting image path or clipboard image emits ContextFileAttac, Create a temporary SVG file for testing., Create a temporary non-image binary file containing null bytes. (+11 more)

### Community 51 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 52 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 53 - "ContextBudget"
Cohesion: 0.07
Nodes (16): _clamp(), ContextBudget, Adaptive, headroom-driven context budget coordinator for Torchlight.  Static res, Token reserve kept for the recent-message window., Current fraction of the target window in use., Effective budget allocations for the current turn.      `used_tokens` is the liv, Token allowance for the L0 working memory scratchpad this turn., Max characters per scratchpad entry (longer when headroom is ample). (+8 more)

### Community 54 - "ProjectMemory"
Cohesion: 0.06
Nodes (40): ensure_git_repository(), ensure_project_initialized(), init_new_project(), ProjectMemory, MemoryObject, Path, SessionState, Ensure target project directory exists and has a local Git repository initialize (+32 more)

### Community 55 - "test_optimization_fixes.py"
Cohesion: 0.12
Nodes (21): Unit tests for core/tools/dedup.py argument normalization & TrajectoryLock., test_compute_payload_hash(), test_edit_file_alternate_trajectory_hint(), test_normalize_tool_args(), test_trajectory_lock(), test_trajectory_lock_error_feedback(), test_trajectory_lock_window_and_read_only_rate_limiting(), compute_payload_hash() (+13 more)

### Community 56 - "EngineConfigModal"
Cohesion: 0.10
Nodes (11): EngineConfigModal, Modal dialog for selecting Inference Engine and TurboQuant KV Cache mode., Get model choices tailored to the selected inference backend., Open the Inference Engine & TurboQuant configuration modal., ConnectionPill, ComposeResult, Horizontal, Pressed (+3 more)

### Community 57 - "test_tui_status_bar.py"
Cohesion: 0.15
Nodes (18): anyio, Tests for Phase-4 consolidated status bar (gauge + segments widget)., test_build_status_segments_defaults(), test_build_status_segments_populated(), test_build_status_segments_running_no_tps_yet(), test_build_status_segments_server_offline_and_branch_escape(), test_gauge_markup_clamps_out_of_range(), test_gauge_markup_color_escalation() (+10 more)

### Community 58 - "LMStudioClient"
Cohesion: 0.14
Nodes (8): _friendly_timeout_msg(), LMStudioClient, Synchronous streaming generator — yields tokens one-by-one.          Uses DEFAUL, Async streaming generator. Uses per-chunk read timeout (DEFAULT_TIMEOUT)., Simple synchronous query interface (LLMClient protocol compatibility)., Return a human-readable message explaining which part of the request timed out., Timeout, TimeoutException

### Community 59 - "verify_m1_setup.py"
Cohesion: 0.18
Nodes (24): format_memory_status(), get_memory_pressure(), is_memory_safe(), Memory pressure monitor for macOS Apple Silicon.  Provides real-time memory pres, Return a human-readable one-line memory status string., Get current macOS memory pressure level and stats.      Returns:         dict wi, Quick check: is it safe to run inference without swap thrashing?      Args:, check_hardware() (+16 more)

### Community 60 - "get_tool_registry"
Cohesion: 0.17
Nodes (12): test_identical_old_new_text_preflight(), test_whitespace_stripped_preflight(), Tests for performance and accuracy optimizations in Torchlight., test_batch_tool_execution(), test_inline_syntax_guardrail(), test_symbol_index_mtime_cache(), test_get_tool_registry(), test_tool_registry_preview_dry_run() (+4 more)

### Community 61 - "StreamingChatSession"
Cohesion: 0.18
Nodes (8): Panel, /params                    — show current params         /params auto, Re-append closing tags and unclosed JSON braces that were consumed as stop token, Auto-switch _params based on detected phase.  No-op when locked., Run out-of-band DebateVerifier pass if candidate proposal needs verification., Step function for AutonomousHarness - executes a single task iteration., Async implementation of harness step function., StreamingChatSession

### Community 62 - "StructurePreservingHTMLParser"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 63 - "Static"
Cohesion: 0.11
Nodes (16): DirectoryTree, format_model_display_name(), list_available_draft_models(), any, Format a model ID or filename into a concise, human-readable display name., Scan local models directory for potential speculative draft models.      Returns, ComposeResult, VerticalScroll (+8 more)

### Community 64 - "transcript.py"
Cohesion: 0.13
Nodes (17): _build_cached_syntax(), escape_markup(), extract_code_blocks(), Container, Rich transcript widgets for the Torchlight TUI.  Phase 1 of the UI-improvements, Truncate tool output for the UI: hard char + line caps., Current time as a compact HH:MM label (local time, display only)., Cache Pygments syntax objects to avoid re-parsing identical code blocks. (+9 more)

### Community 65 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 66 - "ProjectGraph"
Cohesion: 0.18
Nodes (20): get_project_graph(), ProjectGraph, Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Get or create the ProjectGraph instance for a given root directory., Incrementally update the AST graph for a single modified file., update_project_graph_file(), Unit tests for incremental O(1) AST graph delta updates. (+12 more)

### Community 67 - "detect_model_traits"
Cohesion: 0.20
Nodes (7): detect_model_traits(), Detect architecture traits (size, reasoning status, vision capability) from mode, Dynamically return an InferenceParams preset calibrated for both         the tar, test_detect_model_traits(), test_for_model_and_phase(), test_detect_model_traits_vision(), Manually lock or unlock the agent phase ('code', 'plan', 'goal', 'troubleshoot',

### Community 68 - "test_tui_transcript_widgets.py"
Cohesion: 0.14
Nodes (19): anyio, Tests for Phase-1 transcript widgets (message cards, streaming, thinking)., Smoke test: the real app mounts MessageCards and drives the streaming view., Verify MessageCard copy and reuse actions work for user and assistant messages., Verify MessageCard duration formatting, empty user headers, and timestamp overri, test_app_transcript_wiring(), test_card_meta_for(), test_estimate_token_count() (+11 more)

### Community 69 - "classify_command"
Cohesion: 0.10
Nodes (26): CoreToolRegistry, get_core_registry(), Any, Compatibility subclass of ToolRegistry providing CLI-specific execute/dangerous_, test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command() (+18 more)

### Community 70 - "context_manager/memory/models.py"
Cohesion: 0.13
Nodes (14): _build_excerpt(), LLMStateExtractor, _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa (+6 more)

### Community 71 - "llamacpp_client.py"
Cohesion: 0.17
Nodes (13): Verify _strip_multimodal_images flattens image_url blocks into text., test_llamacpp_client_multimodal_image_stripping(), HTTPError, _context_limit_message(), _is_model_loading_error(), Detect if HTTPError represents llama-server currently loading model weights., Poll llama-server health/models endpoint until the model finishes loading., Convert multimodal image_url content blocks to pure text descriptions for text-o (+5 more)

### Community 72 - ".solve_async"
Cohesion: 0.18
Nodes (7): Return True if the most recent test run actually ran and has failing or, Build an explicit warning attached to an accepted final answer when the, Notify listeners of real-time background status and action telemetry., Notify listeners (dashboard/TUI) that task state changed after a tool call., Stream LLM response token-by-token cleanly without thread deadlocks., True when an LLM error string looks like a transient server stall that         a, Stream an LLM response, retrying up to ``retries`` times on transient         se

### Community 73 - "Changelog"
Cohesion: 0.06
Nodes (34): Added, Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+26 more)

### Community 74 - "VerbatimCompactor"
Cohesion: 0.22
Nodes (5): Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 75 - "Torchlight Rust Port: Performance-Critical Paths"
Cohesion: 0.10
Nodes (20): 1. `token_counter` → `torchlight_core::token_counter` (Week 1), 2. `flashlight/indexer.py` → `torchlight_core::ast_indexer` (Week 2), 3. `graph_engine.py` → `torchlight_core::graph_engine` (Week 3), 4. `memory/manager.py` → `torchlight_core::memory::tiered` (Week 4), 5. `memory/selective_compression.py` → `torchlight_core::memory::selective` (Week 5), 6. `memory/budget.py` → `torchlight_core::memory::budget` (Week 5), 7. `compression/summarizer.py` → `torchlight_core::compression::summarizer` (Week 6), 8. `tools/parser.py` → `torchlight_core::tools::parser` (Week 6) (+12 more)

### Community 76 - "Console"
Cohesion: 0.24
Nodes (7): Console, test_render_task_progress_empty(), test_render_task_progress_with_tasks(), test_action_entry_markup_safety(), test_action_tracker_print_action_safety(), test_escape_raw_brackets_and_json(), test_tui_markup_escaping_safety()

### Community 77 - "TestRunResult"
Cohesion: 0.26
Nodes (8): Return True only if a run succeeded. Uses exit code as the authoritative, TestRunResult, create_mock_feedback_loop(), Path, Unit tests for Inter-Task Context Pipeline, Dependencies, and File Collision Gua, test_inter_task_output_summary_injection(), test_target_file_collision_detection(), test_task_dependencies_and_execution_ordering()

### Community 78 - "VerbatimCompactor"
Cohesion: 0.21
Nodes (6): Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 80 - "main_optimized.py"
Cohesion: 0.29
Nodes (11): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Step (+3 more)

### Community 81 - "test_tui_plan_panel.py"
Cohesion: 0.16
Nodes (18): _build_plan_text(), _make_app(), anyio, Delegate to the real TUI plan-builder helper., Verify build_plan_text handles bulleted plan lists without explicit checkboxes., Repeated checklist entries (summary + detailed sections) must not duplicate., test_build_plan_text_all_done(), test_build_plan_text_dedupes_duplicate_checkbox_lines() (+10 more)

### Community 82 - "ActionTracker"
Cohesion: 0.19
Nodes (7): _ActionContext, ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 83 - "PaneResizer"
Cohesion: 0.13
Nodes (6): MouseMove, MouseUp, PaneResizer, Click, MouseDown, Interactive splitter bar to resize the left/right side panes.      Drag the bar

### Community 84 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 85 - "CloudClient"
Cohesion: 0.21
Nodes (6): CloudClient, Sanitize message roles. Convert system role to user role for models (e.g. Gemma, Async streaming implementation required by LLMClient protocol., Return the ids of models the provider currently reports as available.         Us, Resolve requested self.model against live models to prevent 404 mismatches., _sanitize_messages_for_cloud()

### Community 86 - "test_inline_interception.py"
Cohesion: 0.20
Nodes (13): _looks_like_full_file(), _looks_like_prose_or_outline(), Helper to check if content looks like a complete standalone file rather than a s, Heuristic gate for inline code interception (step 6b of _parse_response).      R, MockEngine, Unit tests for inline code interception safety checks, tight regex matching, and, test_detect_phase_prioritizes_write_and_file_extensions(), test_existing_file_partial_snippet_protection() (+5 more)

### Community 87 - "save_clipboard_image"
Cohesion: 0.11
Nodes (12): Test save_clipboard_image when PIL ImageGrab returns a PIL Image., Test save_clipboard_image when PIL ImageGrab returns list of copied file paths., test_save_clipboard_image_file_list(), test_save_clipboard_image_pil_object(), Check system clipboard for image data or copied image file paths.     If found,, save_clipboard_image(), Paste, ContextFileAttached (+4 more)

### Community 88 - "TranscriptView"
Cohesion: 0.12
Nodes (10): VerticalScroll, Bounded scroll container hosting the transcript.      Encapsulates the 120-child, Mount a card, prune the oldest when over the cap, and scroll., Scroll the transcript to the bottom without animation., Navigate up (vim-style)., Navigate down (vim-style)., Focus a specific card by index., Copy last message content to clipboard. (+2 more)

### Community 89 - "test_tui_tabbed_editor.py"
Cohesion: 0.14
Nodes (17): anyio, Tests for Phase-5 tabbed editor split pane (open_file_tab, dirty marker, keyboar, test_close_file_tab_removes_from_open_tabs(), test_close_file_tab_switches_active_tab(), test_editor_pane_resizer_and_scrollbars(), test_editor_split_pane_composes(), test_editor_view_renders_syntax_with_line_numbers(), test_get_tab_hash() (+9 more)

### Community 90 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 91 - "android_ref_signing.md"
Cohesion: 0.12
Nodes (16): ~200 tokens. Do NOT load other reference files in the same turn., Android Signing Reference — Keystore, Certificates, Google Play, app/build.gradle:, Common errors, Enroll: Play Console -> App -> Setup -> App signing, Generate a new debug keystore (if lost), Google manages the release key; you upload with a separate upload key, Google Play App Signing (recommended) (+8 more)

### Community 92 - "AutonomousHarness"
Cohesion: 0.09
Nodes (33): AutonomousHarness, GoalSpec, HarnessConfig, Enum, Path, str, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, Ensure target project has local git repository and persistent memory initialized (+25 more)

### Community 93 - "Issues Found"
Cohesion: 0.12
Nodes (16): 1. **ExecutionMode Enum Mismatch**, 2. **Phase Detection Not Integrated with Goal Mode**, 3. **Goal Spec Initialization Race Condition**, 4. **Missing Verification Gate in CLI Goal Mode**, 5. **AutonomousHarness Not Wired to LLM Engine in CLI**, 6. **Inconsistent ExecutionMode Default**, 7. **Memory State Sync Issues**, Fix Plan (+8 more)

### Community 94 - "test_turboquant_qwen3b.py"
Cohesion: 0.17
Nodes (13): BenchmarkResult, get_process_rss_mb(), LlamaCppTurboRunner, main(), MlxTurboRunner, Run micro-benchmark via llama-bench (measures raw Metal kernel throughput)., Run real code generation using llama-cli and test Python AST syntax., Run token generation with MLX Quantized KV Cache. (+5 more)

### Community 95 - "OllamaClient"
Cohesion: 0.22
Nodes (4): _normalize_messages_for_ollama(), OllamaClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.

### Community 96 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 97 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 98 - "test_phase_detection.py"
Cohesion: 0.13
Nodes (22): _make_session(), asyncio, Troubleshoot wins over code when both signals are present in unified mode., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., Verify that in Goal Mode with no implementation_plan.md, _generate_response reje, Verify that when session is explicitly in Chat Mode, _detect_phase returns 'chat, Create a StreamingChatSession with mocked heavy dependencies. (+14 more)

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

### Community 103 - "rlm_engine_optimized.py"
Cohesion: 0.07
Nodes (47): Conversation Summarizer for Torchlight.  Extracts key information from conversat, ContentChunk, ContentType, ContextSnapshot, ExecutionMode, MemoryEventType, Message, MessageRole (+39 more)

### Community 104 - "test_surgical_task_verification.py"
Cohesion: 0.20
Nodes (13): Unit tests for Surgical Targeted Task Verification in Torchlight., test_verify_task_preflight_invalid_json(), test_verify_task_preflight_syntax_error(), test_verify_task_preflight_valid_python(), test_verify_task_targeted_command(), _extract_referenced_files(), _find_file_in_project(), Extract distinct code/markup filenames referenced in task description. (+5 more)

### Community 105 - "model_tester_gui.py"
Cohesion: 0.17
Nodes (13): execute_llama_run(), execute_mlx_run(), Any, Validate python code block syntax., Execute llama-completion generation with custom TurboQuant / KV mode., Execute MLX generation in venv_mlx environment., Scan local models directory and HuggingFace/LMStudio caches for models., Start local Studio GUI server. (+5 more)

### Community 106 - "ImageAttachmentCard"
Cohesion: 0.14
Nodes (8): open_file_in_system_app(), on, Pressed, Open a file with the operating system default application., ImageAttachmentCard, Click, on, Visual card displaying image metadata and a 24-bit ANSI terminal color preview.

### Community 107 - "interactive_model_tester.py"
Cohesion: 0.23
Nodes (15): BenchmarkRecord, interactive_menu(), main(), Path, Validate python code block syntax., Run llama-bench throughput evaluation., Run MLX generation in venv_mlx environment., Render comparison results table. (+7 more)

### Community 108 - "Architecture"
Cohesion: 0.15
Nodes (12): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Hard Rules, Commands, Context Budget Breakdown, Development (+4 more)

### Community 109 - "Checklist"
Cohesion: 0.15
Nodes (13): 1. Slash Command Verification, 2. Runtime Hardening, 3. Process Hygiene, 4. Provider and Model Verification, 5. Local-Model Efficiency, 6. Context-Rot and Memory Durability, 7. Retry And Cancel Semantics, Already Completed (+5 more)

### Community 110 - "ToolResult"
Cohesion: 0.15
Nodes (10): test_tool_result_failure(), test_tool_result_success(), Execute a tool by name with given arguments.          Validates args, executes,, Generate a dry-run preview string for a tool call without executing mutations., Structured result from tool execution., Execute multiple tool calls in parallel when safe (AUTO risk level).         Fal, Get a tool definition by name., Validate a tool call against its schema.          Returns (is_valid, error_msg, (+2 more)

### Community 111 - "Prompt Templates for 7B Coder Models"
Cohesion: 0.13
Nodes (14): Breaking Complex Tasks into Chained Prompts, General Rules for 7B Models, Key Characteristics of 7B Models, Prompt Pattern: Chained Development, Prompt Templates for 7B Coder Models, Structure, Structure, Structure (+6 more)

### Community 112 - "REPLSandbox"
Cohesion: 0.10
Nodes (27): test_rlm_engine_solve_method(), create_client(), display_step(), get_depth_style(), main(), print_banner(), print_help(), Step (+19 more)

### Community 113 - "tui_app.py"
Cohesion: 0.09
Nodes (25): test_list_available_models_includes_gemma4e4b(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), test_normalize_mlx_gemma_4_4e4b(), fetch_provider_models(), list_available_models(), normalize_model_name(), Normalize model alias names (e.g. 'gemma-2-2b', 'qwen', 'gemma 4 E2B', 'gemma 4 (+17 more)

### Community 114 - "Memory System Deep Dive"
Cohesion: 0.15
Nodes (12): Allocation for 4k Context, Architecture Overview, Auto-tuned Budgets by Context Size, Auto-tuning, CLI Integration, Configuration Commands, Configuration Commands, File Locations (+4 more)

### Community 115 - "discovery.py"
Cohesion: 0.12
Nodes (26): _extract_markdown_skill_metadata(), get_skill_directories(), parse_frontmatter(), Splits a markdown file into (metadata_dict, body_markdown).     Gracefully falls, Return candidate directories containing skills in priority order:     1. <worksp, Extract (skill_name, description, icon, risk_level, category, tags) from a markd, discover_skills(), execute_skill_by_name() (+18 more)

### Community 116 - "Plan: Non-Security Improvements"
Cohesion: 0.17
Nodes (11): Decisions, Out of Scope, Plan: Non-Security Improvements, Task 1: Frontend Consolidation, Task 2: Split `implementations.py` into Sub-Modules, Task 3: Cache `SymbolIndex` Across Micro-Epochs, Task 4: Extract Tool Execution Pipeline, Task 5: Fix Error Handling Gaps (+3 more)

### Community 117 - "MessageCard"
Cohesion: 0.18
Nodes (4): MessageCard, ComposeResult, A chat turn rendered as a rich Markdown card with header chrome.      Styled wit, Return elapsed duration (e.g. '2.4s'), explicit timestamp override, or empty str

### Community 118 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

### Community 119 - "context_manager/memory/persistence.py"
Cohesion: 0.16
Nodes (12): MemoryNeedle, MemoryObject, ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, SessionState, SessionPersistence (+4 more)

### Community 120 - "context-manager-cli/tests/test_models.py"
Cohesion: 0.18
Nodes (12): ContentChunk, ContextSnapshot, SessionState, WorkingSetSnapshot, test_content_chunk_custom(), test_content_chunk_defaults(), test_context_snapshot_fields(), test_message_custom_fields() (+4 more)

### Community 121 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 122 - "ValueError"
Cohesion: 0.13
Nodes (9): Add a task node to the DAG after verifying cycle safety., Detect cycles using Kahn's topological sort algorithm., Return topologically sorted list of TaskNodes (dependencies first)., Return list of tasks that are topologically unblocked and ready for execution., Render a token-efficient L0 Working Memory view of task status and topology., Raised when a dependency cycle is detected in the Task DAG., TaskCycleError, test_reraises_non_transient_immediately_without_retry() (+1 more)

### Community 123 - "Plan: UI Improvements — Torchlight Codex IDE"
Cohesion: 0.18
Nodes (10): Decisions, Effort & Sequencing, Non-Goals, Plan: UI Improvements — Torchlight Codex IDE, Task 1: Fix Latent Bugs (prerequisite), Task 2: Phase 5 — Tabbed Editor Split Pane, Task 3: Phase 6a — Accessibility & Focus Management, Task 4: Phase 6b — Performance & Streaming Polish (+2 more)

### Community 124 - "Torchlight — Terminal AI Coding Agent"
Cohesion: 0.18
Nodes (11): Architecture, CLI Commands, Core Flow, Development, Error Handling, Key Features, Memory Files, Module Structure (+3 more)

### Community 125 - "IndexVisitor"
Cohesion: 0.27
Nodes (4): index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings.

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

### Community 130 - "TrajectoryRail"
Cohesion: 0.14
Nodes (7): ComposeResult, Trajectory rail for the Torchlight TUI.  Phase 2: a collapsed, status-colored ra, Flip the most recent pending dot to a terminal status., Remove all dots (called on transcript clear/reset)., Vertical spine of tool-outcome dots next to the transcript.      ``add_pending``, Append a running dot for a newly streamed/started tool call., TrajectoryRail

### Community 131 - ".from_dict"
Cohesion: 0.14
Nodes (8): Any, Create an immutable state snapshot of the DAG., Serialize DAG state for goal_spec.json backward compatibility., Deserialize DAG state from goal_spec.json dict., Atomic transaction manager for persistent goal_spec.json DAG updates., TaskStateSnapshot, TaskTransaction, test_task_transaction_atomic_file_write()

### Community 132 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 133 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 134 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 135 - "sync_workspace_tasks"
Cohesion: 0.16
Nodes (15): test_add_subtask_survives_sync_and_lands_in_plan(), test_insert_task_into_plan_section(), test_sync_preserves_stable_ids_and_fields_across_reorder(), test_sync_workspace_tasks_populates_tasks_md(), test_update_task_graph_syncs_plan(), UPDATE_TASK_GRAPH — dynamically mutate sub-tasks in .torchlight/goal_spec.json., tool_update_task_graph_impl(), insert_task_into_plan() (+7 more)

### Community 136 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 137 - "command"
Cohesion: 0.15
Nodes (13): command, chat(), compress_file(), count_tokens(), goal(), plan(), Start an interactive chat session with context management and flashlight., Start a planning session to brainstorm and write/update implementation_plan.md. (+5 more)

### Community 138 - "Textual & Rich TUI Performance and Design Rules"
Cohesion: 0.29
Nodes (6): 1. Widget Border & Alignment Discipline, 2. Modal Backdrop Opacity, 3. High-Performance Log Rendering, 4. Telemetry & Disk I/O Throttling, 5. Renderable AST Caching & Adaptive Streaming, Textual & Rich TUI Performance and Design Rules

### Community 139 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

### Community 140 - "context_manager/prompts.py"
Cohesion: 0.29
Nodes (4): verify_cli_prompt(), build_default_system_prompt(), Torchlight prompt stack — single source of truth.  V2: Optimized for local LLMs, Build system prompt. Use V2 for small contexts.

### Community 141 - "AgentMemoryWidget"
Cohesion: 0.14
Nodes (7): Parse the LLM response for action tags.         Returns: (action, thinking, cont, AgentMemoryWidget, Displays the live L0 Agent Brain Scratchpad in UI/UX Pro format with scrollbars., Return the current project root path from engine or working directory., build_plan_overview_text(), Render Implementation Plan overview (title & mode badge)., setter

### Community 143 - "core/api/lmstudio.py"
Cohesion: 0.29
Nodes (5): Re-export LMStudioClient from shared core library core.api.lmstudio., get_phase_inference_params(), LM Studio REST client.  Recovered from the original CLI implementation (commit f, Return the inference parameters preset for a named phase., httpx script

### Community 145 - "SkillResult"
Cohesion: 0.14
Nodes (9): Any, ReproSkill, MarkdownDocumentSkill, Any, Lightweight skill backed by SKILL.md.      This lets users add modular markdown, Synchronous wrapper for use from non-async contexts., Trigger real load on first call, then delegate., SkillResult (+1 more)

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

### Community 156 - "task_graph.py"
Cohesion: 0.21
Nodes (9): Enum, str, Robust Task Lifecycle and Directed Acyclic Graph (DAG) Engine for Torchlight.  P, Validate and execute status transition for a task node., Auto-complete parent if all child subtasks are COMPLETED/SKIPPED., Raised when an invalid task status transition is attempted., TaskLifecycleEvent, TaskStateTransitionError (+1 more)

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

### Community 162 - "test_tui_trajectory_rail.py"
Cohesion: 0.24
Nodes (9): anyio, Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)., The streamed <tool_call> adds a dot; the completing step flips it., test_app_pending_step_updates_rail(), test_rail_add_pending_and_complete_ok(), test_rail_clear_removes_dots(), test_rail_complete_error_and_denied(), test_rail_complete_without_pending_is_noop() (+1 more)

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

### Community 185 - "_clean_and_parse_json"
Cohesion: 0.50
Nodes (3): test_clean_and_parse_json_tolerant_multiline_content(), test_clean_and_parse_json_trailing_unterminated_string(), _clean_and_parse_json()

### Community 189 - "ConversationSummarizer"
Cohesion: 0.20
Nodes (9): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., ConversationSummarizer, Message, Summarize conversation turns for compression using high-density structured templ, Generate a high-density structured compaction template preserving key context in, Create a compact structured summary of messages., Extract key information from text. (+1 more)

### Community 192 - "iter_project_files"
Cohesion: 0.22
Nodes (9): Binding, test_build_palette_items_kinds_and_visibility(), test_iter_project_files_caps(), test_iter_project_files_skips_dot_and_vendor_dirs(), build_palette_items(), iter_project_files(), Path, Build ``(label, detail, kind, value)`` entries for the palette. (+1 more)

### Community 195 - "test_goal_mode_process.py"
Cohesion: 0.22
Nodes (9): anyio, Verify Goal mode detects missing implementation_plan.md and forces 'plan' phase., Verify Goal mode rejects premature FINAL_ANSWER on turn 1 when implementation_pl, Verify bare JSON tool calls without <tool_call> tags are correctly parsed as too, Verify solve_async in Goal Mode initializes phase to 'plan' when implementation_, test_detect_phase_goal_mode_missing_plan_forces_plan(), test_parse_response_bare_json_tool_call(), test_solve_async_goal_mode_missing_plan_rejects_premature_final_answer() (+1 more)

### Community 198 - "._execute_tool_with_approval"
Cohesion: 0.29
Nodes (4): Lock phase based on concrete execution events., _risk_tier(), _tool_kind(), _tool_label()

### Community 199 - "prompts/__init__.py"
Cohesion: 0.43
Nodes (5): build_tool_syntax_prompt(), get_tool_syntax_for_context_size(), Tool syntax instructions for Torchlight.  Generates the appropriate tool calling, Build the complete tool syntax prompt for the system message.      Args:, Return the tool calling syntax instructions appropriate for the model's context

### Community 200 - "._build_messages"
Cohesion: 0.33
Nodes (3): get_phase_system_prompt(), Infer the current agent phase from user input and the last model response., Build the final message list for the LLM, respecting the context budget.

### Community 201 - "set_ctx_window"
Cohesion: 0.27
Nodes (8): test_set_ctx_window(), Unit tests for context budget overflow detection and fixes in TieredMemory, RLME, test_tiered_memory_total_tokens_includes_pinned_files(), test_tool_context_window_scaling(), Tell the tool layer what context window the current model has., Return (MAX_LINES, MAX_CHARS) for the current context window., _read_budget_for_ctx(), set_ctx_window()

### Community 203 - "Flashlight"
Cohesion: 0.26
Nodes (4): _beam_config_for_context(), Flashlight, FileEntry, SymbolIndex

### Community 204 - ".update_file"
Cohesion: 0.32
Nodes (3): Path, Parse file via Tree-Sitter when tree_sitter library is installed., Perform an incremental O(1) AST update for a single modified file.

### Community 205 - "fuzzy_filter"
Cohesion: 0.29
Nodes (6): test_fuzzy_filter_empty_query_and_no_match(), test_fuzzy_filter_prefix_beats_substring(), fuzzy_filter(), _fuzzy_score(), Rank ``query`` against ``label``; 0 means no match.      Prefix matches beat sub, Filter ``(label, detail, kind, value)`` items by fuzzy score, best first.

### Community 206 - "MyCustomSkill"
Cohesion: 0.33
Nodes (3): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi

### Community 207 - ".pin_file"
Cohesion: 0.33
Nodes (3): Pin a recently-read file slice so it survives compression without bloating conte, Remove a file from pinned memory if deleted or stale., Re-read an edited file from disk and update its pin in memory.

### Community 209 - "ActionEntry"
Cohesion: 0.29
Nodes (3): ActionEntry, A single recorded action with its status and elapsed time., Text

### Community 211 - "test_plan_execution_loop.py"
Cohesion: 0.12
Nodes (30): test_auto_mark_does_not_complete_stub_or_missing_file(), test_auto_mark_does_not_overmark_unrelated_tasks(), test_auto_mark_matches_target_files_exact_basename(), test_auto_mark_multi_file_task_in_progress(), test_auto_mark_no_false_positive_substring(), test_auto_mark_pending_task_becomes_in_progress_without_verification(), test_auto_mark_task_completed_by_command(), test_auto_mark_task_completed_by_file() (+22 more)

### Community 212 - "test_solve_async_plan_mode_allows_final_answer_with_pending_tasks"
Cohesion: 0.40
Nodes (5): anyio, Verify that in Plan Mode, pending - [ ] tasks in implementation_plan.md do not b, Verify that in Plan Mode with no implementation_plan.md, premature FINAL_ANSWER, test_solve_async_plan_mode_allows_final_answer_with_pending_tasks(), test_solve_async_plan_mode_missing_plan_rejects_premature_final_answer()

### Community 218 - "start_mlx_server.sh"
Cohesion: 0.53
Nodes (4): log_info(), log_success(), log_warn(), start_mlx_server.sh script

### Community 219 - "test_chat_mode_verification_gate_bypassed"
Cohesion: 0.40
Nodes (5): asyncio, Verify solve_async in Chat Mode delivers <FINAL_ANSWER> directly without verific, Verify solve_async in Goal Mode rejects premature FINAL_ANSWER when no plan or t, test_chat_mode_verification_gate_bypassed(), test_goal_mode_verification_gate_rejects_premature_final_answer()

### Community 220 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

### Community 221 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 222 - "test_cli_plan_mode_session"
Cohesion: 0.67
Nodes (3): asyncio, Verify StreamingChatSession in Plan Mode correctly handles plan creation and ver, test_cli_plan_mode_session()

## Knowledge Gaps
- **436 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `context-manager-cli`, `run.sh script`, `COLORTERM` (+431 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RLMEngineOptimized` connect `RLMEngineOptimized` to `TorchlightApp`, `TieredMemory`, `on`, `AgentMemoryWidget`, `ToolCallCard`, `test_timeout_retry.py`, `test_tui_diff_view.py`, `config.py`, `test_tui_trajectory_rail.py`, `DebateVerifier`, `ExecutionFeedbackLoop`, `Step`, `get_phase_system_prompt`, `test_tui_image_viewer.py`, `ContextBudget`, `ProjectMemory`, `test_optimization_fixes.py`, `EngineConfigModal`, `test_goal_mode_process.py`, `test_ring_buffer_prompt_dedup_skip`, `test_tui_transcript_widgets.py`, `context_manager/memory/models.py`, `detect_model_traits`, `.solve_async`, `set_ctx_window`, `main_optimized.py`, `test_tui_plan_panel.py`, `._repair_stop_tokens`, `test_plan_execution_loop.py`, `test_solve_async_plan_mode_allows_final_answer_with_pending_tasks`, `PaneResizer`, `test_inline_interception.py`, `test_tui_tabbed_editor.py`, `test_chat_mode_verification_gate_bypassed`, `ProjectMemory`, `._update_params`, `test_resizer.py`, `rlm_engine_optimized.py`, `ToolResult`, `REPLSandbox`, `tui_app.py`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Why does `TieredMemory` connect `TieredMemory` to `MemoryObject`, `task_helpers.py`, `command`, `test_multimodal_vision.py`, `AgentMemoryWidget`, `RLMEngineOptimized`, `DeduplicationEngine`, `cli/main.py`, `config.py`, `._append_message`, `Step`, `tool_edit_file_impl`, `ContextBudget`, `StreamingChatSession`, `.solve_async`, `set_ctx_window`, `TestRunResult`, `.__init__`, `.pin_file`, `test_plan_execution_loop.py`, `AutonomousHarness`, `rlm_engine_optimized.py`, `REPLSandbox`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `TorchlightApp` connect `TorchlightApp` to `TrajectoryRail`, `on`, `AgentMemoryWidget`, `RLMEngineOptimized`, `GitFileTree`, `ToolCallCard`, `test_tui_diff_view.py`, `test_tui_trajectory_rail.py`, `Step`, `CommandPalette`, `get_phase_system_prompt`, `test_tui_accessibility.py`, `test_tui_image_viewer.py`, `EngineConfigModal`, `Static`, `test_tui_transcript_widgets.py`, `test_tui_plan_panel.py`, `PaneResizer`, `CloudClient`, `TranscriptView`, `test_tui_tabbed_editor.py`, `AutonomousHarness`, `OllamaClient`, `test_tui_theme.py`, `test_resizer.py`, `tui_app.py`, `MessageCard`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `TorchlightApp` (e.g. with `_StubClient` and `AutonomousHarness`) actually correct?**
  _`TorchlightApp` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `TieredMemory` (e.g. with `StreamingChatSession` and `AutonomousHarness`) actually correct?**
  _`TieredMemory` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `RLMEngineOptimized` (e.g. with `ConversationSummarizer` and `Message`) actually correct?**
  _`RLMEngineOptimized` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `MemoryConfig` (e.g. with `StreamingChatSession` and `ContextBudget`) actually correct?**
  _`MemoryConfig` has 24 INFERRED edges - model-reasoned connections that need verification._