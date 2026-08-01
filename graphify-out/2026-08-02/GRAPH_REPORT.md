# Graph Report - tourchlight v1_i6  (2026-08-01)

## Corpus Check
- 176 files · ~128,141 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2577 nodes · 4696 edges · 169 communities (136 shown, 33 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 272 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c64f57ae`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- implementations.py
- LLMStateExtractor
- ProjectSnapshot
- SymbolIndex
- ToolRegistry
- BaseSkill
- LMStudioClient
- TokenCounter
- test_prompts_and_memory.py
- ActionTracker
- core/memory/manager.py
- test_enhanced_web_tools.py
- RecoveryEngine
- test_implementations.py
- CloudClient
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
- MemoryConfig
- android_ref_runtime.md
- VerbatimCompactor
- TestRunner
- on
- ProjectGraph
- TorchlightApp
- _EvictingDeque
- TDDSkill
- context_manager/memory/manager.py
- android_ref_emulator.md
- .format_l0_scratchpad
- TokenCounter
- OllamaClient
- VerbatimCompactor
- Static
- test_ast_tool.py
- MarkdownDocumentSkill
- CalculatorSkill
- verifier.py
- tui_app.py
- tool_read_file
- Torchlight Architecture
- tool_edit_file_impl
- test_graph_engine.py
- Embedder
- discovery.py
- UnifiedSkillRegistry
- ApprovalModal
- TDDSkill
- android_ref_adb.md
- SelectiveCompressor
- LlamaCppClient
- 🦸‍♂️ Torchlight's Superpowers!
- Architecture
- classify_command
- test_code_quality_harness.py
- prompts_minimal.py
- Step
- android_ref_signing.md
- Prompt Templates for 7B Coder Models
- Torchlight Excellence Roadmap
- Checklist
- Memory System Deep Dive
- WorkingMemory
- Execution Feedback Loop
- start_optimized_local.sh
- Panel
- setup_optimized.sh
- prompts/__init__.py
- run.sh
- start_mlx_server.sh
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- context-manager-cli
- torchlight-core
- context_manager/memory/persistence.py
- datetime
- Context Manager CLI
- Torchlight — Terminal AI Coding Agent
- dashboard.py
- .agents/AGENTS.md
- TieredMemory
- Data Flow
- Core Classes
- Schema Reference
- SymbolIndex
- _HttpxLMStudioClient
- str
- Resource-Adaptive Features
- RLMEngineOptimized
- context_manager/execution/feedback_loop.py
- rules/graphify.md
- workflows/graphify.md
- web_server.py
- .clear
- ConversationSummarizer
- Target Quality Tiers
- P1: Important Follow-On Work
- Compression System
- Future Improvements
- Improvement Recommendations by Resource Tier
- Torchlight Documentation
- TieredMemory
- test_tui_plan_panel.py
- Console
- Android Troubleshoot — Routing Layer
- Memory Tiers
- Persistence
- test_phase_detection.py
- SkillResult
- Retrieval System
- ~350 tokens. Do NOT load other reference files in the same turn.
- Profile: Run -> Profile app -> Memory tab
- at android.app.Activity...          <- framework — ignore
- StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
- Context null in Fragment -> requireContext() (throws if detached, which is correct)
- implementation 'androidx.multidex:multidex:2.0.1'
- Never use StrictMode.allowThreadDiskReads() — it masks the bug
- Any
- AutonomousHarness
- ExecutionFeedbackLoop
- ActionEntry
- context_manager/prompts.py
- Protocol
- Any
- anyio
- cli/main.py
- .get_recent_changes
- HTMLParser
- Step
- .__init__
- Flashlight
- Step
- Step
- opencode.json
- Enum
- graphify.js
- Path
- HTMLGameSkill

## God Nodes (most connected - your core abstractions)
1. `TieredMemory` - 85 edges
2. `TieredMemory` - 67 edges
3. `TorchlightApp` - 58 edges
4. `AutonomousHarness` - 52 edges
5. `MemoryConfig` - 45 edges
6. `RLMEngineOptimized` - 41 edges
7. `ProjectSnapshot` - 31 edges
8. `SkillResult` - 30 edges
9. `tool_edit_file_impl()` - 27 edges
10. `get_core_registry()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `StreamingChatSession` --uses--> `InferenceParams`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/api/base.py
- `StreamingChatSession` --uses--> `AutonomousHarness`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/execution/autonomous_harness.py
- `AgentStatusModal` --uses--> `AutonomousHarness`  [INFERRED]
  rlm_optimized/tui_app.py → core/execution/autonomous_harness.py
- `ApprovalModal` --uses--> `AutonomousHarness`  [INFERRED]
  rlm_optimized/tui_app.py → core/execution/autonomous_harness.py
- `CopySelectionModal` --uses--> `AutonomousHarness`  [INFERRED]
  rlm_optimized/tui_app.py → core/execution/autonomous_harness.py

## Import Cycles
- None detected.

## Communities (169 total, 33 thin omitted)

### Community 0 - "implementations.py"
Cohesion: 0.08
Nodes (42): Tests for performance and accuracy optimizations in Torchlight., test_batch_tool_execution(), test_inline_syntax_guardrail(), test_symbol_index_mtime_cache(), _ddg_search(), _detect_doc_source(), _extract_identifiers(), _git_run() (+34 more)

### Community 1 - "LLMStateExtractor"
Cohesion: 0.13
Nodes (11): _build_excerpt(), LLMStateExtractor, _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa (+3 more)

### Community 2 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 3 - "SymbolIndex"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 4 - "ToolRegistry"
Cohesion: 0.05
Nodes (46): test_get_tool_registry(), test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_preview_dry_run(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command() (+38 more)

### Community 5 - "BaseSkill"
Cohesion: 0.10
Nodes (20): ABC, BaseSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, Any, Skills — external / plugin capabilities.  Skills are DIFFERENT from core tools: (+12 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.08
Nodes (15): _friendly_timeout_msg(), InferenceParams, LMStudioClient, Emitting <plan> blocks and <thought> reasoning.         Some creativity for step, Analysing errors and diagnosing failures.         Moderate exploration to surfac, General conversation and clarification — default settings., Return only the fields that LM Studio accepts, dropping None/defaults., One-line human-readable summary for the dashboard. (+7 more)

### Community 7 - "TokenCounter"
Cohesion: 0.07
Nodes (30): CompressionConfig, CompressionLevel, Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing., Legacy heuristic — only used when no tokenizer is injected. (+22 more)

### Community 8 - "test_prompts_and_memory.py"
Cohesion: 0.19
Nodes (10): get_phase_system_prompt(), Unified system prompts for Torchlight.  Single source of truth for all frontends, Generate phase-tailored system prompt by appending phase instructions., Unit tests for phase-tailored system prompts, anti-symptom-patching rules, and L, test_headroom_calculation(), test_l0_scratchpad_formatting(), test_persistent_memory_loading_and_prompt_inclusion(), test_phase_system_prompt_generation() (+2 more)

### Community 9 - "ActionTracker"
Cohesion: 0.22
Nodes (5): ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex

### Community 10 - "core/memory/manager.py"
Cohesion: 0.12
Nodes (31): Conversation Summarizer for Torchlight.  Extracts key information from conversat, Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, ContentChunk, ContentType, ContextSnapshot, ExecutionMode, MemoryNeedle, MemoryObject (+23 more)

### Community 11 - "test_enhanced_web_tools.py"
Cohesion: 0.11
Nodes (19): Tests for enhanced web tools and anti-blocking capabilities in core/tools/implem, test_augment_query_pep621_pyproject(), test_augment_query_with_project_deps_package_json(), test_augment_query_with_project_deps_pyproject(), test_get_browser_headers(), test_none_query_augment_handling(), test_structure_preserving_html_parser(), test_tool_web_fetch_no_url_or_none() (+11 more)

### Community 12 - "RecoveryEngine"
Cohesion: 0.06
Nodes (57): get_recovery_hint(), Recovery engine for Torchlight errors.  Provides structured recovery strategies, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type., Decide what to do after an error.          Returns a RecoveryAction indicating t, Reset all retry state (e.g., on new conversation turn)., Reset retry state for a specific error. (+49 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.09
Nodes (31): test_edit_file_impl(), test_edit_file_impl_not_found(), test_grep_hyphen_pattern(), test_grep_impl(), test_grep_impl_file_path(), test_grep_impl_no_match(), test_list_dir_impl(), test_read_file_impl() (+23 more)

### Community 14 - "CloudClient"
Cohesion: 0.06
Nodes (27): EphemeralHTTPServer, Any, HTMLParser, Path, QuietHTTPRequestHandler, Web Outcome Inspector for Torchlight.  Provides low-memory, ephemeral runtime an, Spins up a lightweight local HTTP server for static file inspection., Tier 1: Static HTML syntax and asset path validator. (+19 more)

### Community 15 - "Detailed Bug Reports & Resolutions"
Cohesion: 0.12
Nodes (16): BUG-01: `_total_llm_calls` Counter Accumulation Across Sessions, BUG-02: Verification Gate Premature Answer Bypass via Rejection State, BUG-03: Autonomous Harness Daemon Infinite Loop on Exception, BUG-04: Consecutive Code Error Loop Unbounded Retries, BUG-05: Unimported `Path` Silently Disables Feedback Loop, BUG-06: Stale Verification Gate Gatekeeping on Test Failure Reset, BUG-07: Read-Only Tool Interleaving Counter Laundering, BUG-08: LLM Step Failure Overwritten by Passing Pre-Existing Tests (+8 more)

### Community 16 - "ExecutionFeedbackLoop"
Cohesion: 0.16
Nodes (8): ExecutionFeedbackLoop, Closes the loop between code changes and test verification.          Flow:     1, Called after a tool is executed.                  Returns TestRunResult if tests, Run tests related to a source file., Run all tests in the project., Check if command is a test command., Parse test command output., TestRunResult

### Community 17 - "InferenceParams"
Cohesion: 0.07
Nodes (14): InferenceParams, Synthesis and refinement following critique. Deterministic., Send messages and return the full response., Send messages and yield response chunks., Sampling parameters forwarded to the LLM /chat/completions endpoint.     Only no, One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters. (+6 more)

### Community 18 - "ProjectMemory"
Cohesion: 0.10
Nodes (24): ensure_git_repository(), ensure_project_initialized(), init_new_project(), ProjectMemory, Path, SessionState, Ensure target project directory exists and has `.context-memory.json` persistent, Explicitly initialize a new project directory with both persistent memory files (+16 more)

### Community 19 - "repl_sandbox.py"
Cohesion: 0.16
Nodes (18): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+10 more)

### Community 20 - "android_ref_build.md"
Cohesion: 0.04
Nodes (44): ~350 tokens. Do NOT load other reference files in the same turn., <activity android:name="com.lib.X" tools:node="remove"/>, AGP 7.0-7.3 -> Gradle 7.0+, Java 11, AGP 7.4 -> Gradle 7.5+, Java 11, AGP 8.x -> Gradle 8.0+, Java 17, AGP <-> Gradle wrapper compatibility (must match):, Android Build Reference — Gradle, AGP, Dependencies, ProGuard, Manifest, android { buildFeatures { buildConfig = true } } (+36 more)

### Community 21 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 22 - "core.py"
Cohesion: 0.07
Nodes (45): classify_command(), CoreTool, CoreToolRegistry, _ddg_search(), _detect_doc_source(), _extract_identifiers(), get_core_registry(), Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Ri (+37 more)

### Community 23 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 24 - "ContextDashboard"
Cohesion: 0.10
Nodes (7): ContextDashboard, Panel, Print sub-agent task progress to the console., Return a new ActionTracker bound to this dashboard's console., Render a Rich Panel displaying sub-agent goal progress and task status breakdown, Layout, Progress

### Community 25 - "DebateVerifier"
Cohesion: 0.13
Nodes (16): CritiqueResult, DebateVerifier, Full debate flow: evaluate should_debate, execute critique, and refine if flaws, Helper to extract JSON payload from LLM response., Structured result of an adversarial critique step., Orchestrates multi-turn debate (Proposer -> Critic -> Refiner) to elevate     ou, Determine whether debate/critique should be run.          Bypasses debate for lo, Execute an adversarial critique pass using InferenceParams.for_critic(). (+8 more)

### Community 26 - "config.py"
Cohesion: 0.05
Nodes (55): test_list_available_models_includes_gemma4e4b(), test_normalize_gemma_4_4e4b_variants(), test_normalize_gemma_4_e2b_variants(), test_normalize_mlx_gemma_4_4e4b(), test_rlm_engine_solve_method(), index_directory(), IndexVisitor, init_db() (+47 more)

### Community 27 - "StreamingChatSession"
Cohesion: 0.14
Nodes (10): chat(), get_phase_system_prompt(), Start an interactive chat session with context management and flashlight., Infer the current agent phase from user input and the last model response., Auto-switch _params based on detected phase.  No-op when locked., Run out-of-band DebateVerifier pass if candidate proposal needs verification., Build the final message list for the LLM, respecting the context budget., /params                    — show current params         /params auto (+2 more)

### Community 28 - "4. Web Browsing, Anti-Blocking & Documentation Engineering"
Cohesion: 0.09
Nodes (22): 1. Context Engineering & Memory Architecture, 2. Prompt Engineering & Agent Steering, 3. Autonomous Execution & Verification, 4. Web Browsing, Anti-Blocking & Documentation Engineering, 5. Tool Call Resilience & Fault-Tolerant Parsing, A. Context Overhead vs Available Headroom, A. Defensive Auto-Routing & Graceful Fallbacks, A. Phase-Tailored Prompt Injection (+14 more)

### Community 29 - "LLMClient"
Cohesion: 0.13
Nodes (18): LLMClient, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client(), _create_cloud_client() (+10 more)

### Community 30 - "Changelog"
Cohesion: 0.09
Nodes (22): Added, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved, Added & Improved (+14 more)

### Community 31 - "build_embedder"
Cohesion: 0.19
Nodes (9): build_embedder(), Embedder, FallbackEmbedder, HashEmbedder, _normalize(), ProviderEmbedder, any, Protocol (+1 more)

### Community 32 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.15
Nodes (17): ConversationSummarizer, DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer (+9 more)

### Community 34 - "MemoryConfig"
Cohesion: 0.13
Nodes (17): MemoryConfig, test_pin_file_truncation_to_budget(), Unit tests for manual context compaction trigger and 85%/91% threshold logic., test_core_compress_recent_force(), test_core_should_compress_high_ratio_low_message_count(), test_engine_compact_context(), Tests for read/edit tool memory synchronization (unpin_file, refresh_pin)., test_memory_refresh_pin() (+9 more)

### Community 35 - "android_ref_runtime.md"
Cohesion: 0.06
Nodes (33): After enabling minification -> add -keep rule in proguard-rules.pro, All network calls must be off the main thread., Android Runtime Reference — Crashes, ANR, OOM, Lifecycle, at com.example.MyClass.foo(X.kt:42) <- YOUR code — go here, Avoid storing Activity/Context in long-lived objects — use applicationContext, class MyView @JvmOverloads constructor(, Common causes and fixes:, ctx: Context, attrs: AttributeSet? = null, defStyle: Int = 0 (+25 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (8): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 37 - "TestRunner"
Cohesion: 0.16
Nodes (8): Path, Auto-detect test framework from project structure., Run tests and return parsed results., Parse pytest output to extract test results., Parse npm test output., Parse cargo test output., Run tests and parse results for various test frameworks., TestRunner

### Community 38 - "on"
Cohesion: 0.13
Nodes (8): DirectorySelected, on, Pressed, FolderPickerModal, Modal dialog for interactive visual folder selection across the entire computer., Modal dialog for selecting session execution mode (Chat vs Goal)., SessionModePickerModal, Submitted

### Community 39 - "ProjectGraph"
Cohesion: 0.15
Nodes (13): get_project_graph(), ProjectGraph, Path, Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Scan project files and construct the AST graph., Save graph data to JSON and markdown report., Load graph from JSON file if available., Search nodes matching search_term. Returns code snippets alongside names. (+5 more)

### Community 40 - "TorchlightApp"
Cohesion: 0.08
Nodes (12): App, copy_to_clipboard(), Extract text from the TextArea, clear it, and dispatch., Extract text from the TextArea, clear it, and dispatch., Enter submits the prompt; Shift+Enter inserts a newline., Mount a widget defensively and scroll safely after layout pass., Build the AST knowledge graph for the current project_root in a         backgrou, Manually trigger memory context compaction. (+4 more)

### Community 41 - "_EvictingDeque"
Cohesion: 0.12
Nodes (11): _EvictingDeque, TokenCounter, Deque that fires a callback when an item is evicted due to maxlen., Validate all tracked file paths against the actual filesystem.         Prunes no, Minimum NEW tokens that must arrive before re-compression is allowed.          S, Pin a recently-read file so it survives compression.          If the file is alr, Remove a file from pinned memory if deleted or stale., Re-read an edited file from disk and update its pin in memory. (+3 more)

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "context_manager/memory/manager.py"
Cohesion: 0.11
Nodes (27): _extract_dep_installs(), _extract_failing_tests(), MemoryConfig, Create a MemoryConfig automatically tuned for the given context window size and, ContentChunk, ContentType, ContextSnapshot, MemoryNeedle (+19 more)

### Community 44 - "android_ref_emulator.md"
Cohesion: 0.07
Nodes (26): 1. AVD Manager -> Edit -> Graphics -> Hardware GLES 2.0  (not Software), ~200 tokens. Do NOT load other reference files in the same turn., 2. On Intel/AMD: use x86_64 system images (10-30x faster than ARM), 3. Allocate >=2 GB RAM in AVD settings, 4. Enable snapshots — saves ~25s off each boot, 5. Disable unused hardware (camera, sensors) in AVD Advanced settings, Android Emulator Reference — Setup, Acceleration, Performance, -> Android Studio -> SDK Manager -> System Images -> ARM 64 v8a (+18 more)

### Community 45 - ".format_l0_scratchpad"
Cohesion: 0.20
Nodes (6): Build the message list for the LLM.          Pinned files and dynamic L0 Scratch, Format current SessionState into a dynamic L0 working memory scratchpad for syst, Build critical context block from session state., get_workspace_pending_tasks(), Unified Task Helper Module for Torchlight.  Extracts pending tasks from implemen, Extract list of pending task descriptions from the workspace.     Priority order

### Community 46 - "TokenCounter"
Cohesion: 0.24
Nodes (9): get_token_counter(), Token counting for Torchlight.  Uses tiktoken when available, falls back to a wo, TokenCounter, test_get_token_counter_caching(), test_get_token_counter_different_models(), test_token_counter_basic(), test_token_counter_empty(), test_token_counter_truncate_long() (+1 more)

### Community 47 - "OllamaClient"
Cohesion: 0.22
Nodes (3): OllamaClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.

### Community 48 - "VerbatimCompactor"
Cohesion: 0.14
Nodes (6): CompressionConfig, Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 49 - "Static"
Cohesion: 0.19
Nodes (4): ComposeResult, AgentStatusModal, Modal dialog for complete visibility into background agent actions & status tele, Static

### Community 50 - "test_ast_tool.py"
Cohesion: 0.24
Nodes (9): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_read_symbols_indented_methods_and_duplicate_names(), test_search_ast_action_aliases(), test_search_ast_impl_fallback(), test_read_symbols_impl(), READ_SYMBOLS — show file structure without loading content., Query AST Knowledge Graph (search, path, subgraph, structure, update, summary)., tool_read_symbols_impl() (+1 more)

### Community 52 - "CalculatorSkill"
Cohesion: 0.40
Nodes (3): CalculatorSkill, Evaluate a mathematical expression safely using Python's AST., expr

### Community 53 - "verifier.py"
Cohesion: 0.40
Nodes (3): Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., DebateVerifier implementation: orchestrates adversarial critique and refinement

### Community 54 - "tui_app.py"
Cohesion: 0.24
Nodes (10): create_client(), load_last_state(), main(), ModelPickerModal, _provider_runtime_info(), Torchlight Agent — Codex / Tiny-Brain 2 Style IDE TUI (Textual) Full-featured ID, Return (port, externally_managed) for a given provider key.      externally_mana, # NOTE: The model badge button click is handled by on_model_badge_clicked (+2 more)

### Community 55 - "tool_read_file"
Cohesion: 0.16
Nodes (16): _extract_symbols(), Return (MAX_LINES, MAX_CHARS) for the current context window., Return [(lineno_1based, kind, name), ...] sorted by line number., Compact symbol map prepended to READ_FILE output., READ_FILE — read a file with optional line-range or symbol syntax.      Formats:, READ_SYMBOLS — show the structure of a file without loading its content.      Re, _read_budget(), _symbol_map() (+8 more)

### Community 56 - "Torchlight Architecture"
Cohesion: 0.08
Nodes (24): CLI (primary), Common Debugging Map, Current Status, Design Principles, End-To-End Turn Flow, Execution Feedback Loop, Execution Policy, How To Run (+16 more)

### Community 57 - "tool_edit_file_impl"
Cohesion: 0.15
Nodes (20): Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_edit_file_auto_fallback_to_write(), test_edit_file_diagnostic_nudge(), test_edit_file_diff_block_in_old_text(), test_edit_file_line_bounded(), test_edit_file_line_bounded_without_old_text(), test_edit_file_malformed_diff_diagnostic(), test_edit_file_multi_chunk() (+12 more)

### Community 58 - "test_graph_engine.py"
Cohesion: 0.31
Nodes (7): Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Path, Unit tests for Torchlight Native AST Graph Engine., test_project_graph_advanced_signatures_and_paths(), test_project_graph_build(), test_project_graph_queries(), test_tool_search_ast_integration()

### Community 59 - "Embedder"
Cohesion: 0.21
Nodes (9): build_embedder(), Embedder, HybridEmbedder, KeywordEmbedder, Embedding support for Torchlight.  Provides hybrid embedding (LLM-based + keywor, Base embedder interface., Simple keyword-based embedding fallback., Hybrid embedder: uses LLM embeddings when available, falls back to keywords. (+1 more)

### Community 60 - "discovery.py"
Cohesion: 0.18
Nodes (14): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+6 more)

### Community 61 - "UnifiedSkillRegistry"
Cohesion: 0.18
Nodes (9): Any, Robustly parses tool calls from text.         Supports:           1. JSON format, A single registry for ALL tools and skills.     Bridges the gap between core too, Synchronous wrapper for execute_skill., Unified execution bridge.         Routes to core tools or external skills as app, Condensed tool documentation injected into the system prompt.                  U, UnifiedSkillRegistry, UnifiedToolResult (+1 more)

### Community 62 - "ApprovalModal"
Cohesion: 0.12
Nodes (4): ApprovalModal, CopySelectionModal, Modal dialog for tool & file modification approval., Modal dialog to select and copy specific messages, code blocks, or text turns.

### Community 64 - "android_ref_adb.md"
Cohesion: 0.11
Nodes (18): ~200 tokens. Do NOT load other reference files in the same turn., Android ADB Reference — Device, Logcat, APK Install, APK install failures, Developer Options -> USB Debugging must be ON, Device not found / offline, Essential logcat commands, If "offline"      -> unplug/replug, different USB cable (data, not charge-only), If "unauthorized" -> revoke USB debugging on device -> replug -> re-authorize (+10 more)

### Community 65 - "SelectiveCompressor"
Cohesion: 0.12
Nodes (14): TokenCounter, Load persistent project memory (.context-memory.json) into L0 working state., CompressionConfig, CompressionLevel, Enum, Pattern, Selective Memory Compression — Progressive context reduction for local LLMs.  4-, Progressive compression that preserves semantic meaning.      Strategy:     - Re (+6 more)

### Community 66 - "LlamaCppClient"
Cohesion: 0.20
Nodes (5): LlamaCppClient, Ensure strict role alternation (user, assistant...) and merge consecutive same-r, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol., _sanitize_messages()

### Community 67 - "🦸‍♂️ Torchlight's Superpowers!"
Cohesion: 0.18
Nodes (10): 📊 Summary Table of Superpowers, 🗺️ Superpower 1: The Magic Code Map (Native AST Graph Engine), 🔫 Superpower 2: The Shrink Ray (8GB Memory Tricks), 🧠 Superpower 3: Tiny, Ultra-Smart Brains (Small Models), 🎭 Superpower 4: Changing Moods (Phase-Based Inference), 🔄 Superpower 5: The "Try Again" Loop (RLM), 🕵️‍♂️ Superpower 6: The Invisible Devil's Advocate (Out-of-Band Self-Critique), 🏃‍♂️ Superpower 7: The 24-Hour Non-Stop Marathon Engine (Autonomous Harness) (+2 more)

### Community 68 - "Architecture"
Cohesion: 0.15
Nodes (12): 1. 12k Context (TurboQuant Base — 12,288 Tokens), 2. 4k Model Fallback (4,096 Tokens), Agentic Loop, Architecture, Codebase Exploration & Token Optimization Rules, Commands, Context Budget Breakdown, Development (+4 more)

### Community 69 - "classify_command"
Cohesion: 0.26
Nodes (11): test_classify_confirm_commands(), test_classify_destructive_commands(), test_classify_empty_command(), test_classify_safe_commands(), test_classify_unknown_defaults_to_confirm(), test_classify_whitespace_handling(), classify_command(), classify_tool() (+3 more)

### Community 70 - "test_code_quality_harness.py"
Cohesion: 0.15
Nodes (19): Unit tests for Torchlight Zero-Context Code Quality Harness., test_check_syntax_js_bracket_balance(), test_check_syntax_js_string_literal_brackets(), test_check_syntax_json(), test_check_syntax_python(), test_detect_stubs(), test_format_code_on_save_fallback(), test_makefile_tab_preservation() (+11 more)

### Community 71 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 72 - "Step"
Cohesion: 0.30
Nodes (11): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Interactive approval for CONFIRM/REVIEW tier tools. (+3 more)

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

### Community 78 - "WorkingMemory"
Cohesion: 0.15
Nodes (7): Track changes and test results across the session., Record a file change., Get all currently failing tests., Guess test file path from source file., Clear all working memory., Get a summary of current state., WorkingMemory

### Community 79 - "Execution Feedback Loop"
Cohesion: 0.15
Nodes (13): Architecture, CLI Integration, Configuration, Context Injection, Core Components, Execution Feedback Loop, ExecutionFeedbackLoop, Resource Impact (+5 more)

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

### Community 104 - "context_manager/memory/persistence.py"
Cohesion: 0.22
Nodes (8): SessionState, ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, SessionPersistence, test_session_state_defaults(), test_session_state_populated()

### Community 105 - "datetime"
Cohesion: 0.23
Nodes (8): Any, Session Trajectory Logger & Audit Exporter for Torchlight.  Records full agent e, Session trajectory recorder writing structured JSONL steps to disk., TrajectoryLogger, TrajectoryStep, Tests for TrajectoryLogger., test_trajectory_logger_record_step(), datetime

### Community 106 - "Context Manager CLI"
Cohesion: 0.20
Nodes (9): Architecture, CLI Options, Commands (in CLI), Context Manager CLI, Features, How It Works, Installation, Requirements (+1 more)

### Community 107 - "Torchlight — Terminal AI Coding Agent"
Cohesion: 0.18
Nodes (11): Architecture, CLI Commands, Core Flow, Development, Error Handling, Key Features, Memory Files, Module Structure (+3 more)

### Community 108 - "dashboard.py"
Cohesion: 0.33
Nodes (3): _ActionContext, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 110 - "TieredMemory"
Cohesion: 0.06
Nodes (20): main(), CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., ContextSnapshot, Message, Persist L0 working state to disk in .context-memory.json., Pin a recently-read file slice so it survives compression without bloating conte, Remove a file from pinned memory if deleted or stale., Re-read an edited file from disk and update its pin in memory. (+12 more)

### Community 111 - "Data Flow"
Cohesion: 0.25
Nodes (8): 1. Message Ingestion, 2. Context Assembly for LLM, 3. Tool Result Processing, 4. Message Format for LLM, 5. Critical Context Injection, 6. Intent-Aware Beam Selection, 7. Tool Prediction, Data Flow

### Community 112 - "Core Classes"
Cohesion: 0.25
Nodes (8): Core Classes, Key Methods, MemoryConfig (`manager.py`), MemoryNeedle (`models.py`), MemoryObject (`models.py`), Message (`models.py`), SessionState (`models.py`), TieredMemory (`manager.py`)

### Community 113 - "Schema Reference"
Cohesion: 0.67
Nodes (3): `.context-memory.json` Schema, Schema Reference, Session File Schema

### Community 114 - "SymbolIndex"
Cohesion: 0.18
Nodes (8): Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build(), test_symbol_index_summary()

### Community 117 - "Resource-Adaptive Features"
Cohesion: 0.29
Nodes (7): Compression Cooldown, Embedding Cache, LLM State Extraction, Resource-Adaptive Configuration, Resource-Adaptive Features, Resource Tiers, Tool Result Budget

### Community 118 - "RLMEngineOptimized"
Cohesion: 0.07
Nodes (23): anyio, Return True if the most recent test run has failing or error tests., test_format_l0_scratchpad_includes_pending_tasks(), test_verification_gate_allows_final_answer_when_all_done(), test_verification_gate_rejects_premature_final_answer(), test_rlm_engine_code_tag_and_backticks(), test_rlm_engine_debate_verifier_error_resilience(), test_rlm_engine_optimized_code_execution() (+15 more)

### Community 119 - "context_manager/execution/feedback_loop.py"
Cohesion: 0.39
Nodes (6): FileChange, Enum, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, TestResult, TestResultStatus, Execution feedback loop for Torchlight.

### Community 123 - "web_server.py"
Cohesion: 0.32
Nodes (5): DashboardHTTPHandler, get_dashboard_data(), Path, Torchlight Web GUI Dashboard Server  Lightweight zero-dependency Python HTTP ser, run_dashboard_server()

### Community 124 - ".clear"
Cohesion: 0.14
Nodes (6): Get the token breakdown bucket for a role., Add tokens to the token breakdown., Remove tokens from the token breakdown., Reset token breakdown to zero., Remove oldest non-system messages to stay under max_messages limit., Remove all pinned files.

### Community 125 - "ConversationSummarizer"
Cohesion: 0.29
Nodes (6): ConversationSummarizer, Message, Summarize conversation turns for compression., Create a simple summary of messages., Extract key information from text., _role_label()

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
Cohesion: 0.09
Nodes (12): _extract_errors(), _extract_file_paths(), ContextSnapshot, Message, MessageRole, Return list of (path, content) for pinned files., Build context using selective progressive compression.          Kept as a standa, Build a compact dev-session state summary injected at context head. (+4 more)

### Community 133 - "test_tui_plan_panel.py"
Cohesion: 0.17
Nodes (11): _build_plan_text_isolated(), anyio, Isolated plan builder matching TorchlightApp logic., test_build_plan_text_all_done(), test_build_plan_text_goal_spec_json(), test_build_plan_text_no_file(), test_build_plan_text_with_tasks(), test_shortcuts_help_modal_composes() (+3 more)

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

### Community 138 - "test_phase_detection.py"
Cohesion: 0.21
Nodes (13): _make_session(), Create a StreamingChatSession with mocked heavy dependencies., Troubleshoot wins over code when both signals are present., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., test_detect_chat_phase(), test_detect_code_phase(), test_detect_phase_empty_input() (+5 more)

### Community 139 - "SkillResult"
Cohesion: 0.15
Nodes (10): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi, Any, ReproSkill, SkillResult, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement (+2 more)

### Community 140 - "Retrieval System"
Cohesion: 0.67
Nodes (3): Embedding Cache, Hybrid Search, Retrieval System

### Community 149 - "AutonomousHarness"
Cohesion: 0.05
Nodes (54): AutonomousHarness, GoalSpec, HarnessConfig, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, Ensure target project has local git repository and persistent memory initialized, Ensure a goal spec exists on disk in .torchlight, initializing a default workspa, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks. (+46 more)

### Community 151 - "ActionEntry"
Cohesion: 0.29
Nodes (3): ActionEntry, A single recorded action with its status and elapsed time., Text

### Community 152 - "context_manager/prompts.py"
Cohesion: 0.29
Nodes (4): verify_cli_prompt(), build_default_system_prompt(), Torchlight prompt stack — single source of truth.  V2: Optimized for local LLMs, Build system prompt. Use V2 for small contexts.

### Community 156 - "cli/main.py"
Cohesion: 0.17
Nodes (13): ActionTracker, command, compress_file(), count_tokens(), goal(), Start an autonomous goal execution session driven by .torchlight task tracking., Compress a file using verbatim compaction., Count tokens in text. (+5 more)

### Community 160 - ".__init__"
Cohesion: 0.25
Nodes (5): _beam_budget(), Estimate tokens consumed by system prompt, tools, and flashlight beam., Return (max_beam_files, max_lines_per_file) for the given context size., General conversation., ExecutionFeedbackLoop

### Community 161 - "Flashlight"
Cohesion: 0.20
Nodes (5): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex

### Community 164 - "opencode.json"
Cohesion: 0.50
Nodes (3): plugin, $schema, .opencode/plugins/graphify.js

### Community 168 - "HTMLGameSkill"
Cohesion: 0.33
Nodes (4): HTMLGameSkill, Any, HTML Games Generation Skill for Torchlight.  Generates complete, playable HTML g, _render()

## Knowledge Gaps
- **347 isolated node(s):** `Added & Improved`, `Added & Improved`, `Added & Improved`, `Added & Improved`, `Added & Improved` (+342 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AutonomousHarness` connect `AutonomousHarness` to `.__init__`, `MemoryConfig`, `test_tui_plan_panel.py`, `on`, `TorchlightApp`, `core/memory/manager.py`, `TieredMemory`, `Static`, `tui_app.py`, `StreamingChatSession`, `cli/main.py`, `ApprovalModal`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `RLMEngineOptimized` connect `RLMEngineOptimized` to `MemoryConfig`, `test_tui_plan_panel.py`, `on`, `Step`, `TorchlightApp`, `core/memory/manager.py`, `Static`, `AutonomousHarness`, `tui_app.py`, `ApprovalModal`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `TieredMemory` connect `TieredMemory` to `LLMStateExtractor`, `TokenCounter`, `context_manager/memory/persistence.py`, `_EvictingDeque`, `context_manager/memory/manager.py`, `ProjectMemory`, `.clear`, `build_embedder`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `TieredMemory` (e.g. with `ContextSnapshot` and `MemoryNeedle`) actually correct?**
  _`TieredMemory` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `TieredMemory` (e.g. with `LLMStateExtractor` and `ContextSnapshot`) actually correct?**
  _`TieredMemory` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TorchlightApp` (e.g. with `AutonomousHarness` and `RLMEngineOptimized`) actually correct?**
  _`TorchlightApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `AutonomousHarness` (e.g. with `StreamingChatSession` and `AgentStatusModal`) actually correct?**
  _`AutonomousHarness` has 9 INFERRED edges - model-reasoned connections that need verification._