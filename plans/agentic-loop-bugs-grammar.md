# Plan: Agentic Loop Bugs & Grammar Issues

## Bugs in Agentic Loop

### B-01: Feedback loop case-sensitivity on tool names
**File:** `core/execution/feedback_loop.py`  
**Lines:** 182, 207  
**Severity:** Medium  
**Description:** `on_tool_executed` and `_should_run_tests` compare `tool_name` against hardcoded uppercase strings (`("WRITE_FILE", "EDIT_FILE")`, `("RUN_COMMAND", "WRITE_FILE", "EDIT_FILE")`).  
The CLI caller (`context-manager-cli/src/context_manager/cli/main.py:394`) passes `name` from parsed skills without normalizing case, while the RLM caller (`rlm_optimized/rlm_engine_optimized.py:814`) explicitly uppercases. If a lowercase tool name arrives, the feedback loop silently skips file tracking and auto-test execution.  
**Fix:** Normalize `tool_name` to uppercase at the top of `on_tool_executed` and `_should_run_tests`.

### B-02: Inline code interception path collision
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Lines:** 1520-1545  
**Severity:** Medium  
**Description:** Bare markdown code blocks without a `# file:` comment fall back to `"inline_code_output.txt"`. Multiple turns producing inline code will overwrite each other, causing silent data loss.  
**Fix:** Generate a unique fallback path (e.g., include turn counter or timestamp), or reject auto-write for ambiguous inline code.

### B-03: Memory compaction loses token accounting
**File:** `core/memory/manager.py`  
**Lines:** 445-449  
**Severity:** Medium  
**Description:** `compact_between_tasks` appends a summary `Message` without setting `token_count`. The field defaults to `0`, so `_cached_msg_tokens` becomes inaccurate after compaction. This causes `should_compress()` and budget calculations to drift, potentially triggering premature or missed compressions.  
**Fix:** Set `token_count=self.tokenizer.count(summary_content)` on the summary Message.

### B-04: Verification gate rejection message is too restrictive
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Line:** 526  
**Severity:** Low  
**Description:** The gate rejection says: "Use tools (READ_FILE, EDIT_FILE) to debug and resolve the failure." This omits other valid debugging tools like GREP, SEARCH_AST, RUN_COMMAND, and INSPECT_WEB. A model fixated on the listed tools may ignore better alternatives.  
**Fix:** Generalize to "Use tools (READ_FILE, EDIT_FILE, GREP, SEARCH_AST, RUN_COMMAND, etc.) to debug..."

### B-05: `preserve_continuous_context` getattr default mismatch
**File:** `core/execution/autonomous_harness.py`  
**Line:** 330  
**Severity:** Low  
**Description:** `HarnessConfig` defaults `preserve_continuous_context` to `False`, but `getattr(self.config, "preserve_continuous_context", True)` defaults to `True`. If the attribute is missing (e.g., mock config), behavior inverts from the intended default.  
**Fix:** Align the `getattr` default with the dataclass default: `getattr(self.config, "preserve_continuous_context", False)`.

### B-06: Planning tasks with empty `target_files` skip revert on failure
**File:** `core/execution/autonomous_harness.py`  
**Lines:** 685-717  
**Severity:** Low  
**Description:** `_git_revert([])` skips targeted revert and falls through to blanket revert, which requires `allow_blanket_revert=True` and a `.harness_managed` marker. Planning tasks that make no file edits and fail will leave the repo dirty without any revert.  
**Fix:** If `target_files` is empty, skip revert gracefully with a log message rather than falling through to blanket revert.

### B-07: Bare code block regex requires newline after backticks
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Line:** 1517  
**Severity:** Low  
**Description:** The regex `r"```(?:\w+)?\n(.*?)```"` requires a newline after the opening fence. Single-line code blocks like ` ```python x = 1 ``` ` are not matched and fall through to plain text handling.  
**Fix:** Make the newline optional: `r"```(?:\w+)?\n?(.*?)```"`.

### B-08: `_clean_and_parse_json` returns opaque `{"raw": raw}` for unrecognized dicts
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Lines:** 168-186  
**Severity:** Low  
**Description:** If a JSON object doesn't match the expected tool-call schema and lacks "path"/"content" keys, the function returns `{"raw": raw}`. The tool parser then treats this as `tool_args = {"raw": raw}`, losing the actual structure.  
**Fix:** Return the original parsed dict when regex extraction fails, rather than wrapping it.

### B-09: Unverified edits silently pass when no test framework exists
**File:** `core/execution/feedback_loop.py`  
**Lines:** 344-353  
**Severity:** Low  
**Description:** When no test command is detected and no web files exist, `_files_modified_since_test.clear()` is called. Edits to non-test, non-web files are silently treated as "nothing to verify," which can mask unverified changes.  
**Fix:** Preserve the dirty set and surface a "no verifier available" warning instead of clearing it.

---

## Grammar & Spelling Issues

