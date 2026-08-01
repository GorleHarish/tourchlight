# Torchlight Agent & Loop Bug Registry (`bug.md`)

This document records all discovered loop bugs, agent trajectory issues, edge cases, and structural flaws found via knowledge graph traversal and code audit, along with their root causes, locations, severity, and resolution status.

---

## Summary of Tracked Bugs

| Bug ID | Title | Severity | Location | Status |
|--------|-------|----------|----------|--------|
| **BUG-01** | `_total_llm_calls` Counter Accumulation Across Sessions | 🔴 Critical | `rlm_optimized/rlm_engine_optimized.py` | ✅ Fixed |
| **BUG-02** | Verification Gate Premature Answer Bypass via Rejection State | 🔴 Critical | `rlm_optimized/rlm_engine_optimized.py` | ✅ Fixed |
| **BUG-03** | Autonomous Harness Daemon Infinite Loop on Exception | 🔴 Critical | `core/execution/autonomous_harness.py` | ✅ Fixed |
| **BUG-04** | Consecutive Code Error Loop Unbounded Retries | 🔴 Critical | `rlm_optimized/rlm_engine_optimized.py` | ✅ Fixed |
| **BUG-05** | Unimported `Path` Silently Disables Feedback Loop | 🟠 High | `rlm_optimized/rlm_engine_optimized.py` | ✅ Fixed |
| **BUG-06** | Stale Verification Gate Gatekeeping on Test Failure Reset | 🟠 High | `core/execution/feedback_loop.py` | ✅ Fixed |
| **BUG-07** | Read-Only Tool Interleaving Counter Laundering | 🟠 High | `rlm_optimized/rlm_engine_optimized.py` | ✅ Fixed |
| **BUG-08** | LLM Step Failure Overwritten by Passing Pre-Existing Tests | 🟠 High | `core/execution/autonomous_harness.py` | ✅ Fixed |
| **BUG-09** | `consecutive_thinking` Loop Reset via Rejected Tags | 🟡 Medium | `rlm_optimized/rlm_engine_optimized.py` | ✅ Fixed |
| **BUG-10** | Missing Total Streaming LLM Response Timeout | 🟡 Medium | `rlm_optimized/rlm_engine_optimized.py` | ✅ Fixed |
| **BUG-11** | Unscoped Project-Wide `git clean -fd` in Micro-Epoch Revert | 🟡 Medium | `core/execution/autonomous_harness.py` | ✅ Fixed |
| **BUG-12** | `RecoveryEngine` Disconnect from Agentic Loop | 🟡 Medium | `core/errors/recovery.py` | ✅ Fixed |
| **BUG-13** | Misrouted Internal AST Function Invocations via `RUN_COMMAND` | 🟠 High | `core/tools/implementations.py` | ✅ Fixed |
| **BUG-14** | Duplicate Method Definitions Disabling TUI Stop Button | 🔴 Critical | `rlm_optimized/tui_app.py` | ✅ Fixed |
| **BUG-15** | Missing `#status-right` Widget in Status Bar Composition | 🟠 High | `rlm_optimized/tui_app.py` | ✅ Fixed |
| **BUG-16** | Unopened `CopySelectionModal` Screen in `action_copy_selection()` | 🟡 Medium | `rlm_optimized/tui_app.py` | ✅ Fixed |
| **BUG-17** | Erroneous File Tree Reset in `/copylast` Slash Command | 🟡 Medium | `rlm_optimized/tui_app.py` | ✅ Fixed |
| **BUG-18** | Unescaped Rich Markup Tags in `_poll_server_launch()` | 🟡 Medium | `rlm_optimized/tui_app.py` | ✅ Fixed |
| **BUG-19** | Non-Thread-Safe Widget Mounts in Background AST Indexer | 🟡 Medium | `rlm_optimized/tui_app.py` | ✅ Fixed |

---

## Detailed Bug Reports & Resolutions

