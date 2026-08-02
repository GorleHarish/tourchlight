# Graph Report - tourchlight v1_i6  (2026-08-02)

## Corpus Check
- 194 files · ~149,128 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2992 nodes · 5878 edges · 178 communities (156 shown, 22 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 527 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `de43fb34`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- implementations.py
- test_tui_file_tree.py
- ProjectSnapshot
- SymbolIndex
- ToolRegistry
- BaseSkill
- LMStudioClient
- TokenCounter
- CloudClient
- ActionTracker
- core/memory/manager.py
- test_enhanced_web_tools.py
- RecoveryEngine
- test_implementations.py
- WebOutcomeInspector
- Detailed Bug Reports & Resolutions
- ExecutionFeedbackLoop
- InferenceParams
- ProjectMemory
- repl_sandbox.py
- android_ref_build.md
- ProjectMemory
- core.py
- PlanningSkill
- ContextDashboard
- DebateVerifier
- config.py
- StreamingChatSession
- 4. Web Browsing, Anti-Blocking & Documentation Engineering
- LLMClient
- Changelog
- build_embedder
- PyASTVisitor
- context_manager/compression/summarizer.py
- rlm_engine_optimized.py
- android_ref_runtime.md
- VerbatimCompactor
- validate_tool_call
- on
- ProjectGraph
- MemoryConfig
- _EvictingDeque
- TDDSkill
- datetime
- android_ref_emulator.md
- test_plan_execution_loop.py
- MessageCard
- OllamaClient
- VerbatimCompactor
- MemoryConfig
- get_tool_registry
- test_tui_status_bar.py
- SkillResult
- ToolCallCard
- tui_app.py
- tool_read_file
- Torchlight Architecture
- tool_edit_file_impl
- get_project_graph
- Embedder
- UnifiedSkillRegistry
- test_tui_tool_cards.py
- ToolResult
- TDDSkill
- android_ref_adb.md
- SelectiveCompressor
- rlm_optimized/main.py
- 🦸‍♂️ Torchlight's Superpowers!
- Architecture
- context_manager/memory/manager.py
- test_code_quality_harness.py
- prompts_minimal.py
- UI Improvements Plan — Industry-Standard Coding Agent UI
- android_ref_signing.md
- Prompt Templates for 7B Coder Models
- Torchlight Excellence Roadmap
- Checklist
- Memory System Deep Dive
- test_prompts_and_memory.py
- Execution Feedback Loop
- start_optimized_local.sh
- LlamaCppClient
- setup_optimized.sh
- prompts/__init__.py
- run.sh
- start_mlx_server.sh
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- context-manager-cli
- torchlight-core
- classify_command
- TrajectoryLogger
- Context Manager CLI
- Torchlight — Terminal AI Coding Agent
- CommandPalette
- .agents/AGENTS.md
- TieredMemory
- Data Flow
- Core Classes
- AutonomousHarness
- SymbolIndex
- ._build_messages
- _HttpxLMStudioClient
- Resource-Adaptive Features
- RLMEngineOptimized
- LLMStateExtractor
- rules/graphify.md
- workflows/graphify.md
- web_server.py
- context_manager/compression/compactor.py
- verifier.py
- Target Quality Tiers
- P1: Important Follow-On Work
- Compression System
- Future Improvements
- Improvement Recommendations by Resource Tier
- Torchlight Documentation
- TieredMemory
- CopySelectionModal
- dashboard.py
- Android Troubleshoot — Routing Layer
- Memory Tiers
- Persistence
- test_phase_detection.py
- MyCustomSkill
- Retrieval System
- ~350 tokens. Do NOT load other reference files in the same turn.
- Profile: Run -> Profile app -> Memory tab
- at android.app.Activity...          <- framework — ignore
- StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
- Context null in Fragment -> requireContext() (throws if detached, which is correct)
- implementation 'androidx.multidex:multidex:2.0.1'
- Never use StrictMode.allowThreadDiskReads() — it masks the bug
- ._execute_tool_with_approval
- TaskSpec
- core/execution/feedback_loop.py
- ActionEntry
- context_manager/prompts.py
- cli/main.py
- TestResult
- deque
- Schema Reference
- .action_tracker
- .compact_context
- .__init__
- Flashlight
- opencode.json
- graphify.js
- HTMLGameSkill
- ExecutionFeedbackLoop
- AgentStatusModal
- discovery.py
- test_tui_diff_view.py
- GitFileTree
- PromptTextArea
- test_tui_command_palette.py
- TrajectoryRail
- main_optimized.py
- Step
- test_context_budget_overflow.py
- command_palette.py
- TorchlightApp
- tui_widgets/__init__.py

## God Nodes (most connected - your core abstractions)
1. `TorchlightApp` - 109 edges
2. `TieredMemory` - 93 edges
3. `TieredMemory` - 79 edges
4. `RLMEngineOptimized` - 60 edges
5. `AutonomousHarness` - 58 edges
6. `MemoryConfig` - 49 edges
7. `LlamaCppClient` - 42 edges
8. `ExecutionFeedbackLoop` - 38 edges
9. `StreamingChatSession` - 36 edges
10. `SkillResult` - 33 edges

## Surprising Connections (you probably didn't know these)
- `_create_lmstudio_client()` --calls--> `LMStudioClient`  [INFERRED]
  core/api/factory.py → context-manager-cli/src/context_manager/api/lmstudio.py
- `_HttpxLMStudioClient` --uses--> `LMStudioClient`  [INFERRED]
  core/api/factory.py → context-manager-cli/src/context_manager/api/lmstudio.py
- `test_action_entry_markup_safety()` --calls--> `ActionEntry`  [EXTRACTED]
  core/tests/test_markup_escaping.py → context-manager-cli/src/context_manager/cli/dashboard.py
- `StreamingChatSession` --uses--> `DebateVerifier`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/debate/verifier.py
- `StreamingChatSession` --uses--> `AutonomousHarness`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/execution/autonomous_harness.py

## Import Cycles
- None detected.

## Communities (178 total, 22 thin omitted)

### Community 0 - "implementations.py"
Cohesion: 0.07
Nodes (52): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_read_symbols_indented_methods_and_duplicate_names(), test_run_command_intercept_ast_functions(), test_search_ast_action_aliases(), test_search_ast_impl_fallback(), test_read_symbols_impl(), test_run_command_impl(), test_run_command_impl_fail() (+44 more)

### Community 1 - "test_tui_file_tree.py"
Cohesion: 0.13
Nodes (14): _FakeProc, anyio, Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)., test_git_tree_decorates_file_labels(), test_normalize_status_code(), test_parse_git_status_porcelain_basic(), test_parse_git_status_porcelain_quoted_path(), test_parse_git_status_porcelain_rename_takes_destination() (+6 more)

