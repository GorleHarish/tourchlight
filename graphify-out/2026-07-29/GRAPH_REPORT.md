# Graph Report - tourchlight v1_i6  (2026-07-29)

## Corpus Check
- 164 files · ~242,109 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2404 nodes · 4395 edges · 168 communities (137 shown, 31 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 237 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b241ad6e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- implementations.py
- cli/main.py
- ProjectSnapshot
- Flashlight
- ToolRegistry
- BaseSkill
- LMStudioClient
- TokenCounter
- LlamaCppClient
- MessageRole
- .update_sidebar_meta
- RecoveryEngine
- TorchlightError
- test_implementations.py
- CloudClient
- core/execution/feedback_loop.py
- SelectiveCompressor
- InferenceParams
- test_project_init.py
- repl_sandbox.py
- android_ref_build.md
- ProjectMemory
- core.py
- PlanningSkill
- ContextDashboard
- DebateVerifier
- verify_m1_setup.py
- StreamingChatSession
- 1. Context Engineering & Memory Architecture
- LLMClient
- Changelog
- RLMEngineOptimized
- PyASTVisitor
- context_manager/compression/summarizer.py
- classify_command
- android_ref_runtime.md
- VerbatimCompactor
- test_autonomous_harness.py
- on
- ProjectGraph
- TorchlightApp
- config.py
- TDDSkill
- context_manager/memory/persistence.py
- android_ref_emulator.md
- tui_app.py
- SkillResult
- ExecutionFeedbackLoop
- VerbatimCompactor
- tool_read_file
- MemoryConfig
- TokenCounter
- build_embedder
- ActionTracker
- core/memory/__init__.py
- TestRunResult
- Torchlight Architecture
- tool_edit_file_impl
- test_graph_engine.py
- Embedder
- discovery.py
- Message
- OllamaClient
- TDDSkill
- android_ref_adb.md
- unified.py
- Static
- 🦸‍♂️ Torchlight's Superpowers!
- Architecture
- TieredMemory
- test_code_quality_harness.py
- prompts_minimal.py
- rlm_engine.py
- android_ref_signing.md
- Prompt Templates for 7B Coder Models
- Torchlight Excellence Roadmap
- Checklist
- Memory System Deep Dive
- MarkdownDocumentSkill
- Execution Feedback Loop
- verifier.py
- start_optimized_local.sh
- .refresh_pin
- setup_optimized.sh
- prompts/__init__.py
- run.sh
- start_mlx_server.sh
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- context-manager-cli
- torchlight-core
- _EvictingDeque
- TrajectoryLogger
- Context Manager CLI
- Torchlight — Terminal AI Coding Agent
- TieredMemory
- CoreToolRegistry
- Step
- Data Flow
- Core Classes
- main_optimized.py
- SymbolIndex
- _HttpxLMStudioClient
- IndexVisitor
- Resource-Adaptive Features
- test_context_budget_overflow.py
- Indexed Nodes
- rules/graphify.md
- workflows/graphify.md
- P0: Highest-Leverage Work
- test_phase_detection.py
- test_tools_core.py
- context_manager/memory/manager.py
- P1: Important Follow-On Work
- Compression System
- Future Improvements
- Improvement Recommendations by Resource Tier
- Torchlight Documentation
- dashboard.py
- test_tui_plan_panel.py
- Console
- Android Troubleshoot — Routing Layer
- Memory Tiers
- Persistence
- test_prompts_and_memory.py
- Schema Reference
- Retrieval System
- ~350 tokens. Do NOT load other reference files in the same turn.
- Profile: Run -> Profile app -> Memory tab
- at android.app.Activity...          <- framework — ignore
- StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
- Context null in Fragment -> requireContext() (throws if detached, which is correct)
- implementation 'androidx.multidex:multidex:2.0.1'
- Never use StrictMode.allowThreadDiskReads() — it masks the bug
- get_tool_registry
- AutonomousHarness
- ._build_messages
- ProjectMemory
- context_manager/prompts.py
- test_autonomous_harness_pipeline.py
- ._calculate_metadata_overhead
- ConversationSummarizer
- ActionEntry
- .handle
- Panel
- ContextSnapshot
- Message
- Flashlight
- TokenCounter
- .clear
- Enum
- ExecutionFeedbackLoop
- Path
- TieredMemory

## God Nodes (most connected - your core abstractions)
1. `TieredMemory` - 75 edges
2. `TieredMemory` - 67 edges
3. `TorchlightApp` - 54 edges
4. `AutonomousHarness` - 31 edges
5. `ProjectSnapshot` - 31 edges
6. `SkillResult` - 31 edges
7. `MemoryConfig` - 30 edges
8. `get_core_registry()` - 29 edges
9. `BaseSkill` - 28 edges
10. `ProjectMemory` - 26 edges

## Surprising Connections (you probably didn't know these)
- `StreamingChatSession` --uses--> `MemoryConfig`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/memory/manager.py
- `RLMEngineOptimized` --uses--> `MemoryConfig`  [INFERRED]
  rlm_optimized/rlm_engine_optimized.py → core/memory/manager.py
- `StreamingChatSession` --uses--> `TieredMemory`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/memory/manager.py
- `RLMEngineOptimized` --uses--> `TieredMemory`  [INFERRED]
  rlm_optimized/rlm_engine_optimized.py → core/memory/manager.py
- `SolveResult` --uses--> `TieredMemory`  [INFERRED]
  rlm_optimized/rlm_engine_optimized.py → core/memory/manager.py

## Import Cycles
- None detected.

## Communities (168 total, 31 thin omitted)

### Community 0 - "implementations.py"
Cohesion: 0.09
Nodes (37): test_list_dir_impl(), test_read_symbols_impl(), _ddg_search(), _detect_doc_source(), _extract_identifiers(), _git_run(), Unified tool implementations for Torchlight.  All tool functions follow the sign, READ_SYMBOLS — show file structure without loading content. (+29 more)

### Community 1 - "cli/main.py"
Cohesion: 0.15
Nodes (13): ActionTracker, command, _beam_budget(), compress_file(), count_tokens(), Compress a file using verbatim compaction., Count tokens in text., Manage saved sessions. (+5 more)

### Community 2 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 3 - "Flashlight"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 4 - "ToolRegistry"
Cohesion: 0.08
Nodes (26): test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command(), test_tool_result_failure(), test_tool_result_success() (+18 more)

### Community 5 - "BaseSkill"
Cohesion: 0.09
Nodes (21): ABC, BaseSkill, CalculatorSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, Any (+13 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.08
Nodes (15): _friendly_timeout_msg(), InferenceParams, LMStudioClient, Emitting <plan> blocks and <thought> reasoning.         Some creativity for step, Analysing errors and diagnosing failures.         Moderate exploration to surfac, General conversation and clarification — default settings., Return only the fields that LM Studio accepts, dropping None/defaults., One-line human-readable summary for the dashboard. (+7 more)

### Community 7 - "TokenCounter"
Cohesion: 0.07
Nodes (32): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing. (+24 more)

### Community 8 - "LlamaCppClient"
Cohesion: 0.20
Nodes (5): LlamaCppClient, Ensure strict role alternation (user, assistant...) and merge consecutive same-r, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol., _sanitize_messages()

### Community 9 - "MessageRole"
Cohesion: 0.14
Nodes (12): _build_excerpt(), LLMStateExtractor, _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa (+4 more)

### Community 10 - ".update_sidebar_meta"
Cohesion: 0.16
Nodes (4): Mount a widget defensively and scroll safely after layout pass., Build the AST knowledge graph for the current project_root in a         backgrou, Step, work

### Community 11 - "RecoveryEngine"
Cohesion: 0.14
Nodes (20): get_recovery_hint(), Manages recovery strategies across the agentic loop.      Tracks per-error-type, Reset all retry state (e.g., on new conversation turn)., Reset retry state for a specific error., Return a one-line hint for the LLM on how to recover from this error., RecoveryEngine, Tool execution failed., Path or command outside allowed scope. (+12 more)

### Community 12 - "TorchlightError"
Cohesion: 0.12
Nodes (26): Recovery engine for Torchlight errors.  Provides structured recovery strategies, Tracks retry state for a specific error pattern., RecoveryState, ConnectionError, ContextOverflowError, ParseError, Enum, Exception (+18 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.11
Nodes (26): test_edit_file_impl(), test_edit_file_impl_not_found(), test_grep_hyphen_pattern(), test_grep_impl(), test_grep_impl_file_path(), test_grep_impl_no_match(), test_read_file_impl(), test_read_file_impl_not_found() (+18 more)

### Community 14 - "CloudClient"
Cohesion: 0.06
Nodes (27): EphemeralHTTPServer, Any, Path, QuietHTTPRequestHandler, Web Outcome Inspector for Torchlight.  Provides low-memory, ephemeral runtime an, Tier 1: Static HTML syntax and asset path validator., Main Inspector Subsystem driving zero-memory, ephemeral web verification., Tier 3: Run Node JSDOM script if node is available. (+19 more)

### Community 15 - "core/execution/feedback_loop.py"
Cohesion: 0.18
Nodes (12): Post-edit auto-run test suite failure., TestFailureError, extract_surgical_traceback(), Enum, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Extract strictly surgical failure traceback from test output, removing passing t, TestResultStatus, TestRunResult (+4 more)

### Community 16 - "SelectiveCompressor"
Cohesion: 0.16
Nodes (11): CompressionConfig, CompressionLevel, Enum, Pattern, Selective Memory Compression — Progressive context reduction for local LLMs.  4-, Progressive compression that preserves semantic meaning.      Strategy:     - Re, Compress a list of messages using progressive levels., SelectiveCompressor (+3 more)

### Community 17 - "InferenceParams"
Cohesion: 0.06
Nodes (15): InferenceParams, Synthesis and refinement following critique. Deterministic., Send messages and return the full response., Send messages and yield response chunks., Sampling parameters forwarded to the LLM /chat/completions endpoint.     Only no, One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters. (+7 more)

### Community 18 - "test_project_init.py"
Cohesion: 0.15
Nodes (18): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, Ensure target project directory exists and has `.context-memory.json` persistent, Explicitly initialize a new project directory with both persistent memory files, Ensure target project directory exists and has a local Git repository initialize, temp_project_dir() (+10 more)

### Community 19 - "repl_sandbox.py"
Cohesion: 0.19
Nodes (17): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+9 more)

### Community 20 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 21 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 22 - "core.py"
Cohesion: 0.13
Nodes (24): _ddg_search(), _detect_doc_source(), _extract_identifiers(), get_core_registry(), Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Ri, GREP — fast targeted search inside a file or directory.      Returns only the ma, EDIT_FILE — surgically replace a block of text in a file with multi-tiered resil, PATCH_FILE — apply a unified diff to a file.     If preview=True, returns the re (+16 more)

### Community 23 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 24 - "ContextDashboard"
Cohesion: 0.10
Nodes (7): ContextDashboard, Panel, Print sub-agent task progress to the console., Return a new ActionTracker bound to this dashboard's console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 25 - "DebateVerifier"
Cohesion: 0.13
Nodes (16): CritiqueResult, DebateVerifier, Full debate flow: evaluate should_debate, execute critique, and refine if flaws, Helper to extract JSON payload from LLM response., Structured result of an adversarial critique step., Orchestrates multi-turn debate (Proposer -> Critic -> Refiner) to elevate     ou, Determine whether debate/critique should be run.          Bypasses debate for lo, Execute an adversarial critique pass using InferenceParams.for_critic(). (+8 more)

### Community 26 - "verify_m1_setup.py"
Cohesion: 0.18
Nodes (24): format_memory_status(), get_memory_pressure(), is_memory_safe(), Memory pressure monitor for macOS Apple Silicon.  Provides real-time memory pres, Return a human-readable one-line memory status string., Get current macOS memory pressure level and stats.      Returns:         dict wi, Quick check: is it safe to run inference without swap thrashing?      Args:, check_hardware() (+16 more)

### Community 27 - "StreamingChatSession"
Cohesion: 0.22
Nodes (6): chat(), Run out-of-band DebateVerifier pass if candidate proposal needs verification., /params                    — show current params         /params auto, Start an interactive chat session with context management and flashlight.      I, StreamingChatSession, Panel

### Community 28 - "1. Context Engineering & Memory Architecture"
Cohesion: 0.15
Nodes (12): 1. Context Engineering & Memory Architecture, 2. Prompt Engineering & Agent Steering, 3. Autonomous Execution & Verification, A. Context Overhead vs Available Headroom, A. Phase-Tailored Prompt Injection, A. Surgical Traceback Extraction, Architectural Learnings & Engineering Principles, B. Anti-Symptom-Patching Directives (+4 more)

### Community 29 - "LLMClient"
Cohesion: 0.13
Nodes (18): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client() (+10 more)

### Community 30 - "Changelog"
Cohesion: 0.29
Nodes (6): Added, Added & Improved, Changelog, Fixed & Improved, [v1.7.0] - 2026-07-29, [v1.8.0] - 2026-07-29

### Community 31 - "RLMEngineOptimized"
Cohesion: 0.09
Nodes (16): Ensure target project has local git repository and persistent memory initialized, test_rlm_engine_debate_verifier_error_resilience(), test_rlm_engine_optimized_code_execution(), test_rlm_engine_optimized_debate_verifier_initialization(), test_rlm_engine_optimized_none_tool_name(), test_rlm_engine_solve_method(), ExecutionFeedbackLoop, Path (+8 more)

### Community 32 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.16
Nodes (16): ConversationSummarizer, DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer (+8 more)

### Community 34 - "classify_command"
Cohesion: 0.10
Nodes (26): test_classify_confirm_commands(), test_classify_destructive_commands(), test_classify_empty_command(), test_classify_safe_commands(), test_classify_unknown_defaults_to_confirm(), test_classify_whitespace_handling(), test_get_openai_tools_schema(), test_validate_tool_call_alias() (+18 more)

### Community 35 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (8): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 37 - "test_autonomous_harness.py"
Cohesion: 0.25
Nodes (13): HarnessConfig, main(), CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., create_mock_feedback_loop(), ExecutionFeedbackLoop, Path, Unit tests for AutonomousHarness module., test_auto_git_init_and_clean_commit() (+5 more)

### Community 38 - "on"
Cohesion: 0.19
Nodes (5): DirectorySelected, on, FolderPickerModal, Modal dialog for interactive visual folder selection across the entire computer., Submitted

### Community 39 - "ProjectGraph"
Cohesion: 0.15
Nodes (13): get_project_graph(), ProjectGraph, Any, Path, Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Scan project files and construct the AST graph., Save graph data to JSON and markdown report., Load graph from JSON file if available. (+5 more)

### Community 40 - "TorchlightApp"
Cohesion: 0.12
Nodes (6): App, copy_to_clipboard(), Manually trigger memory context compaction., Copy text to system clipboard across macOS, Linux, and Windows., Codex / Tiny-Brain 2 Style Agent IDE TUI., TorchlightApp

### Community 41 - "config.py"
Cohesion: 0.13
Nodes (13): _detect_apple_silicon_ram(), _detect_chip(), fetch_provider_models(), is_port_in_use(), list_available_models(), normalize_model_name(), Normalize model alias names (e.g. 'gemma-2-2b', 'qwen', 'gemma 4 E2B')., Scan local models directory and returns available GGUF and MLX models. (+5 more)

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "context_manager/memory/persistence.py"
Cohesion: 0.10
Nodes (28): MemoryConfig, Create a MemoryConfig automatically tuned for the given context window size and, ContentChunk, ContentType, ContextSnapshot, MemoryNeedle, MemoryObject, Message (+20 more)

### Community 44 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 45 - "tui_app.py"
Cohesion: 0.09
Nodes (15): Pressed, ApprovalModal, CopySelectionModal, create_client(), load_last_state(), main(), ModelPickerModal, _provider_runtime_info() (+7 more)

### Community 46 - "SkillResult"
Cohesion: 0.15
Nodes (10): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi, Any, ReproSkill, SkillResult, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement (+2 more)

### Community 47 - "ExecutionFeedbackLoop"
Cohesion: 0.15
Nodes (11): ExecutionFeedbackLoop, Path, Auto-run tests and web outcome inspection after code changes and inject feedback, Called after a tool is executed. Returns test results if tests were run., Run fast pre-flight auto-fixer/linter on modified files before test execution., Detect and run the project's test suite or web inspector., Convert current failing TestRunResult into a structured TestFailureError for Rec, Build feedback context string for the LLM with surgical error injection. (+3 more)

### Community 48 - "VerbatimCompactor"
Cohesion: 0.14
Nodes (6): CompressionConfig, Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 49 - "tool_read_file"
Cohesion: 0.16
Nodes (16): _extract_symbols(), Return (MAX_LINES, MAX_CHARS) for the current context window., Return [(lineno_1based, kind, name), ...] sorted by line number., Compact symbol map prepended to READ_FILE output., READ_FILE — read a file with optional line-range or symbol syntax.      Formats:, READ_SYMBOLS — show the structure of a file without loading its content.      Re, _read_budget(), _symbol_map() (+8 more)

### Community 50 - "MemoryConfig"
Cohesion: 0.15
Nodes (14): MemoryConfig, Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, Token counting for Torchlight.  Uses tiktoken when available, falls back to a wo, Unit tests for manual context compaction trigger and 85%/91% threshold logic., test_core_compress_recent_force(), test_core_should_compress_high_ratio_low_message_count(), test_engine_compact_context(), Tests for read/edit tool memory synchronization (unpin_file, refresh_pin). (+6 more)

### Community 51 - "TokenCounter"
Cohesion: 0.27
Nodes (8): get_token_counter(), TokenCounter, test_get_token_counter_caching(), test_get_token_counter_different_models(), test_token_counter_basic(), test_token_counter_empty(), test_token_counter_truncate_long(), test_token_counter_truncate_short()

### Community 52 - "build_embedder"
Cohesion: 0.19
Nodes (9): build_embedder(), Embedder, FallbackEmbedder, HashEmbedder, _normalize(), ProviderEmbedder, any, Protocol (+1 more)

### Community 53 - "ActionTracker"
Cohesion: 0.22
Nodes (5): ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex

### Community 54 - "core/memory/__init__.py"
Cohesion: 0.17
Nodes (23): Conversation Summarizer for Torchlight.  Extracts key information from conversat, ContentChunk, ContentType, ContextSnapshot, MemoryNeedle, MemoryObject, Message, MessageRole (+15 more)

### Community 55 - "TestRunResult"
Cohesion: 0.06
Nodes (31): ExecutionFeedbackLoop, FileChange, Enum, Path, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Auto-detect test framework from project structure., Run tests and return parsed results., Parse pytest output to extract test results. (+23 more)

### Community 56 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 57 - "tool_edit_file_impl"
Cohesion: 0.15
Nodes (18): Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_line_bounded(), test_edit_file_line_bounded_without_old_text(), test_edit_file_malformed_diff_diagnostic(), test_edit_file_multi_chunk(), test_edit_file_symbol_anchored() (+10 more)

### Community 58 - "test_graph_engine.py"
Cohesion: 0.32
Nodes (6): Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Path, Unit tests for Torchlight Native AST Graph Engine., test_project_graph_build(), test_project_graph_queries(), test_tool_search_ast_integration()

### Community 59 - "Embedder"
Cohesion: 0.21
Nodes (9): build_embedder(), Embedder, HybridEmbedder, KeywordEmbedder, Embedding support for Torchlight.  Provides hybrid embedding (LLM-based + keywor, Base embedder interface., Simple keyword-based embedding fallback., Hybrid embedder: uses LLM embeddings when available, falls back to keywords. (+1 more)

### Community 60 - "discovery.py"
Cohesion: 0.21
Nodes (12): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+4 more)

### Community 61 - "Message"
Cohesion: 0.17
Nodes (5): Message, Get the token breakdown bucket for a role., Add tokens to the token breakdown., Remove tokens from the token breakdown., Remove oldest non-system messages to stay under max_messages limit.

### Community 62 - "OllamaClient"
Cohesion: 0.24
Nodes (3): OllamaClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.

### Community 64 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 65 - "unified.py"
Cohesion: 0.17
Nodes (12): Run an async coroutine safely regardless of whether an event loop is already run, _run_async(), create_unified_registry(), Any, Robustly parses tool calls from text.         Supports:           1. JSON format, A single registry for ALL tools and skills.     Bridges the gap between core too, Synchronous wrapper for execute_skill., Unified execution bridge.         Routes to core tools or external skills as app (+4 more)

### Community 66 - "Static"
Cohesion: 0.20
Nodes (4): ComposeResult, AgentStatusModal, Modal dialog for complete visibility into background agent actions & status tele, Static

### Community 67 - "🦸‍♂️ Torchlight's Superpowers!"
Cohesion: 0.18
Nodes (10): 📊 Summary Table of Superpowers, 🗺️ Superpower 1: The Magic Code Map (Native AST Graph Engine), 🔫 Superpower 2: The Shrink Ray (8GB Memory Tricks), 🧠 Superpower 3: Tiny, Ultra-Smart Brains (Small Models), 🎭 Superpower 4: Changing Moods (Phase-Based Inference), 🔄 Superpower 5: The "Try Again" Loop (RLM), 🕵️‍♂️ Superpower 6: The Invisible Devil's Advocate (Out-of-Band Self-Critique), 🏃‍♂️ Superpower 7: The 24-Hour Non-Stop Marathon Engine (Autonomous Harness) (+2 more)

### Community 68 - "Architecture"
Cohesion: 0.17
Nodes (11): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Commands, Context Budget Breakdown, Development, Key Design Decisions (+3 more)

### Community 69 - "TieredMemory"
Cohesion: 0.13
Nodes (6): ContextSnapshot, Return list of (path, content) for pinned files., Build context using selective progressive compression.          Kept as a standa, Build a compact dev-session state summary injected at context head., TieredMemory, WorkingSetSnapshot

### Community 70 - "test_code_quality_harness.py"
Cohesion: 0.11
Nodes (26): Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_detect_stubs(), test_format_code_on_save_fallback(), test_makefile_tab_preservation() (+18 more)

### Community 71 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 72 - "rlm_engine.py"
Cohesion: 0.14
Nodes (16): create_client(), display_step(), get_depth_style(), main(), print_banner(), print_help(), Step, run_interactive() (+8 more)

### Community 73 - "android_ref_signing.md"
Cohesion: 0.12
Nodes (16): ~200 tokens. Do NOT load other reference files in the same turn., Android Signing Reference — Keystore, Certificates, Google Play, app/build.gradle:, Common errors, Enroll: Play Console -> App -> Setup -> App signing, Generate a new debug keystore (if lost), Google manages the release key; you upload with a separate upload key, Google Play App Signing (recommended) (+8 more)

### Community 74 - "Prompt Templates for 7B Coder Models"
Cohesion: 0.13
Nodes (14): Breaking Complex Tasks into Chained Prompts, General Rules for 7B Models, Key Characteristics of 7B Models, Prompt Pattern: Chained Development, Prompt Templates for 7B Coder Models, Structure, Structure, Structure (+6 more)

### Community 75 - "Torchlight Excellence Roadmap"
Cohesion: 0.15
Nodes (13): 1. Smarter Retrieval, 2. Adaptive Prompt Compression, 4. Terminal UX Polish, Current Strengths, Design Principle, Goal, P2: Longer-Horizon Upgrades, Success Criteria (+5 more)

### Community 76 - "Checklist"
Cohesion: 0.15
Nodes (13): 1. Slash Command Verification, 2. Runtime Hardening, 3. Process Hygiene, 4. Provider and Model Verification, 5. Local-Model Efficiency, 6. Context-Rot and Memory Durability, 7. Retry And Cancel Semantics, Already Completed (+5 more)

### Community 77 - "Memory System Deep Dive"
Cohesion: 0.15
Nodes (12): Allocation for 4k Context, Architecture Overview, Auto-tuned Budgets by Context Size, Auto-tuning, CLI Integration, Configuration Commands, Configuration Commands, File Locations (+4 more)

### Community 79 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

### Community 80 - "verifier.py"
Cohesion: 0.40
Nodes (3): Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., DebateVerifier implementation: orchestrates adversarial critique and refinement

### Community 81 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

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
Nodes (4): COLORTERM, PYTHONPATH, tui.sh script, TERM

### Community 104 - "_EvictingDeque"
Cohesion: 0.16
Nodes (8): _EvictingDeque, TokenCounter, Deque that fires a callback when an item is evicted due to maxlen., Validate all tracked file paths against the actual filesystem.         Prunes no, Minimum NEW tokens that must arrive before re-compression is allowed.          S, Remove a file from pinned memory if deleted or stale., deque, MemoryObject

### Community 105 - "TrajectoryLogger"
Cohesion: 0.25
Nodes (7): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step()

### Community 106 - "Context Manager CLI"
Cohesion: 0.20
Nodes (9): Architecture, CLI Options, Commands (in CLI), Context Manager CLI, Features, How It Works, Installation, Requirements (+1 more)

### Community 107 - "Torchlight — Terminal AI Coding Agent"
Cohesion: 0.20
Nodes (10): Architecture, CLI Commands, Core Flow, Development, Error Handling, Key Features, Memory Files, Module Structure (+2 more)

### Community 108 - "TieredMemory"
Cohesion: 0.07
Nodes (18): ContextSnapshot, Pin a recently-read file slice so it survives compression without bloating conte, Remove a file from pinned memory if deleted or stale., Re-read an edited file from disk and update its pin in memory., Return list of (path, content) for pinned files., Remove all pinned files., Compress older messages, preserving the first N messages., Async wrapper for compress_recent. (+10 more)

### Community 109 - "CoreToolRegistry"
Cohesion: 0.16
Nodes (6): CoreTool, CoreToolRegistry, tool_save_memory(), tool_web_fetch(), test_core_registry_get_unknown(), test_core_registry_register()

### Community 111 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 112 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 113 - "main_optimized.py"
Cohesion: 0.27
Nodes (12): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Step (+4 more)

### Community 114 - "SymbolIndex"
Cohesion: 0.18
Nodes (8): Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build(), test_symbol_index_summary()

### Community 116 - "IndexVisitor"
Cohesion: 0.27
Nodes (4): index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings.

### Community 117 - "Resource-Adaptive Features"
Cohesion: 0.29
Nodes (7): Compression Cooldown, Embedding Cache, LLM State Extraction, Resource-Adaptive Configuration, Resource-Adaptive Features, Resource Tiers, Tool Result Budget

### Community 118 - "test_context_budget_overflow.py"
Cohesion: 0.32
Nodes (7): Unit tests for context budget overflow detection and fixes in TieredMemory, RLME, test_tiered_memory_total_tokens_includes_pinned_files(), test_tool_context_window_scaling(), Tell the tool layer what context window the current model has., Return (MAX_LINES, MAX_CHARS) for the current context window., _read_budget_for_ctx(), set_ctx_window()

### Community 119 - "Indexed Nodes"
Cohesion: 0.50
Nodes (3): Indexed Nodes, Key Classes & Functions, Torchlight Knowledge Graph Report

### Community 123 - "P0: Highest-Leverage Work"
Cohesion: 0.33
Nodes (6): 1. Execution Policy Router, 2. Explicit Working-Set Builder, 3. Stronger Action Extraction, 4. Provider and Model Truth Model, 5. Failure-Classified Retries, P0: Highest-Leverage Work

### Community 124 - "test_phase_detection.py"
Cohesion: 0.21
Nodes (13): _make_session(), Create a StreamingChatSession with mocked heavy dependencies., Troubleshoot wins over code when both signals are present., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., test_detect_chat_phase(), test_detect_code_phase(), test_detect_phase_empty_input() (+5 more)

### Community 125 - "test_tools_core.py"
Cohesion: 0.16
Nodes (15): classify_command(), Tell the tool layer what context window the current model has., set_ctx_window(), test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command(), test_classify_unknown_command() (+7 more)

### Community 126 - "context_manager/memory/manager.py"
Cohesion: 0.17
Nodes (9): _extract_dep_installs(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _extract_tech_stack(), MessageRole, WorkingSetSnapshot, test_working_set_snapshot_defaults() (+1 more)

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

### Community 132 - "dashboard.py"
Cohesion: 0.33
Nodes (3): _ActionContext, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 133 - "test_tui_plan_panel.py"
Cohesion: 0.17
Nodes (11): anyio, _build_plan_text_isolated(), Isolated plan builder matching TorchlightApp logic., test_build_plan_text_all_done(), test_build_plan_text_goal_spec_json(), test_build_plan_text_no_file(), test_build_plan_text_with_tasks(), test_shortcuts_help_modal_composes() (+3 more)

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

### Community 138 - "test_prompts_and_memory.py"
Cohesion: 0.24
Nodes (7): get_phase_system_prompt(), Unified system prompts for Torchlight.  Single source of truth for all frontends, Generate phase-tailored system prompt by appending phase instructions., Unit tests for phase-tailored system prompts, anti-symptom-patching rules, and L, test_headroom_calculation(), test_l0_scratchpad_formatting(), test_phase_system_prompt_generation()

### Community 139 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

### Community 140 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 148 - "get_tool_registry"
Cohesion: 0.22
Nodes (10): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_search_ast_impl_fallback(), test_search_ast_schema_validation(), test_batch_tool_execution(), test_get_tool_registry(), test_tool_registry_preview_dry_run(), Query AST Knowledge Graph (search, path, subgraph, structure, update, summary)., tool_search_ast_impl() (+2 more)

### Community 149 - "AutonomousHarness"
Cohesion: 0.14
Nodes (14): AutonomousHarness, GoalSpec, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks., Construct inter-task memory prompt summarizing prior verified tasks and dependen, Run a single micro-epoch for a target task., Run continuous autonomous daemon until completion or timeout. (+6 more)

### Community 150 - "._build_messages"
Cohesion: 0.25
Nodes (4): get_phase_system_prompt(), Infer the current agent phase from user input and the last model response., Auto-switch _params based on detected phase.  No-op when locked., Build the final message list for the LLM, respecting the context budget.

### Community 152 - "context_manager/prompts.py"
Cohesion: 0.29
Nodes (4): verify_cli_prompt(), build_default_system_prompt(), Torchlight prompt stack — single source of truth.  V2: Optimized for local LLMs, Build system prompt. Use V2 for small contexts.

### Community 153 - "test_autonomous_harness_pipeline.py"
Cohesion: 0.43
Nodes (7): create_mock_feedback_loop(), ExecutionFeedbackLoop, Path, Unit tests for Inter-Task Context Pipeline, Dependencies, and File Collision Gua, test_inter_task_output_summary_injection(), test_target_file_collision_detection(), test_task_dependencies_and_execution_ordering()

### Community 155 - "ConversationSummarizer"
Cohesion: 0.29
Nodes (6): ConversationSummarizer, Message, Summarize conversation turns for compression., Create a simple summary of messages., Extract key information from text., _role_label()

### Community 157 - ".handle"
Cohesion: 0.33
Nodes (3): Generate a dedup key for this error type., Decide what to do after an error.          Returns a RecoveryAction indicating t, Check if we should escalate to the user after exhausting retries.

### Community 161 - "Flashlight"
Cohesion: 0.20
Nodes (5): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex

## Knowledge Gaps
- **314 isolated node(s):** `Commands`, `Module Structure`, `1. 12k Context (TurboQuant Base — 12,288 Tokens)`, `2. 4k Model Fallback (4,096 Tokens)`, `Agentic Loop` (+309 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TieredMemory` connect `TieredMemory` to `cli/main.py`, `test_autonomous_harness.py`, `rlm_engine.py`, `test_prompts_and_memory.py`, `SelectiveCompressor`, `MemoryConfig`, `AutonomousHarness`, `core/memory/__init__.py`, `test_context_budget_overflow.py`, `test_autonomous_harness_pipeline.py`, `StreamingChatSession`, `RLMEngineOptimized`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `TieredMemory` connect `TieredMemory` to `.clear`, `TokenCounter`, `_EvictingDeque`, `MessageRole`, `rlm_engine.py`, `context_manager/memory/persistence.py`, `.refresh_pin`, `build_embedder`, `ProjectMemory`, `Message`, `context_manager/memory/manager.py`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `SkillResult` connect `SkillResult` to `unified.py`, `ProjectSnapshot`, `BaseSkill`, `TDDSkill`, `MarkdownDocumentSkill`, `PlanningSkill`, `discovery.py`, `TDDSkill`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `TieredMemory` (e.g. with `StreamingChatSession` and `AutonomousHarness`) actually correct?**
  _`TieredMemory` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `TieredMemory` (e.g. with `LLMStateExtractor` and `ContextSnapshot`) actually correct?**
  _`TieredMemory` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ProjectSnapshot` (e.g. with `BaseSkill` and `SkillResult`) actually correct?**
  _`ProjectSnapshot` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Commands`, `Module Structure`, `1. 12k Context (TurboQuant Base — 12,288 Tokens)` to the rest of the system?**
  _314 weakly-connected nodes found - possible documentation gaps or missing edges._