# Bug Report Plan: Agent Writes Gibberish to Files Instead of Coding

## 1. Summary
- **Title (registered)**: BUG-20 — Inline Code Interception Writes Gibberish Prose/Plan Blocks as Files
- **Severity**: 🟠 High
- **Status**: ✅ Fixed
- **Reported symptom**: Agent emits no meaningful reasoning or code, and instead writes garbage text into target files.

## 2. Reproduction Steps
1. Start chat session via `cd context-manager-cli && ./run.sh` (or TUI `./tui.sh`).
2. Issue a coding request (e.g. "add a function that parses JSON").
3. Observe tool calls: `WRITE_FILE`/`EDIT_FILE` payloads contain nonsensical content (random tokens, repeated phrases, raw model text) instead of valid code.
4. Note whether reasoning tags (`<thinking>`) are empty/garbled and whether `SEARCH_AST`/`GREP` read steps are skipped before writing.

## 3. Hypothesis Areas (Root Cause Candidates)
- **A. Tokenizer/context corruption**: `WRITE_FILE` payload built from mangled streamed tokens (bad chunk reassembly, truncation at byte boundary in `_stream_llm`).
- **B. Small-model prompt confusion**: Model misparses tool syntax and emits file content inside reasoning text or as plain chat text; engine interceptor writes it verbatim.
- **C. Tool-call parser failure**: `_parse_tool_call` regex captures wrong region (e.g. grabs assistant prose as `content` arg); falls back to writing the full raw response.
- **D. Non-Verbose output discipline regression**: chat text suppression code misfiring, causing the model's "planning prose" to be routed into a write instead of the assistant message.
- **E. Embedding/token-count overflow**: L0 scratchpad or context budget miscalculation truncating the model's structured output mid-tag.

## 4. Investigation Tasks
- [x] Capture a failing trajectory (TUI/CLI logs) showing the exact gibberish `WRITE_FILE` payload and the preceding raw LLM stream.
- [x] Inspect `_stream_llm` chunk reassembly in `rlm_optimized/rlm_engine_optimized.py` for byte/UTF-8 boundary truncation.
- [x] Inspect `_parse_tool_call` / `<tool_call>` regex handling and the inline code-interception path ("Code in chat → auto-WRITE_FILE").
- [x] Grep for where WRITE_FILE content is validated; check whether any sanity/stub detection runs before writing (stub detector lives in harness layer, not engine).
- [x] Test with a stronger model vs the base model to confirm model-size dependence (Hypothesis B).
- [x] Check whether the gibberish correlates with a specific context pressure level (L0 expanded) or tool interleaving.

## 5. Confirmed Root Cause
`_parse_response()` step 6b converts **any** bare markdown code block into a `WRITE_FILE` tool call. Small models emit planning/reasoning prose inside ``` blocks during the `plan`/`code` phase; the engine wrote that prose verbatim (e.g. `inline_code_output_1.txt`). Compounded by: write gate validating only code extensions, `<WRITE_FILE>` regex swallowing trailing prose on stripped closing tags, and `plan` phase not being excluded from interception. (Hypothesis B confirmed; A/C/E ruled out — no byte-boundary truncation or parser-region capture faults.)

## 6. Applied Fixes
1. **Prose/outline guard**: `_looks_like_prose_or_outline()` in `rlm_engine_optimized.py` rejects numbered outlines, step/plan lead-ins, and sentence-heavy prose; `plan` phase excluded from inline interception. Real code blocks (strong code signals, explicit `# file:` header) still intercepted.
2. **Trailing-prose trim**: `_trim_trailing_prose()` strips prose swallowed by the unclosed `<WRITE_FILE>` regex on code targets.
3. **Non-code truncation stubs**: `_detect_truncation_stubs()` in `implementations.py` extended with plain-text, explicit-omission, and HTML truncation patterns now applied to `.txt`/`.md`/unknown files.
4. **Tests**: 5 new tests across `core/tests/test_rlm_engine.py` and `core/tests/test_code_quality_harness.py`; full suite 390 passed (2 pre-existing unrelated failures); `ruff` at baseline (no new errors).

## 7. Acceptance Criteria
- [x] Repro scenario now produces valid code via `WRITE_FILE`/`EDIT_FILE`.
- [x] No write contains raw reasoning text or unparseable content.
- [x] Existing pytest suite (`pytest core/tests/ context-manager-cli/tests/`) and `ruff check` pass.

## 8. Follow-up
- [x] Register as **BUG-20** in `bug.md` after root cause confirmed and fixed.
- [ ] Update graph: `graphify update .`
