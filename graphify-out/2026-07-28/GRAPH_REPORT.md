# Graph Report - tourchlight v1_i6  (2026-07-28)

## Corpus Check
- 156 files · ~240,440 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1972 nodes · 3764 edges · 116 communities (93 shown, 23 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 202 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `97a826bb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- RecoveryEngine
- context_manager/memory/manager.py
- ProjectSnapshot
- Flashlight
- ToolRegistry
- BaseSkill
- LMStudioClient
- TieredMemory
- AutonomousHarness
- implementations.py
- TorchlightApp
- TestRunResult
- Flashlight
- test_implementations.py
- test_web_inspector.py
- TieredMemory
- SelectiveCompressor
- InferenceParams
- core/memory/persistence.py
- repl_sandbox.py
- Enum
- rlm_engine.py
- core.py
- PlanningSkill
- ContextDashboard
- DebateVerifier
- config.py
- cli/main.py
- Learnings in Building Local SLM Coding Agents
- LLMClient
- 2026-07-24
- rlm_engine_optimized.py
- get_tool_registry
- context_manager/compression/summarizer.py
- MemoryConfig
- SelectiveCompressor
- VerbatimCompactor
- on
- ApprovalModal
- ProjectGraph
- ExecutionFeedbackLoop
- ProjectMemory
- TDDSkill
- LLMStateExtractor
- UnifiedSkillRegistry
- CloudClient
- SkillResult
- test_autonomous_harness.py
- test_optimizations.py
- tool_read_file
- VerbatimCompactor
- core/memory/__init__.py
- RLMEngineOptimized
- LlamaCppClient
- core/tests/test_models.py
- Static
- ProjectMemory
- test_diff_edit.py
- test_phase_detection.py
- Embedder
- discovery.py
- classify_command
- OllamaClient
- TDDSkill
- main_optimized.py
- CopySelectionModal
- PyASTVisitor
- 🦸‍♂️ Torchlight's Superpowers!
- Architecture
- RLMEngine
- get_project_graph
- prompts_minimal.py
- _HttpxLMStudioClient
- Any
- autonomous_harness.py
- MarkdownDocumentSkill
- build_embedder
- start_optimized_local.sh
- setup_optimized.sh
- unified.py
- run.sh
- start_mlx_server.sh
- tui.sh
- context_manager/__init__.py
- core/__init__.py
- context-manager-cli
- torchlight-core
- tui_app.py
- Enum
- ContextSnapshot
- Message
- TokenCounter
- TieredMemory
- ._run_agent
- test_tools_core.py
- SymbolIndex
- context_manager/memory/persistence.py
- test_autonomous_harness_pipeline.py
- Indexed Nodes
- rules/graphify.md
- workflows/graphify.md
- FileEntry
- SymbolIndex
- Step

## God Nodes (most connected - your core abstractions)
1. `TieredMemory` - 65 edges
2. `TieredMemory` - 58 edges
3. `TorchlightApp` - 43 edges
4. `ProjectSnapshot` - 31 edges
5. `SkillResult` - 31 edges
6. `Learnings in Building Local SLM Coding Agents` - 30 edges
7. `AutonomousHarness` - 30 edges
8. `get_core_registry()` - 29 edges
9. `BaseSkill` - 28 edges
10. `StreamingChatSession` - 26 edges

## Surprising Connections (you probably didn't know these)
- `StreamingChatSession` --uses--> `ExecutionFeedbackLoop`  [INFERRED]
  context-manager-cli/src/context_manager/cli/main.py → core/execution/feedback_loop.py
- `RLMEngineOptimized` --uses--> `MemoryConfig`  [INFERRED]
  rlm_optimized/rlm_engine_optimized.py → core/memory/manager.py
- `RLMEngineOptimized` --uses--> `TieredMemory`  [INFERRED]
  rlm_optimized/rlm_engine_optimized.py → core/memory/manager.py
- `SolveResult` --uses--> `TieredMemory`  [INFERRED]
  rlm_optimized/rlm_engine_optimized.py → core/memory/manager.py
- `Step` --uses--> `TieredMemory`  [INFERRED]
  rlm_optimized/rlm_engine_optimized.py → core/memory/manager.py

## Import Cycles
- None detected.

## Communities (116 total, 23 thin omitted)

### Community 0 - "RecoveryEngine"
Cohesion: 0.07
Nodes (49): get_recovery_hint(), Recovery engine for Torchlight errors.  Provides structured recovery strategies, Tracks retry state for a specific error pattern., Manages recovery strategies across the agentic loop.      Tracks per-error-type, Generate a dedup key for this error type., Decide what to do after an error.          Returns a RecoveryAction indicating t, Reset all retry state (e.g., on new conversation turn)., Reset retry state for a specific error. (+41 more)

### Community 1 - "context_manager/memory/manager.py"
Cohesion: 0.12
Nodes (21): _extract_dep_installs(), CompressionConfig, CompressionLevel, create_progressive_compressor(), Enum, Selective Memory Compression - Progressive context reduction for local LLMs.  FI, Configuration for selective memory compression., Create a compressor tuned for the given context window.      Always pass the sha (+13 more)

### Community 2 - "ProjectSnapshot"
Cohesion: 0.10
Nodes (32): AndroidTroubleshootSkill, _diagnose(), ProjectSnapshot, Any, Path, AndroidTroubleshootSkill — auto-loaded by Torchlight at startup.  Diagnoses and, True if ANY of the given signals are present., True if pattern found in any of the named file labels. (+24 more)

### Community 3 - "Flashlight"
Cohesion: 0.08
Nodes (21): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex, Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, Scale beam size to the model's context window.         Call once when the model, Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to     the model (+13 more)

### Community 4 - "ToolRegistry"
Cohesion: 0.08
Nodes (28): test_tool_registry_execute(), test_tool_registry_execute_unknown(), test_tool_registry_get(), test_tool_registry_register(), test_tool_registry_risk_level(), test_tool_registry_risk_level_run_command(), test_tool_result_failure(), test_tool_result_success() (+20 more)

### Community 5 - "BaseSkill"
Cohesion: 0.09
Nodes (21): ABC, BaseSkill, CalculatorSkill, create_default_registry(), _extract_markdown_skill_metadata(), GitSkill, _LazySkill, Any (+13 more)

### Community 6 - "LMStudioClient"
Cohesion: 0.08
Nodes (15): _friendly_timeout_msg(), InferenceParams, LMStudioClient, Emitting <plan> blocks and <thought> reasoning.         Some creativity for step, Analysing errors and diagnosing failures.         Moderate exploration to surfac, General conversation and clarification — default settings., Return only the fields that LM Studio accepts, dropping None/defaults., One-line human-readable summary for the dashboard. (+7 more)

### Community 7 - "TieredMemory"
Cohesion: 0.05
Nodes (26): _EvictingDeque, _extract_errors(), _extract_failing_tests(), _extract_file_paths(), ContextSnapshot, Message, MessageRole, TokenCounter (+18 more)

### Community 8 - "AutonomousHarness"
Cohesion: 0.13
Nodes (13): AutonomousHarness, GoalSpec, ExecutionFeedbackLoop, Path, Return pending tasks whose dependencies are all VERIFIED., Return list of target files that collide with active or failed tasks., Construct inter-task memory prompt summarizing prior verified tasks and dependen, Run a single micro-epoch for a target task. (+5 more)

### Community 9 - "implementations.py"
Cohesion: 0.07
Nodes (34): _ddg_search(), _detect_doc_source(), _extract_identifiers(), _git_run(), _grep_python(), _grep_rg(), Unified tool implementations for Torchlight.  All tool functions follow the sign, WEB_FETCH — fetch and return readable content of a URL. (+26 more)

### Community 10 - "TorchlightApp"
Cohesion: 0.18
Nodes (3): App, Codex / Tiny-Brain 2 Style Agent IDE TUI., TorchlightApp

### Community 11 - "TestRunResult"
Cohesion: 0.06
Nodes (31): ExecutionFeedbackLoop, FileChange, Enum, Path, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, Auto-detect test framework from project structure., Run tests and return parsed results., Parse pytest output to extract test results. (+23 more)

### Community 12 - "Flashlight"
Cohesion: 0.21
Nodes (5): _beam_config_for_context(), BeamResult, Flashlight, FileEntry, SymbolIndex

### Community 13 - "test_implementations.py"
Cohesion: 0.10
Nodes (30): test_edit_file_diff_block_in_old_text(), test_edit_file_with_diff_block(), test_edit_file_impl(), test_edit_file_impl_not_found(), test_grep_hyphen_pattern(), test_grep_impl(), test_grep_impl_file_path(), test_grep_impl_no_match() (+22 more)

### Community 14 - "test_web_inspector.py"
Cohesion: 0.08
Nodes (24): EphemeralHTTPServer, Any, Path, QuietHTTPRequestHandler, Web Outcome Inspector for Torchlight.  Provides low-memory, ephemeral runtime an, Tier 1: Static HTML syntax and asset path validator., Main Inspector Subsystem driving zero-memory, ephemeral web verification., Tier 3: Run Node JSDOM script if node is available. (+16 more)

### Community 15 - "TieredMemory"
Cohesion: 0.08
Nodes (14): ContextSnapshot, Pin a recently-read file slice so it survives compression without bloating conte, Return list of (path, content) for pinned files., Remove all pinned files., Compress older messages, preserving the first N messages., Async wrapper for compress_recent., Build the message list for the LLM.          Pinned files are injected as a syst, Build critical context block from session state. (+6 more)

### Community 16 - "SelectiveCompressor"
Cohesion: 0.19
Nodes (8): CompressionConfig, Pattern, Progressive compression that preserves semantic meaning.      Strategy:     - Re, Compress a list of messages using progressive levels., SelectiveCompressor, TurnSummary, test_selective_compressor_custom_config(), test_selective_compressor_defaults()

### Community 17 - "InferenceParams"
Cohesion: 0.07
Nodes (14): InferenceParams, Synthesis and refinement following critique. Deterministic., Send messages and return the full response., Send messages and yield response chunks., Sampling parameters forwarded to the LLM /chat/completions endpoint.     Only no, One-line description of current params., Convert to API payload dict, excluding None and default values., Writing code files. Near-deterministic — exact syntax matters. (+6 more)

### Community 18 - "core/memory/persistence.py"
Cohesion: 0.17
Nodes (16): ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, Session and project memory persistence for Torchlight., Ensure target project directory exists and has `.context-memory.json` persistent, Explicitly initialize a new project directory with both persistent memory files, Ensure target project directory exists and has a local Git repository initialize (+8 more)

### Community 19 - "repl_sandbox.py"
Cohesion: 0.16
Nodes (18): _ast_db_missing_message(), get_class_signature(), _get_encoder(), get_function_ast(), get_function_source(), get_kuzu_connection(), get_local_subgraph(), get_project_structure() (+10 more)

### Community 21 - "rlm_engine.py"
Cohesion: 0.15
Nodes (15): ConversationSummarizer, Message, Conversation Summarizer for Torchlight.  Extracts key information from conversat, Summarize conversation turns for compression., Create a simple summary of messages., Extract key information from text., _role_label(), ContentType (+7 more)

### Community 22 - "core.py"
Cohesion: 0.12
Nodes (27): _ddg_search(), _detect_doc_source(), _extract_identifiers(), get_core_registry(), Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.  Ri, GREP — fast targeted search inside a file or directory.      Returns only the ma, EDIT_FILE — surgically replace a block of text in a file with multi-tiered resil, PATCH_FILE — apply a unified diff to a file.     If preview=True, returns the re (+19 more)

### Community 23 - "PlanningSkill"
Cohesion: 0.13
Nodes (14): ExecutionPlan, PlanningSkill, PlanStep, Any, Planning Skill for Torchlight.  Breaks down complex tasks into executable steps, Detect if a task likely needs planning., Create a structured plan for the task., Plan for creation/build/implementation tasks. (+6 more)

### Community 24 - "ContextDashboard"
Cohesion: 0.05
Nodes (23): Console, _ActionContext, ActionEntry, ActionTracker, ContextDashboard, Panel, Print sub-agent task progress to the console., Return a new ActionTracker bound to this dashboard's console. (+15 more)

### Community 25 - "DebateVerifier"
Cohesion: 0.11
Nodes (19): Debate & Self-Critique Verification module for Torchlight., System and user prompt templates for LLM debate & self-critique verification., CritiqueResult, DebateVerifier, DebateVerifier implementation: orchestrates adversarial critique and refinement, Full debate flow: evaluate should_debate, execute critique, and refine if flaws, Helper to extract JSON payload from LLM response., Structured result of an adversarial critique step. (+11 more)

### Community 26 - "config.py"
Cohesion: 0.07
Nodes (41): index_directory(), IndexVisitor, init_db(), Initialize the Kuzu graph database with the AST schema and vector embeddings., _detect_apple_silicon_ram(), _detect_chip(), fetch_provider_models(), is_port_in_use() (+33 more)

### Community 27 - "cli/main.py"
Cohesion: 0.05
Nodes (34): command, verify_cli_prompt(), _beam_budget(), chat(), compress_file(), count_tokens(), Panel, Compress a file using verbatim compaction. (+26 more)

### Community 28 - "Learnings in Building Local SLM Coding Agents"
Cohesion: 0.06
Nodes (30): 24-Hour Continuous Autonomous Execution & Micro-Epoch Context Flushing, 7B Model EDIT_FILE Failure Modes, Active File Pinning for Context Preservation, Aider-Style Search/Replace Diff Blocks vs JSON `old_text`, AST Graph Engine: Context Overflow & Performance Audit, Consume-on-Read Pattern for Automated Feedback Context, Context Loss & Memory Compression, Context Recovery via Dynamic JIT File Pinning Budget Scaling (+22 more)

### Community 29 - "LLMClient"
Cohesion: 0.12
Nodes (18): LLMClient, Protocol, Abstract LLM client interface and shared inference parameters.  All LLM backends, Protocol that all LLM backends must implement.      Both sync and async methods, Check if the backend is reachable., List available models., Simple query interface (for backward compatibility)., create_client() (+10 more)

### Community 30 - "2026-07-24"
Cohesion: 0.06
Nodes (30): 2026-07-23, 2026-07-24, 2026-07-26, 2026-07-27, 2026-07-28, 24-Hour Continuous Autonomous Goal Harness (`AutonomousHarness`), Active File Pinning (Context Management Fix), Automatic Project & Persistent Memory File Initialization (+22 more)

### Community 31 - "rlm_engine_optimized.py"
Cohesion: 0.20
Nodes (8): MemoryConfig, test_tiered_memory_pinned_files_without_system_message(), test_tiered_memory_compress_recent_summarizer(), _clean_and_parse_json(), Parse the LLM response for action tags.         Returns: (action, thinking, cont, SolveResult, Step, TokenCounter

### Community 32 - "get_tool_registry"
Cohesion: 0.11
Nodes (23): Tests for SEARCH_AST tool implementation and Kuzu connection handling., test_search_ast_impl_fallback(), test_search_ast_schema_validation(), test_get_tool_registry(), test_get_openai_tools_schema(), test_validate_tool_call_alias(), test_validate_tool_call_missing_required(), test_validate_tool_call_unknown_tool() (+15 more)

### Community 33 - "context_manager/compression/summarizer.py"
Cohesion: 0.15
Nodes (17): ConversationSummarizer, DevSessionSummarizer, _extract_code_signatures(), _extract_errors(), _extract_failing_tests(), _extract_file_paths(), _format_messages_for_summary(), IncrementalSummarizer (+9 more)

### Community 34 - "MemoryConfig"
Cohesion: 0.13
Nodes (23): _build_excerpt(), LLM-powered SessionState extractor.  Replaces the regex-based _merge_summary_int, Build a compact conversation view for the extraction prompt., MemoryConfig, Create a MemoryConfig automatically tuned for the given context window size and, ContentChunk, ContentType, ContextSnapshot (+15 more)

### Community 35 - "SelectiveCompressor"
Cohesion: 0.14
Nodes (12): Pattern, FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent., FIX 2: token-aware truncation instead of character slicing., Legacy heuristic — only used when no tokenizer is injected., Determine compression level based on turn position from the end., FIX 2: Remove whitespace/noise then TOKEN-TRUNCATE to compact_budget.          T, Compress a list of message dicts with progressive levels.          Args:, Build a compressed context string within token budget.          Uses the real to (+4 more)

### Community 36 - "VerbatimCompactor"
Cohesion: 0.18
Nodes (8): CompressionConfig, VerbatimCompactor — compress text while preserving code structure., Compress text while preserving the content that matters most for dev sessions., VerbatimCompactor, test_compactor_compression(), test_compactor_empty_lines(), test_compactor_no_compress_short(), test_compactor_preserves_code()

### Community 37 - "on"
Cohesion: 0.21
Nodes (5): DirectorySelected, on, Pressed, FolderPickerModal, Modal dialog for interactive visual folder selection across the entire computer.

### Community 39 - "ProjectGraph"
Cohesion: 0.16
Nodes (11): Any, ProjectGraph, Path, Stores nodes (files, classes, functions) and edges (contains, calls, imports)., Scan project files and construct the AST graph., Save graph data to JSON and markdown report., Load graph from JSON file if available., Search nodes matching search_term. (+3 more)

### Community 40 - "ExecutionFeedbackLoop"
Cohesion: 0.16
Nodes (8): ExecutionFeedbackLoop, Path, Detect and run the project's test suite or web inspector., Build feedback context string for the LLM., Auto-run tests and web outcome inspection after code changes and inject feedback, Called after a tool is executed. Returns test results if tests were run., TestResult, TestRunResult

### Community 41 - "ProjectMemory"
Cohesion: 0.26
Nodes (3): ProjectMemory, Add a fact (and optional embedding) to project memory.          Signature accept, Merge current session's key findings into long-term project memory.

### Community 42 - "TDDSkill"
Cohesion: 0.18
Nodes (6): Any, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement, # TODO: Implement based on the requirement, TDDSkill, TDDStep

### Community 43 - "LLMStateExtractor"
Cohesion: 0.15
Nodes (8): LLMStateExtractor, _merge_into_state(), _parse_json_response(), Robustly extract a JSON object from the model's response.      Local models some, Merge the extracted JSON fields into the existing SessionState.      Strategy: L, Uses the local LLM to extract structured SessionState fields from a     conversa, Run LLM extraction and merge findings into *state* in-place.          Returns Tr, Return a copy of the call/hit/miss/error counters.

### Community 44 - "UnifiedSkillRegistry"
Cohesion: 0.17
Nodes (10): Run an async coroutine safely regardless of whether an event loop is already run, _run_async(), Any, Robustly parses tool calls from text.         Supports:           1. JSON format, A single registry for ALL tools and skills.     Bridges the gap between core too, Synchronous wrapper for execute_skill., Unified execution bridge.         Routes to core tools or external skills as app, Condensed tool documentation injected into the system prompt.                  U (+2 more)

### Community 45 - "CloudClient"
Cohesion: 0.18
Nodes (5): CloudClient, Sanitize message roles. Convert system role to user role for models (e.g. Gemma, Async streaming implementation required by LLMClient protocol., Return the ids of models the provider currently reports as available.         Us, _sanitize_messages_for_cloud()

### Community 46 - "SkillResult"
Cohesion: 0.15
Nodes (10): MyCustomSkill, Any, A template for creating your own custom tools for the agent.     Place your logi, Any, ReproSkill, SkillResult, Test-Driven Development (TDD) Skill for Torchlight.  Implements a test-first wor, # TODO: Write assertion based on requirement (+2 more)

### Community 47 - "test_autonomous_harness.py"
Cohesion: 0.33
Nodes (11): HarnessConfig, create_mock_feedback_loop(), ExecutionFeedbackLoop, Path, Unit tests for AutonomousHarness module., test_auto_git_init_and_clean_commit(), test_context_flushing_during_micro_epoch(), test_daemon_loop_completion() (+3 more)

### Community 48 - "test_optimizations.py"
Cohesion: 0.24
Nodes (9): test_write_file_impl(), test_write_file_impl_missing_path(), Tests for performance and accuracy optimizations in Torchlight., test_batch_tool_execution(), test_inline_syntax_guardrail(), _check_syntax(), Perform fast inline syntax validation for edited/written files., WRITE_FILE — create or overwrite a file. (+1 more)

### Community 49 - "tool_read_file"
Cohesion: 0.16
Nodes (16): _extract_symbols(), Return (MAX_LINES, MAX_CHARS) for the current context window., Return [(lineno_1based, kind, name), ...] sorted by line number., Compact symbol map prepended to READ_FILE output., READ_FILE — read a file with optional line-range or symbol syntax.      Formats:, READ_SYMBOLS — show the structure of a file without loading its content.      Re, _read_budget(), _symbol_map() (+8 more)

### Community 50 - "VerbatimCompactor"
Cohesion: 0.14
Nodes (6): CompressionConfig, Compress text while preserving the content that matters most for dev sessions., Keep the MOST RECENT errors, not the first ones.          For dev sessions, the, Compress text to fit a specific token budget while preserving Head/Tail., Compress a fenced code block intelligently.          Strategy (dev-aware):, VerbatimCompactor

### Community 51 - "core/memory/__init__.py"
Cohesion: 0.19
Nodes (12): CompressionLevel, Enum, Selective Memory Compression — Progressive context reduction for local LLMs.  4-, get_token_counter(), Token counting for Torchlight.  Uses tiktoken when available, falls back to a wo, TokenCounter, test_get_token_counter_caching(), test_get_token_counter_different_models() (+4 more)

### Community 52 - "RLMEngineOptimized"
Cohesion: 0.15
Nodes (9): test_rlm_engine_debate_verifier_error_resilience(), test_rlm_engine_optimized_code_execution(), test_rlm_engine_optimized_debate_verifier_initialization(), test_rlm_engine_optimized_none_tool_name(), Switch the active workspace, keeping the sandbox's AST-graph         lookups (ge, Notify listeners of real-time background status and action telemetry., Re-append closing tags that were consumed as stop tokens by llama-server., Stream LLM response token-by-token cleanly without thread deadlocks. (+1 more)

### Community 53 - "LlamaCppClient"
Cohesion: 0.20
Nodes (5): LlamaCppClient, Ensure strict role alternation (user, assistant...) and merge consecutive same-r, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol., _sanitize_messages()

### Community 54 - "core/tests/test_models.py"
Cohesion: 0.18
Nodes (15): ContentChunk, ContextSnapshot, MemoryNeedle, MemoryObject, Snapshot of current memory state for display., SessionState, WorkingSetSnapshot, test_content_chunk() (+7 more)

### Community 55 - "Static"
Cohesion: 0.20
Nodes (4): ComposeResult, AgentStatusModal, Modal dialog for complete visibility into background agent actions & status tele, Static

### Community 56 - "ProjectMemory"
Cohesion: 0.23
Nodes (6): ProjectMemory, SessionState, SessionPersistence, test_corrupt_memory_file_self_heals(), test_manual_deletion_context_memory_self_heals(), test_project_memory_auto_init()

### Community 57 - "test_diff_edit.py"
Cohesion: 0.32
Nodes (6): Tests for Aider-style Search/Replace block editing (Approach B) and dynamic JIT, test_parse_diff_block_invalid(), test_parse_diff_block_valid(), test_pin_file_truncation_to_budget(), _parse_diff_block(), Parse Aider-style <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE block into (old

### Community 58 - "test_phase_detection.py"
Cohesion: 0.21
Nodes (13): _make_session(), Create a StreamingChatSession with mocked heavy dependencies., Troubleshoot wins over code when both signals are present., Code phase should yield lower temperature than chat phase., Chat phase should have higher temperature than code phase., test_detect_chat_phase(), test_detect_code_phase(), test_detect_phase_empty_input() (+5 more)

### Community 59 - "Embedder"
Cohesion: 0.21
Nodes (9): build_embedder(), Embedder, HybridEmbedder, KeywordEmbedder, Embedding support for Torchlight.  Provides hybrid embedding (LLM-based + keywor, Base embedder interface., Simple keyword-based embedding fallback., Hybrid embedder: uses LLM embeddings when available, falls back to keywords. (+1 more)

### Community 60 - "discovery.py"
Cohesion: 0.18
Nodes (14): discover_skills(), execute_skill_by_name(), get_compact_skill_list(), get_skill_executor(), _load_skill_index(), Any, Skill Discovery - On-demand skill retrieval to minimize context.  Instead of inj, Discover available skills based on query or category.          This is called ON (+6 more)

### Community 61 - "classify_command"
Cohesion: 0.26
Nodes (11): test_classify_confirm_commands(), test_classify_destructive_commands(), test_classify_empty_command(), test_classify_safe_commands(), test_classify_unknown_defaults_to_confirm(), test_classify_whitespace_handling(), classify_command(), classify_tool() (+3 more)

### Community 62 - "OllamaClient"
Cohesion: 0.24
Nodes (3): OllamaClient, Async implementation of chat protocol method required by LLMClient / DebateVerif, Async streaming implementation required by LLMClient protocol.

### Community 64 - "main_optimized.py"
Cohesion: 0.24
Nodes (12): amain(), approval_prompt(), create_client(), display_step(), get_depth_style(), main(), print_banner(), Step (+4 more)

### Community 65 - "CopySelectionModal"
Cohesion: 0.25
Nodes (4): copy_to_clipboard(), CopySelectionModal, Modal dialog to select and copy specific messages, code blocks, or text turns., Copy text to system clipboard across macOS, Linux, and Windows.

### Community 66 - "PyASTVisitor"
Cohesion: 0.14
Nodes (8): AsyncFunctionDef, Call, ClassDef, PyASTVisitor, AST visitor to extract classes, functions, calls, and imports from Python code., FunctionDef, Import, ImportFrom

### Community 67 - "🦸‍♂️ Torchlight's Superpowers!"
Cohesion: 0.18
Nodes (10): 📊 Summary Table of Superpowers, 🗺️ Superpower 1: The Magic Code Map (Native AST Graph Engine), 🔫 Superpower 2: The Shrink Ray (8GB Memory Tricks), 🧠 Superpower 3: Tiny, Ultra-Smart Brains (Small Models), 🎭 Superpower 4: Changing Moods (Phase-Based Inference), 🔄 Superpower 5: The "Try Again" Loop (RLM), 🕵️‍♂️ Superpower 6: The Invisible Devil's Advocate (Out-of-Band Self-Critique), 🏃‍♂️ Superpower 7: The 24-Hour Non-Stop Marathon Engine (Autonomous Harness) (+2 more)

### Community 68 - "Architecture"
Cohesion: 0.20
Nodes (9): Agentic Loop, Architecture, Commands, Context Budget (4k model), Development, Key Design Decisions, Memory Files, Module Structure (+1 more)

### Community 69 - "RLMEngine"
Cohesion: 0.20
Nodes (12): test_rlm_engine_solve_method(), create_client(), display_step(), get_depth_style(), main(), print_banner(), print_help(), Step (+4 more)

### Community 70 - "get_project_graph"
Cohesion: 0.27
Nodes (8): get_project_graph(), Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping., Get or create the ProjectGraph instance for a given root directory., Path, Unit tests for Torchlight Native AST Graph Engine., test_project_graph_build(), test_project_graph_queries(), test_tool_search_ast_integration()

### Community 71 - "prompts_minimal.py"
Cohesion: 0.29
Nodes (7): build_efficient_prompt(), get_compact_tool_list(), get_system_prompt(), Minimal Prompt Strategy for Torchlight.  Instead of loading all skills into cont, Build the most token-efficient prompt for the given context., Select appropriate prompt based on context window size., Get the most compact tool list possible.

### Community 76 - "autonomous_harness.py"
Cohesion: 0.21
Nodes (9): Autonomous Harness Driver for Torchlight.  Enables continuous, multi-epoch execu, TaskStatus, Execution Feedback Loop for Torchlight.  Closes the loop between code changes an, TestResultStatus, main(), CLI entry point to launch the Torchlight 24-Hour Autonomous Harness., Tiered Memory Manager for Torchlight.  L0-L3 memory hierarchy with progressive c, Enum (+1 more)

### Community 80 - "build_embedder"
Cohesion: 0.17
Nodes (10): build_embedder(), Embedder, FallbackEmbedder, HashEmbedder, _normalize(), ProviderEmbedder, any, Protocol (+2 more)

### Community 81 - "start_optimized_local.sh"
Cohesion: 0.53
Nodes (4): log_error(), log_info(), log_warn(), start_optimized_local.sh script

### Community 83 - "setup_optimized.sh"
Cohesion: 0.60
Nodes (3): info(), ok(), setup_optimized.sh script

### Community 84 - "unified.py"
Cohesion: 0.16
Nodes (5): CoreTool, CoreToolRegistry, tool_web_fetch(), test_core_registry_get_unknown(), test_core_registry_register()

### Community 104 - "tui_app.py"
Cohesion: 0.17
Nodes (10): create_client(), load_last_state(), main(), ModelPickerModal, _provider_runtime_info(), Torchlight Agent — Codex / Tiny-Brain 2 Style IDE TUI (Textual) Full-featured ID, Return (port, externally_managed) for a given provider key.      externally_mana, Modal dialog to visually pick models and engine providers. (+2 more)

### Community 111 - "._run_agent"
Cohesion: 0.17
Nodes (5): Mount a widget defensively.          A widget reference captured before an `awai, Build the AST knowledge graph for the current project_root in a         backgrou, Step, Submitted, work

### Community 113 - "test_tools_core.py"
Cohesion: 0.21
Nodes (12): classify_command(), Tell the tool layer what context window the current model has., set_ctx_window(), test_classify_destructive_command(), test_classify_empty_command(), test_classify_install_command(), test_classify_safe_command(), test_classify_unknown_command() (+4 more)

### Community 114 - "SymbolIndex"
Cohesion: 0.15
Nodes (9): Flashlight Beam — query-to-code relevance scorer.  Scoring strategy (additive):, FileEntry, Path, Flashlight Indexer — scans the project and builds a searchable symbol index., SymbolIndex, test_file_entry(), test_symbol_index_build(), test_symbol_index_summary() (+1 more)

### Community 115 - "context_manager/memory/persistence.py"
Cohesion: 0.16
Nodes (12): MemoryNeedle, MemoryObject, ensure_git_repository(), ensure_project_initialized(), init_new_project(), Path, SessionState, SessionPersistence (+4 more)

### Community 116 - "test_autonomous_harness_pipeline.py"
Cohesion: 0.42
Nodes (7): create_mock_feedback_loop(), ExecutionFeedbackLoop, Path, Unit tests for Inter-Task Context Pipeline, Dependencies, and File Collision Gua, test_inter_task_output_summary_injection(), test_target_file_collision_detection(), test_task_dependencies_and_execution_ordering()

### Community 119 - "Indexed Nodes"
Cohesion: 0.50
Nodes (3): Indexed Nodes, Key Classes & Functions, Torchlight Knowledge Graph Report

## Knowledge Gaps
- **82 isolated node(s):** `Commands`, `Module Structure`, `Context Budget (4k model)`, `Agentic Loop`, `Key Design Decisions` (+77 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SkillResult` connect `SkillResult` to `ProjectSnapshot`, `BaseSkill`, `TDDSkill`, `UnifiedSkillRegistry`, `MarkdownDocumentSkill`, `unified.py`, `PlanningSkill`, `discovery.py`, `TDDSkill`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `ConnectionError` connect `RecoveryEngine` to `LlamaCppClient`, `CloudClient`, `OllamaClient`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `BaseSkill` connect `BaseSkill` to `ProjectSnapshot`, `TDDSkill`, `UnifiedSkillRegistry`, `MarkdownDocumentSkill`, `SkillResult`, `unified.py`, `PlanningSkill`, `TDDSkill`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `TieredMemory` (e.g. with `LLMStateExtractor` and `ContextSnapshot`) actually correct?**
  _`TieredMemory` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `TieredMemory` (e.g. with `AutonomousHarness` and `GoalSpec`) actually correct?**
  _`TieredMemory` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ProjectSnapshot` (e.g. with `BaseSkill` and `SkillResult`) actually correct?**
  _`ProjectSnapshot` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `SkillResult` (e.g. with `AndroidTroubleshootSkill` and `ProjectSnapshot`) actually correct?**
  _`SkillResult` has 13 INFERRED edges - model-reasoned connections that need verification._