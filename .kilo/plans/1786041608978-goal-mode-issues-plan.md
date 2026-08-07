# Goal Mode Issues - Analysis & Fix Plan

## Issues Found

### 1. **ExecutionMode Enum Mismatch**
- **Location**: `core/memory/models.py:20-23` vs `rlm_optimized/rlm_engine_optimized.py:403-408`
- **Problem**: `ExecutionMode` has `UNIFIED`, `CHAT`, `GOAL` but `rlm_engine_optimized.py` only checks for `"chat"` and `"goal"` strings, defaults to `"code"` phase
- **Impact**: UNIFIED mode (default) falls through to "code" phase, not handled properly

### 2. **Phase Detection Not Integrated with Goal Mode**
- **Location**: `context-manager-cli/src/context_manager/cli/main.py:416-439` vs `rlm_optimized/rlm_engine_optimized.py`
- **Problem**: CLI has sophisticated `_detect_phase()` with auto-switching of inference params, but TUI engine uses static phase based on `execution_mode` only
- **Impact**: Goal Mode loses dynamic phase adaptation (plan → code → troubleshoot)

### 3. **Goal Spec Initialization Race Condition**
- **Location**: `rlm_optimized/tui_app.py:2737-2747` and `rlm_optimized/tui_app.py:3490-3497`
- **Problem**: `ensure_goal_spec_initialized()` called without error handling in two places; if it fails silently, user sees "Goal Mode" but no task files created
- **Impact**: False positive - user thinks Goal Mode is active but `.torchlight/goal_spec.json` and `tasks.md` don't exist

### 4. **Missing Verification Gate in CLI Goal Mode**
- **Location**: `context-manager-cli/src/context_manager/cli/main.py:1037-1047`
- **Problem**: CLI's `/tasks` command shows task progress but doesn't enforce Verification Gate (pending tasks block `<FINAL_ANSWER>`)
- **Impact**: Inconsistent behavior between CLI and TUI - TUI has gate (line 558-566), CLI doesn't

### 5. **AutonomousHarness Not Wired to LLM Engine in CLI**
- **Location**: `context-manager-cli/src/context_manager/cli/main.py:1013-1018`
- **Problem**: CLI creates `AutonomousHarness` but never passes `llm_engine_step_fn` - harness can't actually execute tasks
- **Impact**: Goal Mode in CLI is UI-only; tasks never get executed autonomously

### 6. **Inconsistent ExecutionMode Default**
- **Location**: `core/memory/models.py:126` default is `UNIFIED` but both frontends treat absence as CHAT
- **Impact**: Confusion about what "default" mode actually means

### 7. **Memory State Sync Issues**
- **Location**: `rlm_optimized/tui_app.py:2885-2892` syncs `execution_mode` from memory to engine at start, but not vice versa
- **Problem**: If engine changes mode, memory state not updated; if memory changes, engine not notified mid-session
- **Impact**: Mode drift between engine and memory state

---

## Fix Plan

### Phase 1: Core Model Alignment (High Priority)
1. **Align ExecutionMode handling in RLMEngineOptimized**
   - Update `solve_async()` to handle all three enum values: UNIFIED, CHAT, GOAL
   - Map UNIFIED → default to "code" phase but enable auto-detection like CLI

2. **Add Phase Auto-Detection to TUI Engine**
   - Port `_detect_phase()` and `_update_params()` logic from CLI to `rlm_engine_optimized.py`
   - Enable dynamic phase switching in Goal Mode (not just static "code")

### Phase 2: Goal Spec Robustness (High Priority)
3. **Make Goal Spec Initialization Explicit & Verified**
   - Return success/failure from `ensure_goal_spec_initialized()` calls
   - Show error notification if task files fail to create
   - Add validation that `.torchlight/goal_spec.json` and `tasks.md` exist before announcing Goal Mode

### Phase 3: Verification Gate Consistency (Medium Priority)
4. **Add Verification Gate to CLI**
   - In `_generate_response()` / `_generate_streaming_response()`, check for pending tasks in Goal Mode
   - Reject `<FINAL_ANSWER>` if tasks pending (mirror TUI logic at lines 558-566)

5. **Wire AutonomousHarness to LLM in CLI**
   - Pass a step function to `AutonomousHarness(llm_engine_step_fn=...)`
   - Enable actual autonomous task execution in CLI Goal Mode

### Phase 4: State Synchronization (Medium Priority)
6. **Bidirectional ExecutionMode Sync**
   - Add callback/notification when mode changes in either engine or memory
   - Ensure `memory.state.execution_mode` and `engine.execution_mode` always match

7. **Clarify Default Mode Semantics**
   - Decide: UNIFIED = "auto-detect phase" (like CLI) or UNIFIED = "chat"?
   - Update default in `SessionState` and both frontends consistently

---

## Validation Steps
- [ ] Run existing tests: `pytest core/tests/test_session_modes.py`
- [ ] Test CLI: `cd context-manager-cli && ./run.sh --mode goal` → verify task files created
- [ ] Test TUI: `/mode goal` → verify `.torchlight/goal_spec.json` and `tasks.md` created
- [ ] Test Verification Gate: create pending task, try to yield FINAL_ANSWER → should be rejected
- [ ] Test Phase Detection: in Goal Mode, input "let me plan" → phase should switch to "plan"
- [ ] Test Autonomous Execution: CLI Goal Mode with simple task → verify harness runs micro-epoch

---

## Open Questions
1. Should UNIFIED mode enable auto phase detection (like CLI) or remain static "code"?
2. Should Goal Mode default phase be "plan" (planning first) or "code"?
3. Does CLI need full AutonomousHarness daemon support or just single-task execution?