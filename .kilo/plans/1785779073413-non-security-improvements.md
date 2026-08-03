# Plan: Non-Security Improvements

**Scope:** All improvement areas except security hardening (SSRF, sandbox escape, shell injection, git config, etc.).

## Decisions

- **Frontend consolidation: Option B (Aggressive).** Delete duplicate `flashlight/` and `compression/` copies from `context-manager-cli/src/`, replace with re-export shims from `core/`. Consolidate `rlm_engine.py` into `rlm_engine_optimized.py` via a thin delegation wrapper.
- **Legacy engine: keep `rlm_engine.py` as a thin wrapper.** It stays as a backward-compatible shim that delegates to `RLMEngineOptimized`. No deprecation warning needed since the wrapper is only ~20 lines.
- **Security: out of scope.** Do not address sandbox escape, SSRF, shell injection, or git config issues in this plan.

## Task 1: Frontend Consolidation

1.1 In `context-manager-cli/src/context_manager/flashlight/beam.py`: replace contents with re-exports from `core.flashlight.beam`.
1.2 In `context-manager-cli/src/context_manager/flashlight/indexer.py`: replace contents with re-exports from `core.flashlight.indexer`.
1.3 In `context-manager-cli/src/context_manager/compression/compactor.py`: replace contents with re-exports from `core.compression.compactor`.
1.4 Verify `context-manager-cli/src/context_manager/memory/manager.py` already re-exports from `core/`. Align any drift.
1.5 In `rlm_optimized/rlm_engine.py`: replace the duplicated parsing/streaming logic with a thin wrapper:
   - Keep `RLMEngine` class and its legacy `solve()` method.
   - Implement `solve()` by delegating to `RLMEngineOptimized.solve_async()` via `asyncio.run()`.
   - Delete all duplicated `_parse_response`, `_stream_llm`, `_repair_stop_tokens`, etc.
1.6 Update imports in `rlm_optimized/main.py`, `rlm_optimized/main_optimized.py`, and test files that reference `rlm_engine_optimized` internals (e.g., `_clean_and_parse_json`, `Step`). Move shared types (`Step`, `SolveResult`) to `rlm_optimized/types.py` if both engines need them.

## Task 2: Split `implementations.py` into Sub-Modules

2.1 Create `core/tools/impl_read.py` with READ_FILE, READ_SYMBOLS, LIST_DIR, GREP, SEARCH_AST.
2.2 Create `core/tools/impl_write.py` with WRITE_FILE, EDIT_FILE.
2.3 Create `core/tools/impl_web.py` with WEB_FETCH, WEB_SEARCH, DOC_SEARCH, WEB_VERIFY, INSPECT_WEB.
2.4 Create `core/tools/impl_vcs.py` with GIT.
2.5 Create `core/tools/impl_exec.py` with RUN_COMMAND, FORMAT_CODE.
2.6 Update `core/tools/implementations.py` to import and re-export from the sub-modules. Remove all function bodies.
2.7 Update `core/tools/registry.py` to lazy-load implementations by category on first access.

## Task 3: Cache `SymbolIndex` Across Micro-Epochs

3.1 Add `self._index: Optional[SymbolIndex] = None` and `self._index_mtime: float = 0.0` to `AutonomousHarness.__init__`.
3.2 In `run_micro_epoch`, before building the index, check if any `task.target_files` have changed or if `self._index_mtime` is stale. Only rebuild when needed.
3.3 Reuse the cached index for both the pre-load phase (around line 342) and post-success enrichment phase (around line 430).

## Task 4: Extract Tool Execution Pipeline

4.1 Create `core/tools/pipeline.py` with `ToolExecutionPipeline` class:
   - `execute(name, params, project_root, risk, approval_fn, registry, memory, feedback_loop)` 
   - Encapsulates: risk check → approval → registry.execute → file pin refresh → feedback loop → memory injection.
4.2 Refactor `rlm_engine_optimized.py` lines 760–857 to call `pipeline.execute()` instead of inline logic.
4.3 Refactor `cli/main.py` lines 353–498 to call `pipeline.execute()` instead of inline logic.
4.4 Remove the duplicated pinning/feedback blocks from both frontends.

## Task 5: Fix Error Handling Gaps

5.1 In `core/execution/feedback_loop.py`: replace `except Exception: pass` at lines 192, 198, 244 with `logger.warning("... failed: %s", e)`.
5.2 In `core/execution/autonomous_harness.py`: change `logger.debug` to `logger.warning` for AST indexing failures (lines 362, 453). When extraction fails, inject `[AST indexing unavailable — use SEARCH_AST for symbol discovery]` into the prompt.
5.3 In `core/tools/registry.py`: ensure `ToolResult.success` is the authoritative signal. Update tool implementations to return `ToolResult(success=bool, output=str)` rather than relying on string-prefix heuristics.

## Task 6: Add Missing Tests

6.1 Add `core/tests/test_verification_gate.py`: mock LLM returns `<FINAL_ANSWER>` while `feedback_loop.has_failing_tests` is True. Assert the engine injects the rejection message and continues.
6.2 Add `core/tests/test_recovery_escalation.py`: feed 5 identical `ToolError`s to `RecoveryEngine.handle()`. Assert the action sequence: RETRY, RETRY, RETRY, COMPRESS_AND_RETRY, SKIP.
6.3 Add `core/tests/test_speculative_executor_race.py`: simulate a speculative future in progress, call `_run_tests()`, assert it waits for the future rather than spawning a duplicate.
6.4 Add `core/tests/test_parse_response_robustness.py`: parametrized cases for unclosed `<tool_call>`, nested braces in strings, mixed-case tags, garbage output.
6.5 Add `core/tests/test_context_budget_extreme.py`: parametrized cases for `used_tokens = 0.9 * max_tokens`, `used_tokens > max_tokens`, and oversized pinned files.

## Task 7: Maintainability Fixes

7.1 In `rlm_optimized/config.py`: add `MAX_CONSECUTIVE_DUPLICATE_TOOL_CALLS = 3`, `MAX_CONSECUTIVE_CODE_ERRORS = 5`, `HARNESS_DEFAULT_TASK_MAX_ATTEMPTS = 3`.
7.2 In `core/tools/registry.py`: move `_CTX_WINDOW` and `_global_memory_mgr` from module-level globals into `ToolRegistry` instance attributes.
7.3 In `core/execution/feedback_loop.py`: register an `atexit` handler to shut down `_speculative_executor`.

## Validation

- Run `python -m pytest core/tests/ context-manager-cli/tests/ rlm_optimized/tests/` after each task group.
- After Task 1, verify `from context_manager.flashlight import Flashlight` still works from the CLI package.
- After Task 1, verify `from rlm_optimized.rlm_engine import RLMEngine` still works and produces the same results as `RLMEngineOptimized`.
- After Task 2, verify all 18 tools still resolve correctly from `core.tools.registry`.

## Out of Scope

- Security hardening (SSRF, sandbox escape, shell injection, git config mutation, subprocess cleanup).
- Grammar/spelling cleanup from the earlier plan.