### BUG-01: `_total_llm_calls` Counter Accumulation Across Sessions
- **Severity**: 🔴 Critical
- **Location**: [rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py#L274)
- **Root Cause**: `self._total_llm_calls` was initialized once during `RLMEngineOptimized.__init__` but never reset at the start of `solve_async()`. Multi-turn CLI and TUI sessions accumulated count values across user queries, leading to incorrect telemetry reporting and inflated token estimations.
- **Fix**: Reset `self._total_llm_calls = 0` at the entry of `solve_async()`.

### BUG-02: Verification Gate Premature Answer Bypass via Rejection State
- **Severity**: 🔴 Critical
- **Location**: [rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py#L275)
- **Root Cause**: `_final_answer_rejections` instance variable was not reset on new `solve_async()` calls. If a previous prompt hit 2 rejections, subsequent prompts started with `_final_answer_rejections >= 2`, permanently bypassing the Verification Gate for failing tests and open sub-tasks.
- **Fix**: Added explicit reset `self._final_answer_rejections = 0` at entry of `solve_async()`.

### BUG-03: Autonomous Harness Daemon Infinite Loop on Exception
- **Severity**: 🔴 Critical
- **Location**: [autonomous_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/autonomous_harness.py#L427-L431)
- **Root Cause**: When `run_micro_epoch()` threw an unhandled exception before completing attempt updates, `run_daemon()` logged the exception but left `task.status = TaskStatus.IN_PROGRESS`. On the next loop iteration, `_get_runnable_pending_tasks()` repeatedly selected the same stuck task, causing an infinite loop.
- **Fix**: Updated exception handler in `run_daemon()` to reset `task.status = TaskStatus.PENDING` when attempts remain below `max_attempts`.

### BUG-04: Consecutive Code Error Loop Unbounded Retries
- **Severity**: 🔴 Critical
- **Location**: [rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py#L670-L682)
- **Root Cause**: When REPL code execution failed 3 times consecutively, the engine appended a warning message to the prompt but allowed the LLM to continue retrying failing Python code up to `MAX_ITERATIONS_PER_LEVEL` (15–30 turns).
- **Fix**: Added hard force-break on `consecutive_code_errors >= 5`, yielding a `<FINAL_ANSWER>` with error context to prevent trajectory burn.

### BUG-05: Unimported `Path` Silently Disables Feedback Loop
- **Severity**: 🟠 High
- **Location**: [rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py#L5)
- **Root Cause**: `Path(self.project_root)` was called inside `RLMEngineOptimized.__init__` without importing `Path` at the module top level. The surrounding `try/except Exception` caught the resulting `NameError` and set `self.feedback_loop = None`, silently disabling post-edit test execution.
- **Fix**: Added `from pathlib import Path` to top-level imports in `rlm_engine_optimized.py`.

### BUG-06: Stale Verification Gate Gatekeeping on Test Failure Reset
- **Severity**: 🟠 High
- **Location**: [feedback_loop.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/feedback_loop.py#L130-L319)
- **Root Cause**: `build_feedback_context()` cleared `self._last_test_result = None` after formatting the feedback message. When the LLM attempted `<FINAL_ANSWER>` on the next turn, the Verification Gate checked `_last_test_result` (now `None`) and allowed the premature answer despite failing tests.
- **Fix**: Added `has_failing_tests` property and `_test_result_reported` flag. `build_feedback_context()` marks feedback as reported without clearing `_last_test_result`, keeping test failure state intact for gate evaluation until a new test run completes.

### BUG-07: Read-Only Tool Interleaving Counter Laundering
- **Severity**: 🟠 High
- **Location**: [rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py#L463)
- **Root Cause**: Exempting read-only tools (`READ_FILE`, `GREP`) from duplicate tool detection allowed interleaving read-only tools between identical mutating calls, resetting `_last_tool_key` and laundering duplicate counts.
- **Fix**: Preserved the last mutating tool call key across read-only tool executions so duplicate write patterns are tracked accurately.

### BUG-08: LLM Step Failure Overwritten by Passing Pre-Existing Tests
- **Severity**: 🟠 High
- **Location**: [autonomous_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/autonomous_harness.py#L342)
- **Root Cause**: In `run_micro_epoch()`, if `llm_engine_step_fn` returned `False` (indicating LLM step failure), subsequent execution of `feedback_loop._run_tests()` unconditionally set `success = True` if test suite passed.
- **Fix**: Changed assignment to `success = success and True` so passing tests cannot override an LLM step failure.

### BUG-09: `consecutive_thinking` Loop Reset via Rejected Tags
- **Severity**: 🟡 Medium
- **Location**: [rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py#L348)
- **Root Cause**: `consecutive_thinking` counter reset on any `action != "thinking"`. When a premature final answer was rejected, `step.action` was set to `"rejected_final_answer"`, incorrectly resetting the reasoning loop counter and letting the model evade loop limits.
- **Fix**: Updated condition to `if action not in ("thinking", "rejected_final_answer"):`.

### BUG-10: Missing Total Streaming LLM Response Timeout
- **Severity**: 🟡 Medium
- **Location**: [rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py#L232)
- **Root Cause**: `_stream_llm` checked timeout per chunk (`timeout=60.0`), allowing slow LLMs emitting one token per minute to run indefinitely without hitting a response boundary timeout.
- **Fix**: Added stream health monitoring and proper chunk queue boundary tracking.

### BUG-11: Unscoped Project-Wide `git clean -fd` in Micro-Epoch Revert
- **Severity**: 🟡 Medium
- **Location**: [autonomous_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/autonomous_harness.py#L520-L528)
- **Root Cause**: `_git_revert()` executed `git checkout -- .` and `git clean -fd` across the entire workspace, deleting untracked user files and artifacts unrelated to the failed task.
- **Fix**: Scoped `_git_revert()` to target specific task `target_files` when specified.

### BUG-12: `RecoveryEngine` Disconnect from Agentic Loop
- **Severity**: 🟡 Medium
- **Location**: [recovery.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/errors/recovery.py#L138)
- **Root Cause**: The structured `RecoveryEngine` escalation ladder was implemented in `core/errors/recovery.py` but lacked direct hooks inside `rlm_engine_optimized.py`, relying on ad-hoc counters.
- **Fix**: Connected `get_recovery_hint` and recovery error mapping inside `build_feedback_context` and exception handling.

### BUG-13: Misrouted Internal AST Function Invocations via `RUN_COMMAND`
- **Severity**: 🟠 High
- **Location**: [implementations.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/implementations.py#L1460)
- **Root Cause**: When local or smaller LLMs attempted to inspect project structure using internal AST helper functions (e.g. `get_project_structure()`), prompt confusion led models to issue `<TOOL name="RUN_COMMAND">{"cmd": "get_project_structure()*"}</TOOL>`. `RUN_COMMAND` passed `cmd` directly to `/bin/sh -c`, resulting in shell syntax errors (`Exit 2: syntax error: unexpected end of file`).
- **Fix**: Added auto-interception in `tool_run_command_impl` to redirect internal AST function calls (`get_project_structure`, `semantic_search`, `SEARCH_AST`) to `SEARCH_AST` execution. Added `"get_project_structure"` action alias to `tool_search_ast_impl` and updated system prompts in `prompts.py` to clarify tool vs CODE boundaries.

---

## Verification
All fixes were verified via pytest:
```bash
pytest core/tests/ context-manager-cli/tests/
```
The codebase knowledge graph was updated via `graphify update .`.
