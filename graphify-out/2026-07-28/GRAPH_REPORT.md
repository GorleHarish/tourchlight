# Graph Report - .  (2026-07-28)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1824 nodes · 3890 edges · 104 communities (92 shown, 12 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 330 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f9c15e18`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- RecoveryEngine
- TokenCounter
- ProjectSnapshot
- Flashlight
- ToolRegistry
- BaseSkill
- LMStudioClient
- TieredMemory
- AutonomousHarness
- implementations.py
- TorchlightApp
- ExecutionFeedbackLoop
- SymbolIndex
- test_implementations.py
- WebOutcomeInspector
- TieredMemory
- MemoryConfig
- InferenceParams
- ProjectMemory
- repl_sandbox.py
- test_autonomous_harness_pipeline.py
- core/memory/manager.py
- core.py
- PlanningSkill
- ContextDashboard
- DebateVerifier
- verify_m1_setup.py
- StreamingChatSession
- TestRunResult
- LLMClient
- MemoryConfig
- rlm_engine_optimized.py
- get_tool_registry
- context_manager/compression/summarizer.py
- datetime
- tui_app.py
- VerbatimCompactor
- on
- ApprovalModal
- context_manager/memory/manager.py
- _EvictingDeque
- ProjectMemory
- TDDSkill
- LLMStateExtractor
- unified.py
- CloudClient
- SkillResult
- build_embedder
- CoreToolRegistry
- tool_read_file
- VerbatimCompactor
- TokenCounter
- RLMEngineOptimized
- LlamaCppClient
- cli/main.py
- Static
- ActionTracker
- test_tools_core.py
- test_phase_detection.py
- Embedder
- discovery.py
- classify_command
- OllamaClient
- TDDSkill
- main_optimized.py
- ._prune_old_messages
- context_manager/memory/persistence.py
- IndexVisitor
- Console
- rlm_optimized/main.py
- prompts/__init__.py
- prompts_minimal.py
- _HttpxLMStudioClient
- set_ctx_window
- context_manager/prompts.py
- ActionEntry
- dashboard.py
- context_manager/compression/compactor.py
- MarkdownDocumentSkill
- verifier.py
- test_context_budget_overflow.py
- start_optimized_local.sh
- .__init__
- setup_optimized.sh
- ModelPickerModal
- run.sh
- start_mlx_server.sh
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- context-manager-cli
- torchlight-core

## God Nodes (most connected - your core abstractions)
1. `TieredMemory` - 77 edges
2. `TieredMemory` - 61 edges
3. `TorchlightApp` - 48 edges
4. `LlamaCppClient` - 37 edges
5. `AutonomousHarness` - 36 edges
6. `RLMEngineOptimized` - 36 edges
7. `StreamingChatSession` - 35 edges
8. `ProjectMemory` - 32 edges
9. `ProjectSnapshot` - 31 edges
10. `SkillResult` - 31 edges

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

## Communities (104 total, 12 thin omitted)

### Community 0 - "RecoveryEngine"
Cohesion: 0.07
Nodes (49): get_recovery_hint(), Recovery engine for Torchlight errors.  Provides structured recovery strategies, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type., Decide what to do after an error.          Returns a RecoveryAction indicating t, Reset all retry state (e.g., on new conversation turn)., Reset retry state for a specific error. (+41 more)

### Community 1 - "TokenCounter"
Cohesion: 0.07
Nodes (32): CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Pattern, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing. (+24 more)

### Community 2 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 3 - "Flashlight"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 4 - "ToolRegistry"
Cohesion: 0.08
Nodes (25): test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command(), test_tool_result_failure(), test_tool_result_success() (+17 more)