### Community 2 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 3 - "SymbolIndex"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 4 - "ToolRegistry"
Cohesion: 0.13
Nodes (16): test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command(), Generate tool descriptions for injection into the system prompt.          Scales, Definition of a registered tool. (+8 more)

### Community 5 - "BaseSkill"
Cohesion: 0.09
Nodes (22): ABC, BaseSkill, CalculatorSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, MarkdownDocumentSkill (+14 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.06
Nodes (23): _friendly_timeout_msg(), InferenceParams, LMStudioClient, Emitting <plan> blocks and <thought> reasoning.         Some creativity for step, Analysing errors and diagnosing failures.         Moderate exploration to surfac, General conversation and clarification — default settings., Return only the fields that LM Studio accepts, dropping None/defaults., One-line human-readable summary for the dashboard. (+15 more)

### Community 7 - "TokenCounter"
Cohesion: 0.06
Nodes (36): count_tokens(), Count tokens in text., Manage saved sessions., sessions(), CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum (+28 more)

### Community 8 - "CloudClient"
Cohesion: 0.18
Nodes (5): CloudClient, Sanitize message roles. Convert system role to user role for models (e.g. Gemma, Async streaming implementation required by LLMClient protocol., Return the ids of models the provider currently reports as available.         Us, _sanitize_messages_for_cloud()

### Community 9 - "ActionTracker"
Cohesion: 0.16
Nodes (8): _ActionContext, ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 10 - "core/memory/manager.py"
Cohesion: 0.12
Nodes (31): Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, ContentChunk, ContentType, ContextSnapshot, ExecutionMode, MemoryNeedle (+23 more)

### Community 11 - "test_enhanced_web_tools.py"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 12 - "RecoveryEngine"
Cohesion: 0.07
Nodes (52): get_recovery_hint(), Recovery engine for Torchlight errors.  Provides structured recovery strategies, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type., Decide what to do after an error.          Returns a RecoveryAction indicating t, Reset all retry state (e.g., on new conversation turn)., Reset retry state for a specific error. (+44 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.11
Nodes (25): test_verify_compile_param(), test_edit_file_impl(), test_edit_file_impl_not_found(), test_grep_hyphen_pattern(), test_grep_impl(), test_grep_impl_file_path(), test_grep_impl_no_match(), test_list_dir_impl() (+17 more)

### Community 14 - "WebOutcomeInspector"
Cohesion: 0.09
Nodes (22): EphemeralHTTPServer, Any, HTMLParser, Path, QuietHTTPRequestHandler, Web Outcome Inspector for Torchlight.  Provides low-memory, ephemeral runtime an, Spins up a lightweight local HTTP server for static file inspection., Tier 1: Static HTML syntax and asset path validator. (+14 more)

### Community 15 - "Detailed Bug Reports & Resolutions"
Cohesion: 0.11
Nodes (17): BUG-01: `_total_llm_calls` Counter Accumulation Across Sessions, BUG-02: Verification Gate Premature Answer Bypass via Rejection State, BUG-03: Autonomous Harness Daemon Infinite Loop on Exception, BUG-04: Consecutive Code Error Loop Unbounded Retries, BUG-05: Unimported `Path` Silently Disables Feedback Loop, BUG-06: Stale Verification Gate Gatekeeping on Test Failure Reset, BUG-07: Read-Only Tool Interleaving Counter Laundering, BUG-08: LLM Step Failure Overwritten by Passing Pre-Existing Tests (+9 more)

### Community 16 - "ExecutionFeedbackLoop"
Cohesion: 0.07
Nodes (31): ExecutionFeedbackLoop, FileChange, Enum, Path, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Auto-detect test framework from project structure., Run tests and return parsed results., Parse pytest output to extract test results. (+23 more)

### Community 17 - "InferenceParams"
Cohesion: 0.06
Nodes (15): InferenceParams, Synthesis and refinement following critique. Deterministic., Send messages and return the full response., Send messages and yield response chunks., Sampling parameters forwarded to the LLM /chat/completions endpoint.     Only no, One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters. (+7 more)

### Community 18 - "ProjectMemory"
Cohesion: 0.09
Nodes (26): ensure_git_repository(), ensure_project_initialized(), init_new_project(), ProjectMemory, Path, SessionState, Ensure target project directory exists and has `.context-memory.json` persistent, Explicitly initialize a new project directory with both persistent memory files (+18 more)

### Community 19 - "repl_sandbox.py"
Cohesion: 0.21
Nodes (17): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+9 more)

### Community 20 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 21 - "ProjectMemory"
Cohesion: 0.22
Nodes (4): ProjectMemory, SessionState, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 22 - "core.py"
Cohesion: 0.06
Nodes (44): classify_command(), CoreTool, CoreToolRegistry, _ddg_search(), _detect_doc_source(), _extract_identifiers(), get_core_registry(), Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Ri (+36 more)

### Community 23 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 24 - "ContextDashboard"
Cohesion: 0.11
Nodes (6): ContextDashboard, Panel, Print sub-agent task progress to the console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 25 - "DebateVerifier"
Cohesion: 0.13
Nodes (16): CritiqueResult, DebateVerifier, Full debate flow: evaluate should_debate, execute critique, and refine if flaws, Helper to extract JSON payload from LLM response., Structured result of an adversarial critique step., Orchestrates multi-turn debate (Proposer -> Critic -> Refiner) to elevate     ou, Determine whether debate/critique should be run.          Bypasses debate for lo, Execute an adversarial critique pass using InferenceParams.for_critic(). (+8 more)

### Community 26 - "config.py"
Cohesion: 0.07
Nodes (41): test_list_available_models_includes_gemma4e4b(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), test_normalize_mlx_gemma_4_4e4b(), index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings. (+33 more)

### Community 27 - "StreamingChatSession"
Cohesion: 0.16
Nodes (10): command, chat(), goal(), Panel, Start an interactive chat session with context management and flashlight., Start an autonomous goal execution session driven by .torchlight task tracking., Auto-switch _params based on detected phase.  No-op when locked., Run out-of-band DebateVerifier pass if candidate proposal needs verification. (+2 more)

### Community 28 - "4. Web Browsing, Anti-Blocking & Documentation Engineering"
Cohesion: 0.09
Nodes (22): 1. Context Engineering & Memory Architecture, 2. Prompt Engineering & Agent Steering, 3. Autonomous Execution & Verification, 4. Web Browsing, Anti-Blocking & Documentation Engineering, 5. Tool Call Resilience & Fault-Tolerant Parsing, A. Context Overhead vs Available Headroom, A. Defensive Auto-Routing & Graceful Fallbacks, A. Phase-Tailored Prompt Injection (+14 more)

### Community 29 - "LLMClient"
Cohesion: 0.13
Nodes (18): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client() (+10 more)

### Community 30 - "Changelog"
Cohesion: 0.09
Nodes (22): Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+14 more)

### Community 31 - "build_embedder"
Cohesion: 0.17
Nodes (10): build_embedder(), Embedder, FallbackEmbedder, HashEmbedder, _normalize(), ProviderEmbedder, any, Protocol (+2 more)

### Community 32 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.18
Nodes (15): DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer, Message (+7 more)

### Community 34 - "rlm_engine_optimized.py"
Cohesion: 0.13
Nodes (14): ConversationSummarizer, Message, Conversation Summarizer for Torchlight.  Extracts key information from conversat, Summarize conversation turns for compression., Create a simple summary of messages., Extract key information from text., _role_label(), Return True if the most recent test run actually ran and has failing or (+6 more)

### Community 35 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (8): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 37 - "validate_tool_call"
Cohesion: 0.18
Nodes (13): test_get_openai_tools_schema(), test_validate_tool_call_alias(), test_validate_tool_call_missing_required(), test_validate_tool_call_unknown_tool(), test_validate_tool_call_valid(), get_openai_tools_schema(), Tool schemas and validation for Torchlight.  Defines OpenAI-compatible JSON sche, Validate a tool call against its schema and resolve parameter aliases.      Retu (+5 more)

### Community 38 - "on"
Cohesion: 0.05
Nodes (15): DirectorySelected, NamedTuple, Pressed, ApprovalModal, FileActionModal, FolderPickerModal, on, Selected (+7 more)

### Community 39 - "ProjectGraph"
Cohesion: 0.15
Nodes (12): ProjectGraph, Any, Path, Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Scan project files and construct the AST graph., Save graph data to JSON and markdown report., Load graph from JSON file if available., Search nodes matching search_term. Returns code snippets alongside names. (+4 more)

### Community 40 - "MemoryConfig"
Cohesion: 0.13
Nodes (17): MemoryConfig, test_pin_file_truncation_to_budget(), Unit tests for manual context compaction trigger and 85%/91% threshold logic., test_core_compress_recent_force(), test_core_should_compress_high_ratio_low_message_count(), test_engine_compact_context(), Tests for read/edit tool memory synchronization (unpin_file, refresh_pin)., test_memory_refresh_pin() (+9 more)

### Community 41 - "_EvictingDeque"
Cohesion: 0.18
Nodes (7): _EvictingDeque, TokenCounter, Deque that fires a callback when an item is evicted due to maxlen., Validate all tracked file paths against the actual filesystem.         Prunes no, Minimum NEW tokens that must arrive before re-compression is allowed.          S, MemoryNeedle, MemoryObject

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "datetime"
Cohesion: 0.10
Nodes (26): ContentChunk, ContentType, ContextSnapshot, MemoryNeedle, MemoryObject, Enum, SessionState, WorkingSetSnapshot (+18 more)

### Community 44 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 45 - "test_plan_execution_loop.py"
Cohesion: 0.36
Nodes (6): test_format_l0_scratchpad_includes_pending_tasks(), test_get_workspace_pending_tasks_goal_spec(), test_get_workspace_pending_tasks_md(), get_workspace_pending_tasks(), Unified Task Helper Module for Torchlight.  Extracts pending tasks from implemen, Extract list of pending task descriptions from the workspace.     Priority order

### Community 46 - "MessageCard"
Cohesion: 0.07
Nodes (29): anyio, Tests for Phase-1 transcript widgets (message cards, streaming, thinking)., Smoke test: the real app mounts MessageCards and drives the streaming view., test_app_transcript_wiring(), test_card_meta_for(), test_estimate_token_count(), test_message_card_composes(), test_streaming_view_updates() (+21 more)

### Community 47 - "OllamaClient"
Cohesion: 0.22
Nodes (4): OllamaClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol., create_client()

### Community 48 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (7): compress_file(), Compress a file using verbatim compaction., Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 49 - "MemoryConfig"
Cohesion: 0.14
Nodes (12): ConversationSummarizer, Summarizer with LLM-powered and rule-based fallback paths.      When an llm_clie, MemoryConfig, Create a MemoryConfig automatically tuned for the given context window size and, Message, MessageRole, test_rlm_engine_solve_method(), REPLSandbox (+4 more)

### Community 50 - "get_tool_registry"
Cohesion: 0.33
Nodes (6): test_search_ast_schema_validation(), test_get_tool_registry(), test_tool_registry_preview_dry_run(), test_save_memory_tool(), get_tool_registry(), Get or create the global tool registry.

### Community 51 - "test_tui_status_bar.py"
Cohesion: 0.16
Nodes (17): anyio, Tests for Phase-4 consolidated status bar (gauge + segments widget)., test_build_status_segments_defaults(), test_build_status_segments_populated(), test_build_status_segments_running_no_tps_yet(), test_build_status_segments_server_offline_and_branch_escape(), test_gauge_markup_clamps_out_of_range(), test_gauge_markup_color_escalation() (+9 more)

### Community 52 - "SkillResult"
Cohesion: 0.20
Nodes (7): Any, ReproSkill, Any, Synchronous wrapper for use from non-async contexts., Trigger real load on first call, then delegate., SkillResult, expr

### Community 53 - "ToolCallCard"
Cohesion: 0.19
Nodes (6): ComposeResult, Container, A status-aware tool call card.      Header shows the risk-tier icon, tool name,, Refresh the elapsed counter while the tool is still running., Flip the card from running to done and fill params + output.          Re-derives, ToolCallCard

### Community 54 - "tui_app.py"
Cohesion: 0.11
Nodes (19): fetch_provider_models(), Query an OpenAI-compatible /models endpoint (LM Studio, Ollama, llama.cpp)     a, load_last_state(), main(), ModelPickerModal, _provider_runtime_info(), Torchlight Agent — Codex / Tiny-Brain 2 Style IDE TUI (Textual) Full-featured ID, Return (port, externally_managed) for a given provider key.      externally_mana (+11 more)

### Community 55 - "tool_read_file"
Cohesion: 0.16
Nodes (16): _extract_symbols(), Return (MAX_LINES, MAX_CHARS) for the current context window., Return [(lineno_1based, kind, name), ...] sorted by line number., Compact symbol map prepended to READ_FILE output., READ_FILE — read a file with optional line-range or symbol syntax.      Formats:, READ_SYMBOLS — show the structure of a file without loading its content.      Re, _read_budget(), _symbol_map() (+8 more)

### Community 56 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 57 - "tool_edit_file_impl"
Cohesion: 0.14
Nodes (23): Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_auto_fallback_to_write(), test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_line_bounded(), test_edit_file_line_bounded_without_old_text(), test_edit_file_line_range_no_old_text_full_range_replace(), test_edit_file_line_range_old_text_found_replaces_within_range() (+15 more)

### Community 58 - "get_project_graph"
Cohesion: 0.25
Nodes (9): get_project_graph(), Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Get or create the ProjectGraph instance for a given root directory., Path, Unit tests for Torchlight Native AST Graph Engine., test_project_graph_advanced_signatures_and_paths(), test_project_graph_build(), test_project_graph_queries() (+1 more)

### Community 59 - "Embedder"
Cohesion: 0.21
Nodes (9): build_embedder(), Embedder, HybridEmbedder, KeywordEmbedder, Embedding support for Torchlight.  Provides hybrid embedding (LLM-based + keywor, Base embedder interface., Simple keyword-based embedding fallback., Hybrid embedder: uses LLM embeddings when available, falls back to keywords. (+1 more)

### Community 60 - "UnifiedSkillRegistry"
Cohesion: 0.19
Nodes (9): create_unified_registry(), Any, Robustly parses tool calls from text.         Supports:           1. JSON format, A single registry for ALL tools and skills.     Bridges the gap between core too, Synchronous wrapper for execute_skill., Unified execution bridge.         Routes to core tools or external skills as app, Factory to create and bootstrap the unified registry.      Reuses create_default, Condensed tool documentation injected into the system prompt.                  U (+1 more)

### Community 61 - "test_tui_tool_cards.py"
Cohesion: 0.15
Nodes (18): anyio, Tests for Phase-2 tool call cards (risk badge, status, timing, sections)., The streamed <tool_call> mounts a pending card completed by the step., test_app_pending_card_wiring(), test_risk_for_tool(), test_summarize_args(), test_tool_card_complete_denied(), test_tool_card_complete_error_expands() (+10 more)

### Community 62 - "ToolResult"
Cohesion: 0.15
Nodes (10): test_tool_result_failure(), test_tool_result_success(), Execute a tool by name with given arguments.          Validates args, executes,, Generate a dry-run preview string for a tool call without executing mutations., Execute multiple tool calls in parallel when safe (AUTO risk level).         Fal, Structured result from tool execution., Get a tool definition by name., Validate a tool call against its schema.          Returns (is_valid, error_msg, (+2 more)

### Community 63 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 64 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 65 - "SelectiveCompressor"
Cohesion: 0.12
Nodes (14): TokenCounter, Load persistent project memory (.context-memory.json) into L0 working state., CompressionConfig, CompressionLevel, Enum, Pattern, Selective Memory Compression — Progressive context reduction for local LLMs.  4-, Progressive compression that preserves semantic meaning.      Strategy:     - Re (+6 more)

### Community 66 - "rlm_optimized/main.py"
Cohesion: 0.36
Nodes (9): create_client(), display_step(), get_depth_style(), main(), print_banner(), print_help(), Step, run_interactive() (+1 more)

### Community 67 - "🦸‍♂️ Torchlight's Superpowers!"
Cohesion: 0.18
Nodes (10): 📊 Summary Table of Superpowers, 🗺️ Superpower 1: The Magic Code Map (Native AST Graph Engine), 🔫 Superpower 2: The Shrink Ray (8GB Memory Tricks), 🧠 Superpower 3: Tiny, Ultra-Smart Brains (Small Models), 🎭 Superpower 4: Changing Moods (Phase-Based Inference), 🔄 Superpower 5: The "Try Again" Loop (RLM), 🕵️‍♂️ Superpower 6: The Invisible Devil's Advocate (Out-of-Band Self-Critique), 🏃‍♂️ Superpower 7: The 24-Hour Non-Stop Marathon Engine (Autonomous Harness) (+2 more)

### Community 68 - "Architecture"
Cohesion: 0.15
Nodes (12): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Rules, Commands, Context Budget Breakdown, Development (+4 more)

### Community 69 - "context_manager/memory/manager.py"
Cohesion: 0.22
Nodes (5): _extract_dep_installs(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), MessageRole

### Community 70 - "test_code_quality_harness.py"
Cohesion: 0.08
Nodes (42): Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_compile_gate_rejects_return_outside_function(), test_detect_stubs(), test_edit_file_blocks_broken_syntax() (+34 more)

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

### Community 78 - "test_prompts_and_memory.py"
Cohesion: 0.22
Nodes (8): get_phase_system_prompt(), Unified system prompts for Torchlight.  Single source of truth for all frontends, Generate phase-tailored system prompt by appending phase instructions., Unit tests for phase-tailored system prompts, anti-symptom-patching rules, and L, test_headroom_calculation(), test_l0_scratchpad_formatting(), test_persistent_memory_loading_and_prompt_inclusion(), test_phase_system_prompt_generation()

### Community 79 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

### Community 81 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

### Community 82 - "LlamaCppClient"
Cohesion: 0.20
Nodes (5): LlamaCppClient, Ensure strict role alternation (user, assistant...) and merge consecutive same-r, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol., _sanitize_messages()

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

### Community 104 - "classify_command"
Cohesion: 0.22
Nodes (12): test_classify_confirm_commands(), test_classify_destructive_commands(), test_classify_empty_command(), test_classify_safe_commands(), test_classify_unknown_defaults_to_confirm(), test_classify_whitespace_handling(), classify_command(), classify_tool() (+4 more)

### Community 105 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 106 - "Context Manager CLI"
Cohesion: 0.20
Nodes (9): Architecture, CLI Options, Commands (in CLI), Context Manager CLI, Features, How It Works, Installation, Requirements (+1 more)

### Community 107 - "Torchlight — Terminal AI Coding Agent"
Cohesion: 0.18
Nodes (11): Architecture, CLI Commands, Core Flow, Development, Error Handling, Key Features, Memory Files, Module Structure (+3 more)

### Community 108 - "CommandPalette"
Cohesion: 0.13
Nodes (8): Changed, Highlighted, CommandPalette, ComposeResult, on, Selected, Submitted, Ctrl+P modal: fuzzy-search actions, slash commands, and files.

### Community 110 - "TieredMemory"
Cohesion: 0.07
Nodes (19): ContextSnapshot, Message, Persist L0 working state to disk in .context-memory.json., Pin a recently-read file slice so it survives compression without bloating conte, Remove a file from pinned memory if deleted or stale., Re-read an edited file from disk and update its pin in memory., Return list of (path, content) for pinned files., Remove all pinned files. (+11 more)

### Community 111 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 112 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 113 - "AutonomousHarness"
Cohesion: 0.19
Nodes (21): AutonomousHarness, HarnessConfig, ExecutionFeedbackLoop, Path, Ensure target project has local git repository and persistent memory initialized, Autonomous Harness Engine driving long-running continuous execution., main(), create_mock_feedback_loop() (+13 more)

### Community 114 - "SymbolIndex"
Cohesion: 0.18
Nodes (8): Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build(), test_symbol_index_summary()

### Community 115 - "._build_messages"
Cohesion: 0.33
Nodes (3): get_phase_system_prompt(), Infer the current agent phase from user input and the last model response., Build the final message list for the LLM, respecting the context budget.

### Community 117 - "Resource-Adaptive Features"
Cohesion: 0.29
Nodes (7): Compression Cooldown, Embedding Cache, LLM State Extraction, Resource-Adaptive Configuration, Resource-Adaptive Features, Resource Tiers, Tool Result Budget

### Community 118 - "RLMEngineOptimized"
Cohesion: 0.09
Nodes (26): anyio, test_verification_gate_allows_final_answer_when_all_done(), test_verification_gate_rejects_premature_final_answer(), test_action_tag_braces_inside_string_values(), test_action_tag_no_json_args(), test_action_tag_unclosed_with_trailing_prose(), test_clean_and_parse_json_tolerant_multiline_content(), test_clean_and_parse_json_trailing_unterminated_string() (+18 more)

### Community 119 - "LLMStateExtractor"
Cohesion: 0.29
Nodes (3): LLMStateExtractor, Uses the local LLM to extract structured SessionState fields from a     conversa, Return a copy of the call/hit/miss/error counters.

### Community 123 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 125 - "verifier.py"
Cohesion: 0.40
Nodes (3): Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., DebateVerifier implementation: orchestrates adversarial critique and refinement

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

### Community 132 - "TieredMemory"
Cohesion: 0.08
Nodes (13): ContextSnapshot, Message, Get the token breakdown bucket for a role., Add tokens to the token breakdown., Remove tokens from the token breakdown., Reset token breakdown to zero., Remove oldest non-system messages to stay under max_messages limit., Return list of (path, content) for pinned files. (+5 more)

### Community 133 - "CopySelectionModal"
Cohesion: 0.14
Nodes (18): _build_plan_text(), _make_app(), anyio, Delegate to the real TUI plan-builder helper., Repeated checklist entries (summary + detailed sections) must not duplicate., test_build_plan_text_all_done(), test_build_plan_text_dedupes_duplicate_checkbox_lines(), test_build_plan_text_goal_spec_json() (+10 more)

### Community 134 - "dashboard.py"
Cohesion: 0.23
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

### Community 138 - "test_phase_detection.py"
Cohesion: 0.21
Nodes (13): _make_session(), Create a StreamingChatSession with mocked heavy dependencies., Troubleshoot wins over code when both signals are present., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., test_detect_chat_phase(), test_detect_code_phase(), test_detect_phase_empty_input() (+5 more)

### Community 139 - "MyCustomSkill"
Cohesion: 0.33
Nodes (3): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi

### Community 140 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 148 - "._execute_tool_with_approval"
Cohesion: 0.40
Nodes (3): _risk_tier(), _tool_kind(), _tool_label()

### Community 149 - "TaskSpec"
Cohesion: 0.12
Nodes (12): GoalSpec, Enum, str, Ensure a goal spec exists on disk in .torchlight, initializing a default workspa, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks., Construct inter-task memory prompt summarizing prior verified tasks and dependen, Run a single micro-epoch for a target task. (+4 more)

### Community 150 - "core/execution/feedback_loop.py"
Cohesion: 0.18
Nodes (12): Enum, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Return True only if a run succeeded. Uses exit code as the authoritative, TestResultStatus, TestRunResult, create_mock_feedback_loop(), ExecutionFeedbackLoop, Path (+4 more)

### Community 152 - "context_manager/prompts.py"
Cohesion: 0.29
Nodes (4): verify_cli_prompt(), build_default_system_prompt(), Torchlight prompt stack — single source of truth.  V2: Optimized for local LLMs, Build system prompt. Use V2 for small contexts.

### Community 153 - "cli/main.py"
Cohesion: 0.21
Nodes (9): get_token_counter(), Token counting for Torchlight.  Uses tiktoken when available, falls back to a wo, TokenCounter, test_get_token_counter_caching(), test_get_token_counter_different_models(), test_token_counter_basic(), test_token_counter_empty(), test_token_counter_truncate_long() (+1 more)

### Community 154 - "TestResult"
Cohesion: 0.19
Nodes (7): Path, Freshly verify any modified-but-unverified files and return True if         ever, Run fast pre-flight auto-fixer/linter on modified files before test execution., Detect and run the project's test suite or web inspector., TestResult, Quiet runners (e.g. `pytest -q`) produce no per-test markers; exit code     must, test_all_passed_uses_exit_code()

### Community 155 - "deque"
Cohesion: 0.29
Nodes (4): Pin a recently-read file so it survives compression.          If the file is alr, Remove a file from pinned memory if deleted or stale., Re-read an edited file from disk and update its pin in memory., deque

### Community 156 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

### Community 160 - ".__init__"
Cohesion: 0.40
Nodes (3): _beam_budget(), Estimate tokens consumed by system prompt, tools, and flashlight beam., Return (max_beam_files, max_lines_per_file) for the given context size.

### Community 161 - "Flashlight"
Cohesion: 0.20
Nodes (5): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex

### Community 164 - "opencode.json"
Cohesion: 0.50
Nodes (3): plugin, $schema, .opencode/plugins/graphify.js

### Community 168 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

### Community 169 - "ExecutionFeedbackLoop"
Cohesion: 0.10
Nodes (26): ExecutionFeedbackLoop, extract_surgical_traceback(), Auto-run tests and web outcome inspection after code changes and inject feedback, Called after a tool is executed. Returns test results if tests were run., Convert current failing TestRunResult into a structured TestFailureError for Rec, Build feedback context string for the LLM with surgical error injection., Extract strictly surgical failure traceback from test output, removing passing t, Project with nothing to verify must not trip the verification gate. (+18 more)

### Community 171 - "AgentStatusModal"
Cohesion: 0.12
Nodes (10): Horizontal, AgentStatusModal, ComposeResult, Modal dialog for complete visibility into background agent actions & status tele, ComposeResult, Consolidated status bar for the Torchlight TUI.  Phase 4: one glanceable row tha, Single-row consolidated status bar (Phase 4).      Hosted where the old text met, StatusBar (+2 more)

### Community 174 - "discovery.py"
Cohesion: 0.21
Nodes (12): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+4 more)

### Community 177 - "test_tui_diff_view.py"
Cohesion: 0.08
Nodes (36): anyio, Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)., A pre-write snapshot (from approval) wins over the already-written disk state., The engine's own CODE_FILE_WRITE approval path is diffable too., The approval modal shows a DIFF PREVIEW section when entries exist., A successful WRITE_FILE step mounts a DiffView card with real content., test_app_write_step_renders_diff_card(), test_approval_modal_omits_diff_when_empty() (+28 more)

### Community 178 - "GitFileTree"
Cohesion: 0.14
Nodes (15): DirectoryTree, DirEntry, git_status_for_tree(), GitFileTree, Path, Git-aware file tree for the Torchlight TUI.  Phase 4: the explorer's ``Directory, Check if a directory name should be skipped from exploration., Filter out OS noise, cache directories, and internal state files. (+7 more)

### Community 180 - "PromptTextArea"
Cohesion: 0.19
Nodes (6): PromptTextArea, Message, TextArea whose Enter submits instead of inserting a newline.      Hooks ``update, Posted when the user presses Enter with no active suggestion., SubmitRequested, TextArea

### Community 181 - "test_tui_command_palette.py"
Cohesion: 0.13
Nodes (23): Binding, anyio, Tests for Phase-4 command palette + prompt autocomplete., test_build_palette_items_kinds_and_visibility(), test_command_palette_composes_filters_and_selects(), test_command_palette_enter_runs_highlighted_item(), test_iter_project_files_caps(), test_iter_project_files_skips_dot_and_vendor_dirs() (+15 more)

### Community 182 - "TrajectoryRail"
Cohesion: 0.14
Nodes (7): ComposeResult, Trajectory rail for the Torchlight TUI.  Phase 2: a collapsed, status-colored ra, Flip the most recent pending dot to a terminal status., Remove all dots (called on transcript clear/reset)., Vertical spine of tool-outcome dots next to the transcript.      ``add_pending``, Append a running dot for a newly streamed/started tool call., TrajectoryRail

### Community 185 - "main_optimized.py"
Cohesion: 0.24
Nodes (12): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Step (+4 more)

### Community 186 - "Step"
Cohesion: 0.15
Nodes (12): anyio, Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)., The streamed <tool_call> adds a dot; the completing step flips it., test_app_pending_step_updates_rail(), test_rail_add_pending_and_complete_ok(), test_rail_clear_removes_dots(), test_rail_complete_error_and_denied(), test_rail_complete_without_pending_is_noop() (+4 more)