### G-01: Singular/plural mismatch in docstring
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Line:** 80  
**Text:** "Extract strictly surgical failure traceback from test output"  
**Issue:** "traceback" is singular but the function extracts potentially multiple failures.  
**Fix:** "Extract strictly surgical failure tracebacks from test output" or "Extract a strictly surgical failure traceback from test output".

### G-02: Docstring subject-verb agreement
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Line:** 145  
**Text:** "Auto-run tests and web outcome inspection after code changes and inject feedback into context."  
**Issue:** Compound subject ("Auto-run tests...") with singular verb ("inject").  
**Fix:** "Auto-runs tests and web outcome inspection after code changes, and injects feedback into context."

### G-03: Ambiguous "grammar" reference
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Line:** 1268  
**Text:** "fallback shape when grammar is off"  
**Issue:** "grammar" could mean English grammar or JSON grammar. In context it means the GBNF tool-call grammar.  
**Fix:** "fallback shape when the tool-call grammar is off" or "fallback shape when constrained decoding grammar is off".

### G-04: Missing article
**File:** `context-manager-cli/src/context_manager/prompts.py`  
**Line:** 4  
**Text:** "V2: Optimized for local LLMs with concise guidance and explicit agent loop."  
**Fix:** "V2: Optimized for local LLMs with concise guidance and an explicit agent loop."

### G-05: Hyphenation / compound adjective
**File:** `core/prompts/system.py`  
**Line:** 15  
**Text:** "a truncation-stub rejection"  
**Issue:** "truncation-stub" is awkward as a compound adjective.  
**Fix:** "a truncation stub rejection" or "a truncation-stub rejection" (if intended as a compound modifier, hyphenate consistently).

### G-06: Redundant instruction
**File:** `rlm_optimized/prompts.py`  
**Lines:** 81-82, 127  
**Text:** Two identical "Keep reasoning EXTREMELY CONCISE — under 50 words (2-3 short sentences)" instructions.  
**Fix:** Remove one instance.

### G-07: Redundant modifier
**File:** `core/execution/autonomous_harness.py`  
**Line:** 80  
**Text:** "long-running continuous execution"  
**Issue:** "long-running" and "continuous" are redundant.  
**Fix:** "long-running execution" or "continuous execution".

### G-08: Informal slash in formal docstring
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Line:** 1140  
**Text:** "test state is still failing/unverified"  
**Fix:** "test state is still failing or unverified".

### G-09: British spelling in American codebase
**File:** `context-manager-cli/src/context_manager/cli/main.py`  
**Line:** 291  
**Text:** "Flashlight not initialised."  
**Fix:** "Flashlight not initialized."

### G-10: Awkward phrasal verb
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Line:** 299  
**Text:** "Re-append closing tags that were consumed as stop tokens"  
**Issue:** "Re-append" is clunky.  
**Fix:** "Reattach closing tags" or "Append closing tags back".

### G-11: Compound predicate punctuation
**File:** `core/execution/feedback_loop.py`  
**Line:** 145  
**Text:** "Auto-run tests and web outcome inspection after code changes and inject feedback into context."  
**Fix:** Add comma before final "and": "Auto-run tests and web outcome inspection after code changes, and inject feedback into context." (Also see G-02 for full subject-verb fix).

### G-12: Missing article in module docstring
**File:** `context-manager-cli/src/context_manager/prompts.py`  
**Line:** 2  
**Text:** "Torchlight prompt stack — single source of truth."  
**Fix:** "Torchlight prompt stack — the single source of truth."

### G-13: Inconsistent slash formatting
**File:** `core/prompts/system.py`  
**Line:** 19  
**Text:** "PENDING/IN_PROGRESS"  
**Issue:** Other status formatting in the codebase uses spaces or pipes.  
**Fix:** "PENDING or IN_PROGRESS" or keep consistent with project style.

### G-14: Missing Oxford comma in docstring
**File:** `rlm_optimized/rlm_engine_optimized.py`  
**Line:** 65  
**Text:** "Repair common LLM JSON corruption inside string values: raw (unescaped) newlines/tabs, and a trailing unterminated string."  
**Issue:** List of three items but only one comma.  
**Fix:** "raw (unescaped) newlines/tabs and a trailing unterminated string" (remove extra comma) or keep as-is if the colon introduces a list.

### G-15: Vague phrase in docstring
**File:** `core/memory/manager.py`  
**Line:** 429  
**Text:** "without losing debug and code improvement history."  
**Issue:** "code improvement history" is vague.  
**Fix:** "without losing debugging context and code change history."

---

## Recommended Fix Order

1. **B-01** (case-sensitivity) — highest impact, easy fix.
2. **B-03** (token accounting) — causes subtle memory drift.
3. **B-02** (inline code collision) — data loss bug.
4. **B-05** (getattr default mismatch) — correctness issue.
5. **G-01 through G-04** — grammar fixes that improve prompt clarity for LLMs.