### Community 5 - "BaseSkill"
Cohesion: 0.09
Nodes (21): ABC, BaseSkill, CalculatorSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, Any (+13 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.08
Nodes (15): _friendly_timeout_msg(), InferenceParams, LMStudioClient, Emitting <plan> blocks and <thought> reasoning.         Some creativity for step, Analysing errors and diagnosing failures.         Moderate exploration to surfac, General conversation and clarification — default settings., Return only the fields that LM Studio accepts, dropping None/defaults., One-line human-readable summary for the dashboard. (+7 more)

### Community 7 - "TieredMemory"
Cohesion: 0.10
Nodes (10): ContextSnapshot, Message, MessageRole, Return list of (path, content) for pinned files., Build context using selective progressive compression.          Kept as a standa, Build a compact dev-session state summary injected at context head., TieredMemory, MemoryNeedle (+2 more)

### Community 8 - "AutonomousHarness"
Cohesion: 0.12
Nodes (25): AutonomousHarness, GoalSpec, HarnessConfig, Enum, Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks., Construct inter-task memory prompt summarizing prior verified tasks and dependen (+17 more)

### Community 9 - "implementations.py"
Cohesion: 0.09
Nodes (37): test_list_dir_impl(), test_read_symbols_impl(), _ddg_search(), _detect_doc_source(), _extract_identifiers(), _git_run(), Unified tool implementations for Torchlight.  All tool functions follow the sign, WEB_FETCH — fetch and return readable content of a URL. (+29 more)

### Community 10 - "TorchlightApp"
Cohesion: 0.13
Nodes (9): App, is_port_in_use(), Check if server port 8080 is actively listening., Step, Mount a widget defensively.          A widget reference captured before an `awai, Build the AST knowledge graph for the current project_root in a         backgrou, Codex / Tiny-Brain 2 Style Agent IDE TUI., TorchlightApp (+1 more)

### Community 11 - "ExecutionFeedbackLoop"
Cohesion: 0.08
Nodes (22): ExecutionFeedbackLoop, FileChange, Enum, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Track changes and test results across the session., Record a file change., Get all currently failing tests., Get recent file changes. (+14 more)

### Community 12 - "SymbolIndex"
Cohesion: 0.09
Nodes (16): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path (+8 more)

### Community 13 - "test_implementations.py"
Cohesion: 0.08
Nodes (37): test_edit_file_diff_block_in_old_text(), test_edit_file_with_diff_block(), test_edit_file_impl(), test_edit_file_impl_not_found(), test_grep_hyphen_pattern(), test_grep_impl(), test_grep_impl_file_path(), test_grep_impl_no_match() (+29 more)

### Community 14 - "WebOutcomeInspector"
Cohesion: 0.10
Nodes (20): EphemeralHTTPServer, Any, Path, QuietHTTPRequestHandler, Web Outcome Inspector for Torchlight.  Provides low-memory, ephemeral runtime an, Tier 1: Static HTML syntax and asset path validator., Main Inspector Subsystem driving zero-memory, ephemeral web verification., Tier 3: Run Node JSDOM script if node is available. (+12 more)

### Community 15 - "TieredMemory"
Cohesion: 0.08
Nodes (14): main(), CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., ContextSnapshot, Message, Pin a recently-read file slice so it survives compression without bloating conte, Return list of (path, content) for pinned files., Remove all pinned files., Compress older messages, preserving the first N messages. (+6 more)

### Community 16 - "MemoryConfig"
Cohesion: 0.10
Nodes (20): MemoryConfig, TokenCounter, CompressionConfig, CompressionLevel, Enum, Pattern, Selective Memory Compression — Progressive context reduction for local LLMs.  4-, Progressive compression that preserves semantic meaning.      Strategy:     - Re (+12 more)

### Community 17 - "InferenceParams"
Cohesion: 0.07
Nodes (14): InferenceParams, Synthesis and refinement following critique. Deterministic., Send messages and return the full response., Send messages and yield response chunks., Sampling parameters forwarded to the LLM /chat/completions endpoint.     Only no, One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters. (+6 more)

### Community 18 - "ProjectMemory"
Cohesion: 0.11
Nodes (21): ensure_git_repository(), ensure_project_initialized(), init_new_project(), ProjectMemory, Path, SessionState, Ensure target project directory exists and has `.context-memory.json` persistent, Explicitly initialize a new project directory with both persistent memory files (+13 more)

### Community 19 - "repl_sandbox.py"
Cohesion: 0.16
Nodes (21): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_search_ast_impl_fallback(), Query Kùzu AST graph (semantic search, signature, source, structure, subgraph)., tool_search_ast_impl(), _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast() (+13 more)

### Community 20 - "test_autonomous_harness_pipeline.py"
Cohesion: 0.12
Nodes (18): ExecutionFeedbackLoop, Enum, Path, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Build feedback context string for the LLM., Auto-run tests and web outcome inspection after code changes and inject feedback, Called after a tool is executed. Returns test results if tests were run., Detect and run the project's test suite or web inspector. (+10 more)

### Community 21 - "core/memory/manager.py"
Cohesion: 0.17
Nodes (24): Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, ContentChunk, ContentType, ContextSnapshot, MemoryNeedle, MemoryObject, Message, MessageRole (+16 more)

### Community 22 - "core.py"
Cohesion: 0.12
Nodes (26): _ddg_search(), _detect_doc_source(), _extract_identifiers(), get_core_registry(), Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Ri, GREP — fast targeted search inside a file or directory.      Returns only the ma, EDIT_FILE — surgically replace a block of text in a file with multi-tiered resil, PATCH_FILE — apply a unified diff to a file.     If preview=True, returns the re (+18 more)

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
Cohesion: 0.15
Nodes (9): chat(), Panel, Infer the current agent phase from user input and the last model response., Auto-switch _params based on detected phase.  No-op when locked., Run out-of-band DebateVerifier pass if candidate proposal needs verification., Build the final message list for the LLM, respecting the context budget., /params                    — show current params         /params auto, Start an interactive chat session with context management and flashlight.      I (+1 more)

### Community 28 - "TestRunResult"
Cohesion: 0.12
Nodes (9): Path, Auto-detect test framework from project structure., Run tests and return parsed results., Parse pytest output to extract test results., Parse npm test output., Parse cargo test output., Run tests and parse results for various test frameworks., TestRunner (+1 more)

### Community 29 - "LLMClient"
Cohesion: 0.13
Nodes (18): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client() (+10 more)

### Community 30 - "MemoryConfig"
Cohesion: 0.18
Nodes (12): ConversationSummarizer, Summarizer with LLM-powered and rule-based fallback paths.      When an llm_clie, MemoryConfig, Create a MemoryConfig automatically tuned for the given context window size and, Message, MessageRole, REPLSandbox, SolveResult (+4 more)

### Community 31 - "rlm_engine_optimized.py"
Cohesion: 0.13
Nodes (14): ConversationSummarizer, Message, Conversation Summarizer for Torchlight.  Extracts key information from conversat, Summarize conversation turns for compression., Create a simple summary of messages., Extract key information from text., _role_label(), build_step_message() (+6 more)

### Community 32 - "get_tool_registry"
Cohesion: 0.13
Nodes (18): test_search_ast_schema_validation(), test_get_tool_registry(), test_get_openai_tools_schema(), test_validate_tool_call_alias(), test_validate_tool_call_missing_required(), test_validate_tool_call_unknown_tool(), test_validate_tool_call_valid(), test_inspect_web_tool_registration() (+10 more)

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.19
Nodes (14): DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer, Message (+6 more)

### Community 34 - "datetime"
Cohesion: 0.16
Nodes (18): ContentChunk, ContentType, ContextSnapshot, MemoryNeedle, MemoryObject, Enum, WorkingSetSnapshot, test_content_chunk_custom() (+10 more)

### Community 35 - "tui_app.py"
Cohesion: 0.15
Nodes (18): _detect_apple_silicon_ram(), _detect_chip(), fetch_provider_models(), list_available_models(), normalize_model_name(), Normalize model alias names (e.g. 'gemma-2-2b', 'qwen', 'gemma 4 E2B')., Scan local models directory and returns available GGUF and MLX models., Detect Apple Silicon chip name (e.g., 'Apple M1'). (+10 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (8): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 37 - "on"
Cohesion: 0.17
Nodes (6): DirectorySelected, on, Pressed, FolderPickerModal, Modal dialog for interactive visual folder selection across the entire computer., Submitted

### Community 38 - "ApprovalModal"
Cohesion: 0.10
Nodes (6): ApprovalModal, copy_to_clipboard(), CopySelectionModal, Modal dialog for tool & file modification approval., Modal dialog to select and copy specific messages, code blocks, or text turns., Copy text to system clipboard across macOS, Linux, and Windows.

### Community 39 - "context_manager/memory/manager.py"
Cohesion: 0.20
Nodes (6): _extract_dep_installs(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _extract_tech_stack(), Pin a recently-read file so it survives compression.          If the file is alr

### Community 40 - "_EvictingDeque"
Cohesion: 0.14
Nodes (10): _EvictingDeque, TokenCounter, Deque that fires a callback when an item is evicted due to maxlen., Validate all tracked file paths against the actual filesystem.         Prunes no, Minimum NEW tokens that must arrive before re-compression is allowed.          S, Remove all pinned files., SessionState, test_session_state_defaults() (+2 more)

### Community 41 - "ProjectMemory"
Cohesion: 0.22
Nodes (4): ProjectMemory, SessionState, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "LLMStateExtractor"
Cohesion: 0.14
Nodes (11): _build_excerpt(), LLMStateExtractor, _merge_into_state(), _parse_json_response(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa (+3 more)

### Community 44 - "unified.py"
Cohesion: 0.17
Nodes (12): Run an async coroutine safely regardless of whether an event loop is already run, _run_async(), create_unified_registry(), Any, Robustly parses tool calls from text.         Supports:           1. JSON format, A single registry for ALL tools and skills.     Bridges the gap between core too, Synchronous wrapper for execute_skill., Unified execution bridge.         Routes to core tools or external skills as app (+4 more)

### Community 45 - "CloudClient"
Cohesion: 0.16
Nodes (6): CloudClient, Sanitize message roles. Convert system role to user role for models (e.g. Gemma, Async implementation of chat protocol method required by LLMClient and DebateVer, Async streaming implementation required by LLMClient protocol., Return the ids of models the provider currently reports as available.         Us, _sanitize_messages_for_cloud()

### Community 46 - "SkillResult"
Cohesion: 0.15
Nodes (10): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi, Any, ReproSkill, SkillResult, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement (+2 more)

### Community 47 - "build_embedder"
Cohesion: 0.17
Nodes (10): build_embedder(), Embedder, FallbackEmbedder, HashEmbedder, _normalize(), ProviderEmbedder, any, Protocol (+2 more)

### Community 48 - "CoreToolRegistry"
Cohesion: 0.17
Nodes (5): CoreTool, CoreToolRegistry, tool_web_fetch(), test_core_registry_get_unknown(), test_core_registry_register()

### Community 49 - "tool_read_file"
Cohesion: 0.16
Nodes (16): _extract_symbols(), Return (MAX_LINES, MAX_CHARS) for the current context window., Return [(lineno_1based, kind, name), ...] sorted by line number., Compact symbol map prepended to READ_FILE output., READ_FILE — read a file with optional line-range or symbol syntax.      Formats:, READ_SYMBOLS — show the structure of a file without loading its content.      Re, _read_budget(), _symbol_map() (+8 more)

### Community 50 - "VerbatimCompactor"
Cohesion: 0.22
Nodes (5): Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 51 - "TokenCounter"
Cohesion: 0.24
Nodes (9): get_token_counter(), Token counting for Torchlight.  Uses tiktoken when available, falls back to a wo, TokenCounter, test_get_token_counter_caching(), test_get_token_counter_different_models(), test_token_counter_basic(), test_token_counter_empty(), test_token_counter_truncate_long() (+1 more)

### Community 52 - "RLMEngineOptimized"
Cohesion: 0.18
Nodes (9): test_rlm_engine_debate_verifier_error_resilience(), test_rlm_engine_optimized_code_execution(), test_rlm_engine_optimized_debate_verifier_initialization(), test_rlm_engine_optimized_none_tool_name(), test_rlm_engine_solve_method(), Notify listeners of real-time background status and action telemetry., Re-append closing tags that were consumed as stop tokens by llama-server., Stream LLM response token-by-token cleanly without thread deadlocks. (+1 more)

### Community 53 - "LlamaCppClient"
Cohesion: 0.20
Nodes (5): LlamaCppClient, Ensure strict role alternation (user, assistant...) and merge consecutive same-r, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol., _sanitize_messages()

### Community 54 - "cli/main.py"
Cohesion: 0.19
Nodes (10): command, compress_file(), count_tokens(), Compress a file using verbatim compaction., Count tokens in text., Manage saved sessions., _risk_tier(), sessions() (+2 more)

### Community 55 - "Static"
Cohesion: 0.22
Nodes (4): ComposeResult, AgentStatusModal, Modal dialog for complete visibility into background agent actions & status tele, Static

### Community 56 - "ActionTracker"
Cohesion: 0.22
Nodes (5): ActionTracker, Shows a live panel of what the agent is doing — actions only, no content.      M, Register a new running action and refresh the display., Mark an action done and move it to history., Single-shot: print a completed action line without needing a Live         contex

### Community 57 - "test_tools_core.py"
Cohesion: 0.19
Nodes (13): classify_command(), Tell the tool layer what context window the current model has., set_ctx_window(), test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command(), test_classify_unknown_command() (+5 more)

### Community 58 - "test_phase_detection.py"
Cohesion: 0.21
Nodes (13): _make_session(), Create a StreamingChatSession with mocked heavy dependencies., Troubleshoot wins over code when both signals are present., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., test_detect_chat_phase(), test_detect_code_phase(), test_detect_phase_empty_input() (+5 more)

### Community 59 - "Embedder"
Cohesion: 0.21
Nodes (9): build_embedder(), Embedder, HybridEmbedder, KeywordEmbedder, Embedding support for Torchlight.  Provides hybrid embedding (LLM-based + keywor, Base embedder interface., Simple keyword-based embedding fallback., Hybrid embedder: uses LLM embeddings when available, falls back to keywords. (+1 more)

### Community 60 - "discovery.py"
Cohesion: 0.21
Nodes (12): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+4 more)

### Community 61 - "classify_command"
Cohesion: 0.26
Nodes (11): test_classify_confirm_commands(), test_classify_destructive_commands(), test_classify_empty_command(), test_classify_safe_commands(), test_classify_unknown_defaults_to_confirm(), test_classify_whitespace_handling(), classify_command(), classify_tool() (+3 more)

### Community 62 - "OllamaClient"
Cohesion: 0.22
Nodes (3): OllamaClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.

### Community 64 - "main_optimized.py"
Cohesion: 0.29
Nodes (11): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Step (+3 more)

### Community 65 - "._prune_old_messages"
Cohesion: 0.18
Nodes (5): Get the token breakdown bucket for a role., Add tokens to the token breakdown., Remove tokens from the token breakdown., Reset token breakdown to zero., Remove oldest non-system messages to stay under max_messages limit.

### Community 66 - "context_manager/memory/persistence.py"
Cohesion: 0.29
Nodes (5): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, SessionPersistence

### Community 67 - "IndexVisitor"
Cohesion: 0.27
Nodes (4): index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings.

### Community 68 - "Console"
Cohesion: 0.24
Nodes (6): Console, test_render_task_progress_empty(), test_render_task_progress_with_tasks(), test_action_entry_markup_safety(), test_action_tracker_print_action_safety(), test_escape_raw_brackets_and_json()

### Community 69 - "rlm_optimized/main.py"
Cohesion: 0.36
Nodes (9): create_client(), display_step(), get_depth_style(), main(), print_banner(), print_help(), Step, run_interactive() (+1 more)

### Community 70 - "prompts/__init__.py"
Cohesion: 0.31
Nodes (6): Unified system prompts for Torchlight.  Single source of truth for all frontends, build_tool_syntax_prompt(), get_tool_syntax_for_context_size(), Tool syntax instructions for Torchlight.  Generates the appropriate tool calling, Build the complete tool syntax prompt for the system message.      Args:, Return the tool calling syntax instructions appropriate for the model's context

### Community 71 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 73 - "set_ctx_window"
Cohesion: 0.25
Nodes (6): ExecutionFeedbackLoop, Path, Ensure target project has local git repository and persistent memory initialized, Tell the tool layer what context window the current model has., set_ctx_window(), TieredMemory

### Community 74 - "context_manager/prompts.py"
Cohesion: 0.29
Nodes (4): verify_cli_prompt(), build_default_system_prompt(), Torchlight prompt stack — single source of truth.  V2: Optimized for local LLMs, Build system prompt. Use V2 for small contexts.

### Community 75 - "ActionEntry"
Cohesion: 0.29
Nodes (3): ActionEntry, A single recorded action with its status and elapsed time., Text

### Community 76 - "dashboard.py"
Cohesion: 0.33
Nodes (3): _ActionContext, Per-action context manager:              with tracker.action("read_file", "src/f, Context manager returned by ActionTracker.action().

### Community 79 - "verifier.py"
Cohesion: 0.40
Nodes (3): Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., DebateVerifier implementation: orchestrates adversarial critique and refinement

### Community 80 - "test_context_budget_overflow.py"
Cohesion: 0.40
Nodes (5): Unit tests for context budget overflow detection and fixes in TieredMemory, RLME, test_tiered_memory_total_tokens_includes_pinned_files(), test_tool_context_window_scaling(), Return (MAX_LINES, MAX_CHARS) for the current context window., _read_budget_for_ctx()

### Community 81 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

### Community 82 - ".__init__"
Cohesion: 0.40
Nodes (3): _beam_budget(), Estimate tokens consumed by system prompt, tools, and flashlight beam., Return (max_beam_files, max_lines_per_file) for the given context size.

### Community 83 - "setup_optimized.sh"
Cohesion: 0.60
Nodes (3): info(), ok(), setup_optimized.sh script

## Knowledge Gaps
- **9 isolated node(s):** `context-manager-cli`, `run.sh script`, `PYTHONPATH`, `ToolResult`, `torchlight-core` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TieredMemory` connect `TieredMemory` to `._prune_old_messages`, `datetime`, `TokenCounter`, `context_manager/memory/manager.py`, `_EvictingDeque`, `ProjectMemory`, `AutonomousHarness`, `LLMStateExtractor`, `build_embedder`, `.__init__`, `RLMEngineOptimized`, `cli/main.py`, `StreamingChatSession`, `MemoryConfig`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Why does `SkillResult` connect `SkillResult` to `ProjectSnapshot`, `BaseSkill`, `TDDSkill`, `unified.py`, `MarkdownDocumentSkill`, `PlanningSkill`, `discovery.py`, `TDDSkill`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `ConnectionError` connect `RecoveryEngine` to `TorchlightApp`, `LlamaCppClient`, `CloudClient`, `OllamaClient`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `TieredMemory` (e.g. with `sessions()` and `StreamingChatSession`) actually correct?**
  _`TieredMemory` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `TieredMemory` (e.g. with `ContextSnapshot` and `MemoryNeedle`) actually correct?**
  _`TieredMemory` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `TorchlightApp` (e.g. with `CloudClient` and `LlamaCppClient`) actually correct?**
  _`TorchlightApp` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `LlamaCppClient` (e.g. with `_HttpxLMStudioClient` and `RLMEngineOptimized`) actually correct?**
  _`LlamaCppClient` has 13 INFERRED edges - model-reasoned connections that need verification._