### Community 192 - "test_context_budget_overflow.py"
Cohesion: 0.40
Nodes (5): Unit tests for context budget overflow detection and fixes in TieredMemory, RLME, test_tiered_memory_total_tokens_includes_pinned_files(), test_tool_context_window_scaling(), Tell the tool layer what context window the current model has., set_ctx_window()

### Community 195 - "command_palette.py"
Cohesion: 0.29
Nodes (7): test_fuzzy_filter_empty_query_and_no_match(), test_fuzzy_filter_prefix_beats_substring(), fuzzy_filter(), _fuzzy_score(), Command palette + slash-command autocomplete for the Torchlight TUI.  Phase 4: *, Rank ``query`` against ``label``; 0 means no match.      Prefix matches beat sub, Filter ``(label, detail, kind, value)`` items by fuzzy score, best first.

### Community 197 - "TorchlightApp"
Cohesion: 0.06
Nodes (19): App, FileSelected, NodeSelected, is_port_in_use(), Check if server port 8080 is actively listening., copy_to_clipboard(), Step, Codex / Tiny-Brain 2 Style Agent IDE TUI. (+11 more)

## Knowledge Gaps
- **363 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `context-manager-cli`, `run.sh script`, `COLORTERM` (+358 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AutonomousHarness` connect `AutonomousHarness` to `.__init__`, `SymbolIndex`, `TieredMemory`, `CopySelectionModal`, `dashboard.py`, `on`, `MemoryConfig`, `TorchlightApp`, `core/memory/manager.py`, `AgentStatusModal`, `ExecutionFeedbackLoop`, `TaskSpec`, `core/execution/feedback_loop.py`, `tui_app.py`, `cli/main.py`, `Step`, `StreamingChatSession`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `TorchlightApp` connect `TorchlightApp` to `CopySelectionModal`, `on`, `CloudClient`, `AgentStatusModal`, `CommandPalette`, `MessageCard`, `OllamaClient`, `test_tui_diff_view.py`, `AutonomousHarness`, `LlamaCppClient`, `PromptTextArea`, `GitFileTree`, `tui_app.py`, `RLMEngineOptimized`, `ToolCallCard`, `TrajectoryRail`, `Step`, `test_tui_tool_cards.py`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Why does `RLMEngineOptimized` connect `RLMEngineOptimized` to `TieredMemory`, `CopySelectionModal`, `ExecutionFeedbackLoop`, `ProjectMemory`, `ProjectMemory`, `DebateVerifier`, `.compact_context`, `rlm_engine_optimized.py`, `on`, `MemoryConfig`, `AgentStatusModal`, `test_plan_execution_loop.py`, `MessageCard`, `test_tui_diff_view.py`, `MemoryConfig`, `tui_app.py`, `main_optimized.py`, `Step`, `test_tui_tool_cards.py`, `TorchlightApp`, `LlamaCppClient`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `TorchlightApp` (e.g. with `AutonomousHarness` and `CloudClient`) actually correct?**
  _`TorchlightApp` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `TieredMemory` (e.g. with `ContextSnapshot` and `MemoryNeedle`) actually correct?**
  _`TieredMemory` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `TieredMemory` (e.g. with `sessions()` and `StreamingChatSession`) actually correct?**
  _`TieredMemory` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `RLMEngineOptimized` (e.g. with `ConversationSummarizer` and `ExecutionFeedbackLoop`) actually correct?**
  _`RLMEngineOptimized` has 19 INFERRED edges - model-reasoned connections that need verification._