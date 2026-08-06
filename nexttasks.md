# Next Tasks: 21 Genuine Chaining & Context Issues for 7B Model (12k Context)

This file contains the 21 most genuine and high-impact issues identified in the Torchlight codebase, ordered from **Easy (Low Difficulty)** to **Hard Difficulty** to be easily parsed and acted upon by LLM agents.

---

## 📊 Summary Table

| Task # | Feature / Issue | Difficulty | Improvement Rate | Files Linked |
|:---:|---|:---:|:---:|---|
| **10** | Strict JSON Parsing Failure in Critic | 🟢 Low | 9 / 10 | [core/debate/verifier.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/debate/verifier.py) |
| **11** | POSIX Tab Normalization Corrupting Code | 🟢 Low | 9 / 10 | [core/tools/implementations.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/implementations.py) |
| **12** | Inaccurate Token Estimation via Word-Based Heuristic | 🟢 Low | 7 / 10 | [core/memory/token_counter.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/memory/token_counter.py) |
| **13** | Verbose Error Traceback Swallowing | 🟢 Low | 8 / 10 | [core/execution/feedback_loop.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/feedback_loop.py) |
| **14** | Symlink Recursion during Symbol Indexing | 🟢 Low | 8 / 10 | [core/flashlight/indexer.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/flashlight/indexer.py) |
| **15** | Rigid Tool Parameter Type Checking | 🟢 Low | 8 / 10 | [core/tools/schemas.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/schemas.py) |
| **20** | Truncation and Stop-Token Dropping | 🟢 Low | 8 / 10 | [context-manager-cli/src/context_manager/cli/main.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py)<br>[rlm_optimized/rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py) |
| **21** | Runaway Sub-Query Depth | 🟢 Low | 7 / 10 | [core/flashlight/beam.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/flashlight/beam.py) |
| **2** | Critic Hallucinations (Over-Critique) | 🟡 Medium | 8 / 10 | [core/debate/verifier.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/debate/verifier.py) |
| **3** | Brittle Phrase-Based Phase Switching | 🟡 Medium | 7 / 10 | [context-manager-cli/src/context_manager/cli/main.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py) |
| **4** | Non-Canonical Diff Match Failures | 🟡 Medium | 9 / 10 | [core/tools/implementations.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/implementations.py) |
| **5** | LLM Embedding API Contention on 8GB Machines | 🟡 Medium | 6 / 10 | [core/memory/embeddings.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/memory/embeddings.py) |
| **6** | Verbose System Prompt Tool Schema Bloat | 🟡 Medium | 7 / 10 | [core/prompts/system.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/prompts/system.py)<br>[core/tools/registry.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/registry.py)<br>[core/tools/schemas.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/schemas.py) |
| **7** | The TDD Test-Rewrite Loop Trap | 🟡 Medium | 9 / 10 | [core/execution/feedback_loop.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/feedback_loop.py)<br>[core/execution/autonomous_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/autonomous_harness.py) |
| **8** | AST Graph Cache Invalidation Granularity | 🟡 Medium | 5 / 10 | [core/flashlight/graph_engine.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/flashlight/graph_engine.py) |
| **9** | L0 Working Memory Scratchpad size Fluctuation | 🟡 Medium | 7 / 10 | [core/memory/manager.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/memory/manager.py)<br>[core/memory/budget.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/memory/budget.py) |
| **18** | Repetitive Tool Call Loops | 🟡 Medium | 9 / 10 | [context-manager-cli/src/context_manager/cli/main.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py)<br>[rlm_optimized/rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py) |
| **19** | Write/Edit Gate Validation Hardening | 🟡 Medium | 6 / 10 | [core/tools/implementations.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/implementations.py) |
| **1** | Context Degradation on Multi-File Edits | 🔴 Hard | 8 / 10 | [core/execution/run_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/run_harness.py)<br>[context-manager-cli/src/context_manager/cli/main.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py)<br>[rlm_optimized/rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py) |
| **16** | Lack of Visual Outcome Validation | 🔴 Hard | 8 / 10 | [core/execution/web_inspector.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/web_inspector.py)<br>[core/execution/feedback_loop.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/feedback_loop.py) |
| **17** | Safe Checkpoints and Candidate Branching | 🔴 Hard | 9 / 10 | [core/execution/autonomous_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/autonomous_harness.py) |

---

## 🟢 Low Difficulty (Easy)

### - [x] Task 10: Strict JSON Parsing Failure in Critic
* **Issue:** The Critic fails to output perfectly formatted JSON objects, crashing the verifier loop.
* **Current Implementation:** `_parse_critique_json` parses the Critic's raw output with `json.loads`.
* **Proposed Fix:** Switch the Critic to wrap output sections in `<flaw>...</flaw>` XML tags and parse using simple regular expressions.
* **Improvement Rate:** 9 / 10
* **Files Linked:** [core/debate/verifier.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/debate/verifier.py)

#### Implementation Steps
1. **Open** `core/debate/verifier.py`, locate `_parse_critique_json()` at **L145**.
2. **Before** the `json.loads()` attempt at **L163**, add an XML-tag extraction pass:
   ```python
   # Try XML tag extraction first (more robust for 7B models)
   flaw_matches = re.findall(r'<flaw>(.*?)</flaw>', text, re.DOTALL)
   rec_matches = re.findall(r'<recommendation>(.*?)</recommendation>', text, re.DOTALL)
   if flaw_matches or rec_matches:
       result.has_flaws = bool(flaw_matches)
       result.flaws = [f.strip() for f in flaw_matches]
       result.recommendations = [r.strip() for r in rec_matches]
       return result
   ```
3. **Keep** the existing `json.loads` path as a fallback after the XML pass.
4. **Update** the critic prompt in `core/debate/prompts.py` — change the output format instruction from "respond with JSON" to "wrap each flaw in `<flaw>...</flaw>` tags and each recommendation in `<recommendation>...</recommendation>` tags".
5. **Test:** Run `pytest core/tests/test_debate.py` to verify the XML parser handles both clean XML and malformed fallback cases.

### - [x] Task 11: POSIX Tab Normalization Corrupting Code
* **Issue:** The whitespace normalizer replaces tabs with spaces, potentially breaking C, ASM, and other tab-convention files (Makefiles and Go are already excluded).
* **Current Implementation:** `_normalize_whitespace()` at `implementations.py:L691` preserves tabs for `.go`, `.tsv`, `.tab`, `.mk`, and `Makefile`/`GNUmakefile`, but converts tabs to spaces for all other file types.
* **Proposed Fix:** Extend the `preserve_tabs` extension list to include `.c`, `.h`, `.asm`, `.s`, and other files with tab conventions, or switch to a whitelist approach (only normalize known safe extensions).
* **Improvement Rate:** 9 / 10
* **Files Linked:** [core/tools/implementations.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/implementations.py)

#### Implementation Steps
1. **Open** `core/tools/implementations.py`, locate `_normalize_whitespace()` at **L691**.
2. **At L697**, modify the `preserve_tabs` extension tuple from:
   ```python
   preserve_tabs = ext in (".go", ".tsv", ".tab", ".mk") or basename in ("makefile", "gnumakefile")
   ```
   To:
   ```python
   _TAB_PRESERVE_EXTS = {".go", ".tsv", ".tab", ".mk", ".c", ".h", ".cpp", ".hpp",
                          ".asm", ".s", ".zig", ".lua", ".just"}
   _TAB_PRESERVE_BASENAMES = {"makefile", "gnumakefile", "justfile", "kbuild"}
   preserve_tabs = ext in _TAB_PRESERVE_EXTS or basename in _TAB_PRESERVE_BASENAMES
   ```
3. Move the sets to **module-level constants** (above `_normalize_whitespace`) for testability.
4. **Test:** Write a test in `core/tests/` that calls `_normalize_whitespace("\tindented\n", "test.c")` and asserts the tab is preserved. Also test `"test.py"` confirms tabs are converted.

### - [x] Task 12: Inaccurate Token Estimation via Word-Based Heuristic
* **Issue:** The fallback word-based heuristic (`_estimate()` at `token_counter.py:L34`) counts words + CJK chars + symbols/2, which can under/overcount tokens for code-heavy content with dense symbols.
* **Current Implementation:** `_estimate()` uses `re.findall(r"\b\w+\b", text)` for word counting plus CJK character and symbol counting — not `len(text) // 4`.
* **Proposed Fix:** Improve the heuristic to weight code tokens more heavily (operators, brackets count as full tokens), or enforce tiktoken availability as a hard dependency.
* **Improvement Rate:** 7 / 10
* **Files Linked:** [core/memory/token_counter.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/memory/token_counter.py)

#### Implementation Steps
1. **Open** `core/memory/token_counter.py`, locate `_estimate()` at **L34**.
2. **Replace** the `symbols // 2` logic at **L40** with a code-aware heuristic:
   ```python
   def _estimate(self, text: str) -> int:
       if not text:
           return 0
       cjk = len(re.findall(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', text))
       words = len(re.findall(r'\b\w+\b', text))
       # Count code operators and brackets as individual tokens
       operators = len(re.findall(r'[{}()\[\]<>!=+\-*/&|^~%@;:,.]', text))
       # Newlines cost ~1 token each in most tokenizers
       newlines = text.count('\n')
       return words + cjk + operators + (newlines // 2)
   ```
3. **Add a safety multiplier** of `1.1x` (10% padding) to prevent undercount:
   ```python
   return int((words + cjk + operators + (newlines // 2)) * 1.1)
   ```
4. **Test:** In `core/tests/`, create `test_token_counter.py`:
   - Compare `_estimate()` output against `tiktoken.encode()` output for 5 code snippets.
   - Assert the heuristic is within ±15% of the tiktoken count.

### - [x] Task 13: Verbose Error Traceback Swallowing
* **Issue:** Shoving raw 500-line pytest dumps directly into context blows the 12k context limit.
* **Current Implementation:** Standard command tracebacks are printed entirely into the chat history.
* **Proposed Fix:** Parse test output and extract only the assertion failure and filename:line coordinate, dropping clean stack traces.
* **Improvement Rate:** 8 / 10
* **Files Linked:** [core/execution/feedback_loop.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/feedback_loop.py)

#### Implementation Steps
1. **Open** `core/execution/feedback_loop.py`, locate `extract_surgical_traceback()` at **L80**.
2. **Reduce** the pytest FAILURES capture cap from `[:40]` lines (L105) to `[:20]` lines.
3. **Reduce** the Python traceback capture from `[tb_idx : tb_idx + 35]` (L124) to `[tb_idx : tb_idx + 15]`.
4. **Add a token budget parameter** to `extract_surgical_traceback()`:
   ```python
   def extract_surgical_traceback(output: str, command: str = "", max_lines: int = 20) -> str:
   ```
   Replace all hardcoded line caps with `max_lines`.
5. **At L533** (where `surgical_tb` is injected into context), add a hard character cap:
   ```python
   if len(surgical_tb) > 1500:  # ~375 tokens
       surgical_tb = surgical_tb[:1500] + "\n... [truncated]"
   ```
6. **At L540**, wrap the traceback injection in a compact format:
   ```python
   f"Test failure in {filename}:{line} — {assertion_msg}\n```\n{surgical_tb}\n```"
   ```
7. **Test:** Run `pytest core/tests/test_feedback_loop.py` and verify traceback output stays under 400 tokens.

### - [x] Task 14: Symlink Recursion during Symbol Indexing
* **Issue:** Traversing recursive symlink directories causes infinite loops during graph index runs.
* **Current Implementation:** `indexer.py:L57` uses `os.walk(self.project_dir)` without `followlinks=False` guard or visited-inode tracking.
* **Proposed Fix:** Add `followlinks=False` to `os.walk()` calls or track visited inodes to prevent symlink-induced infinite recursion.
* **Improvement Rate:** 8 / 10
* **Files Linked:** [core/flashlight/indexer.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/flashlight/indexer.py)

#### Implementation Steps
1. **Open** `core/flashlight/indexer.py`, locate `SymbolIndex.build()` at **L53**.
2. **At L57**, change:
   ```python
   for root, dirs, files in os.walk(self.project_dir):
   ```
   To:
   ```python
   for root, dirs, files in os.walk(self.project_dir, followlinks=False):
   ```
3. **Add symlink directory filtering** inside the dirs pruning at **L58**:
   ```python
   dirs[:] = [d for d in dirs if d not in IGNORE_DIRS
              and not os.path.islink(os.path.join(root, d))]
   ```
4. **Also add symlink file skip** at **L60**, before processing each file:
   ```python
   path = Path(root) / file
   if path.is_symlink():
       continue
   ```
5. **Do the same** in `core/flashlight/graph_engine.py` — search for all `os.walk()` calls and apply `followlinks=False`.
6. **Test:** Create a temp directory with a recursive symlink in `core/tests/test_indexer.py`, call `SymbolIndex.build()`, assert it completes without hanging.

### - [x] Task 15: Rigid Tool Parameter Type Checking
* **Issue:** Validator schemas throw errors on minor type mismatches (e.g. passing a port parameter as a string `"8080"` instead of `8080`).
* **Current Implementation:** Strict type checking inside tool schemas.
* **Proposed Fix:** Implement coercive type casting inside the tool validator to resolve primitive mismatches.
* **Improvement Rate:** 8 / 10
* **Files Linked:** [core/tools/schemas.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/schemas.py)

#### Implementation Steps
1. **Open** `core/tools/schemas.py`, locate `validate_tool_call()` at **L408**.
2. **Add a coercion helper** function above `validate_tool_call()`:
   ```python
   def _coerce_param(value, expected_type: str):
       """Coerce LLM-provided values to expected schema types."""
       if expected_type == "integer" and isinstance(value, str):
           try: return int(value)
           except ValueError: pass
       if expected_type == "number" and isinstance(value, str):
           try: return float(value)
           except ValueError: pass
       if expected_type == "boolean" and isinstance(value, str):
           return value.lower() in ("true", "1", "yes")
       if expected_type == "string" and not isinstance(value, str):
           return str(value)
       return value
   ```
3. **Inside `validate_tool_call()`**, after the alias resolution block (L424-430), add coercion:
   ```python
   # Coerce parameter types to match schema expectations
   properties = schema.get("properties", {})
   for key, prop_def in properties.items():
       if key in normalized and normalized[key] is not None:
           expected = prop_def.get("type", "string")
           normalized[key] = _coerce_param(normalized[key], expected)
   ```
4. **Test:** Run `pytest core/tests/test_schemas.py` — add cases like `validate_tool_call("READ_FILE", {"path": "/tmp/x", "start_line": "10"})` asserting `start_line` gets coerced to `int(10)`.

### - [x] Task 20: Truncation and Stop-Token Dropping
* **Issue:** Local inference engines (LM Studio/llama.cpp) drop stop tokens or truncate blocks under context limits, leaving tags like `</tool_call>` unclosed.
* **Current Implementation:** Simple regex parser throws a syntax exception, causing the turn to fail.
* **Proposed Fix:** Implement a stream-intercepting tag-recovery parser that automatically closes structural tags (e.g., XML/JSON tags) when the model output terminates prematurely.
* **Improvement Rate:** 8 / 10
* **Files Linked:** [context-manager-cli/src/context_manager/cli/main.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py), [rlm_optimized/rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py)

#### Implementation Steps
1. **Reference:** The TUI engine already has `_repair_stop_tokens()` at `rlm_engine_optimized.py:L441` with `_STOP_TAG_PAIRS` at L432. This needs to be **ported to the CLI engine**.
2. **Open** `context-manager-cli/src/context_manager/cli/main.py`, locate the `StreamingChatSession` class at **L153**.
3. **Add** the same `_STOP_TAG_PAIRS` list and `_repair_stop_tokens()` method:
   ```python
   _STOP_TAG_PAIRS = [
       ("<WRITE_FILE", "</WRITE_FILE>"),
       ("<TOOL", "</TOOL>"),
       ("<CODE>", "</CODE>"),
       ("<FINAL_ANSWER>", "</FINAL_ANSWER>"),
       ("<action>", "</action>"),
       ("<tool_call>", "</tool_call>"),
   ]

   def _repair_stop_tokens(self, text: str) -> str:
       for open_tag, close_tag in self._STOP_TAG_PAIRS:
           if open_tag.lower() in text.lower() and close_tag.lower() not in text.lower():
               text = text.rstrip() + close_tag
               break
       return text
   ```
4. **Call** `_repair_stop_tokens()` on the raw LLM response immediately after streaming completes, **before** the tool-call parser runs (around **L671-676** in the chain loop).
5. **Also add JSON recovery** — if tool_call content has unclosed `}`, count `{` vs `}` and append missing braces:
   ```python
   open_braces = text.count('{') - text.count('}')
   if open_braces > 0:
       text = text.rstrip() + '}' * open_braces
   ```
6. **Test:** Create a test case with truncated output `"<tool_call>{'name': 'READ_FILE'"` and verify recovery produces valid parseable output.

### - [x] Task 21: Runaway Sub-Query Depth
* **Issue:** Recursive sub-query calls can spawn runaway execution cycles, consuming enormous token volumes and API costs on small models.
* **Current Implementation:** Depth tracking exists but has soft enforcement constraints.
* **Proposed Fix:** Enforce a hard cap of 2 recursion levels for sub-queries, automatically falling back to synthesizing responses from current context when the limit is hit.
* **Improvement Rate:** 7 / 10
* **Files Linked:** [core/flashlight/beam.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/flashlight/beam.py)

#### Implementation Steps
1. **Open** `core/flashlight/beam.py`, locate the `Flashlight` class at **L53**.
2. **Add** a depth-tracking parameter to `__init__` at L54:
   ```python
   self._query_depth = 0
   _MAX_QUERY_DEPTH = 2
   ```
3. **In `beam()`** at **L94**, add a depth guard at the top:
   ```python
   def beam(self, query: str, max_files: Optional[int] = None, _depth: int = 0) -> list[BeamResult]:
       if _depth >= self._MAX_QUERY_DEPTH:
           return []  # Stop recursion, use current context
   ```
4. **Find all call-sites** that invoke `beam()` or `beam_block()` — search for `.beam(` and `.beam_block(` across the codebase. If any pass queries recursively, ensure they increment `_depth`.
5. **In the engine chain loops** (`cli/main.py:L671` and `rlm_engine_optimized.py`), track a `sub_query_count` counter per turn and hard-cap at 2:
   ```python
   if sub_query_count >= 2:
       # Inject: "Sub-query limit reached. Synthesize from available context."
       break
   sub_query_count += 1
   ```
6. **Test:** Call `beam()` with `_depth=3` and assert it returns an empty list immediately.

---

## 🟡 Medium Difficulty

### - [x] Task 2: Critic Hallucinations (Over-Critique)
* **Issue:** 7B models acting as the Critic hallucinate errors or logical flaws in correct proposals.
* **Current Implementation:** [verifier.py:L139-140](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/debate/verifier.py#L139) refines proposals if `has_flaws` is true AND `flaws` or `recommendations` are present. Additionally, the `_parse_critique_json` fallback (L168-172) heuristically sets `has_flaws=True` on any JSON parse failure containing words like "flaw", "error", or "missing" — making 7B models particularly prone to false positives.
* **Proposed Fix:** Run compiler/syntax gates (e.g., Python AST parser) programmatically before calling the Critic, forcing the LLM Critic to focus only on confirmed compiler errors or semantic issues. Also tighten the heuristic fallback to require stronger signals than single-word matches.
* **Improvement Rate:** 8 / 10
* **Files Linked:** [core/debate/verifier.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/debate/verifier.py)

#### Implementation Steps
1. **Open** `core/debate/verifier.py`, locate `_parse_critique_json()` at **L145**.
2. **At L168-172**, tighten the heuristic fallback — replace single-word matching:
   ```python
   if "flaw" in lower_text or "error" in lower_text or "missing" in lower_text:
   ```
   With multi-word pattern matching that requires at least 2 indicator words:
   ```python
   flaw_indicators = ["syntax error", "logic flaw", "missing import", "undefined variable",
                      "type mismatch", "incorrect return", "broken reference"]
   if sum(1 for ind in flaw_indicators if ind in lower_text) >= 1:
   ```
3. **Add a pre-critique compiler gate** in the `critique()` method at **L64**. Before calling the LLM critic, run `ast.parse()` on any Python code in the proposal:
   ```python
   # Pre-critique: only flag if code actually has compile errors
   import ast
   code_blocks = re.findall(r'```python\n(.*?)```', proposal, re.DOTALL)
   compile_errors = []
   for block in code_blocks:
       try:
           ast.parse(block)
       except SyntaxError as e:
           compile_errors.append(f"L{e.lineno}: {e.msg}")
   ```
4. **Inject** `compile_errors` into the critic prompt so the LLM focuses on real issues:
   ```python
   if compile_errors:
       user_content += f"\n\nConfirmed compile errors: {compile_errors}"
   else:
       user_content += "\n\nNote: Code compiles cleanly. Focus on semantic/logic issues only."
   ```
5. **Test:** Run `pytest core/tests/test_debate.py` — add a test with syntactically correct code and verify the critic doesn't hallucinate flaws.

### - [x] Task 3: Brittle Phrase-Based Phase Switching
* **Issue:** Prompt phrases (e.g., `"why is"`, `"debug"`) trigger false phase transitions, swapping temperature presets and prompts unnecessarily.
* **Current Implementation:** [_detect_phase](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py#L379) uses raw substring matches on inputs.
* **Proposed Fix:** Implement a deterministic state-locking engine (e.g., lock phase to `troubleshoot` only after an actual command failure, lock to `code` after file edits).
* **Improvement Rate:** 7 / 10
* **Files Linked:** [context-manager-cli/src/context_manager/cli/main.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py)

#### Implementation Steps
1. **Open** `context-manager-cli/src/context_manager/cli/main.py`, locate `_detect_phase()` at **L379**.
2. **Add a `_phase_lock` attribute** to `StreamingChatSession.__init__()` at **L225**:
   ```python
   self._phase_lock: Optional[str] = None  # Event-driven lock
   self._phase_lock_reason: str = ""
   ```
3. **Create a new method** `_event_lock_phase()` that sets the lock based on concrete events:
   ```python
   def _event_lock_phase(self, event: str, data: str = "") -> None:
       if event == "tool_error":
           self._phase_lock = "troubleshoot"
           self._phase_lock_reason = f"Tool failure: {data}"
       elif event == "file_edit":
           self._phase_lock = "code"
           self._phase_lock_reason = f"Editing: {data}"
       elif event == "user_explicit":
           self._phase_lock = None  # User can override
   ```
4. **In `_detect_phase()`** at L379, check the lock first:
   ```python
   def _detect_phase(self, user_input: str, last_response: str = "") -> str:
       if self._phase_lock:
           return self._phase_lock
       # ... existing substring matching ...
   ```
5. **Call `_event_lock_phase()`** at tool execution points:
   - After a `RUN_COMMAND` tool returns non-zero exit code → `_event_lock_phase("tool_error", cmd)`
   - After a `WRITE_FILE`/`EDIT_FILE` tool succeeds → `_event_lock_phase("file_edit", filename)`
6. **Auto-release the lock** after 2 turns by adding a turn counter that decrements and clears the lock.
7. **Test:** Run `pytest context-manager-cli/tests/test_phase_detection.py` — add tests verifying that a tool error locks phase to `troubleshoot` and a file edit locks to `code`.

### - [x] Task 4: Non-Canonical Diff Match Failures
* **Issue:** The model omits dividers (like `=======`) in diff match blocks, crashing file edit operations.
* **Current Implementation:** `_parse_diff_block` expects canonical dividers.
* **Proposed Fix:** Implement a fuzzy diff fallback parser that tries 3-way line matching or standard Levenshtein-distance line alignment when structural tags are missing.
* **Improvement Rate:** 9 / 10
* **Files Linked:** [core/tools/implementations.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/implementations.py)

#### Implementation Steps
1. **Open** `core/tools/implementations.py`, locate `_parse_diff_block()` at **L1179**.
2. **At the end of the function** (after all existing regex attempts), add a fallback parser that handles bare content without structural dividers:
   ```python
   # Fallback C: No structural tags at all — try splitting on blank-line heuristic
   # If the content has exactly 2 large blocks separated by 2+ blank lines, treat them as search/replace
   parts = re.split(r'\n\s*\n\s*\n', text.strip(), maxsplit=1)
   if len(parts) == 2 and len(parts[0]) > 10 and len(parts[1]) > 10:
       return _clean_segment(parts[0]), _clean_segment(parts[1])
   ```
3. **Add line-by-line similarity matching** as a last resort — above the fallback block:
   ```python
   # Fallback D: Levenshtein-distance line alignment
   # If the diff has >= 60% matching lines, treat first half as search, second as replace
   lines = text.strip().splitlines()
   if len(lines) >= 4:
       mid = len(lines) // 2
       return _clean_segment('\n'.join(lines[:mid])), _clean_segment('\n'.join(lines[mid:]))
   ```
4. **Ensure** the fallback returns `(None, None)` if nothing matches — the caller at **L1341** already handles `None` by delegating to `WRITE_FILE`.
5. **Test:** Add tests in `core/tests/test_diff_edit.py` with diff blocks missing `=======` dividers and verify they parse correctly.

### - [x] Task 5: LLM Embedding API Contention on 8GB Machines
* **Issue:** When `HybridEmbedder` delegates to `llm_client.get_embeddings()`, it sends embedding requests to the same LM Studio server running the main LLM, competing for inference slots and potentially stalling the agentic loop on 8GB machines.
* **Current Implementation:** `embeddings.py` uses pure-Python `KeywordEmbedder` (hash-based, zero GPU) as fallback. The `HybridEmbedder` optionally calls `llm_client.get_embeddings()` which routes through the same LM Studio endpoint — this is an API-level contention issue, not a GPU model loading issue.
* **Proposed Fix:** Disable LLM-based embeddings on 8GB machines (force `KeywordEmbedder` fallback) or route embedding requests to a separate lightweight server/endpoint to avoid blocking the primary inference pipeline.
* **Improvement Rate:** 6 / 10
* **Files Linked:** [core/memory/embeddings.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/memory/embeddings.py)

#### Implementation Steps
1. **Open** `core/memory/embeddings.py`, locate `HybridEmbedder.__init__()` at **L85**.
2. **Add a memory-aware gate** that checks available system RAM:
   ```python
   import os
   def _is_low_memory() -> bool:
       """Return True on machines with <= 8GB RAM."""
       try:
           import psutil
           return psutil.virtual_memory().total <= 8 * 1024**3
       except ImportError:
           # Fallback: check macOS sysctl
           try:
               mem = int(os.popen('sysctl -n hw.memsize').read().strip())
               return mem <= 8 * 1024**3
           except Exception:
               return False
   ```
3. **In `HybridEmbedder.embed_sync()`** at **L89**, skip the LLM path on low-memory machines:
   ```python
   def embed_sync(self, text: str) -> list[float]:
       if _is_low_memory() or self.llm_client is None:
           return self.keyword_embedder.embed_sync(text)
       # ... existing LLM path ...
   ```
4. **Also add an env var override** `TORCHLIGHT_FORCE_KEYWORD_EMBEDDINGS=1` for explicit control:
   ```python
   if os.environ.get("TORCHLIGHT_FORCE_KEYWORD_EMBEDDINGS"):
       return self.keyword_embedder.embed_sync(text)
   ```
5. **Update** `build_embedder()` at **L189** to pass through the memory check.
6. **Test:** Set the env var in `core/tests/` and verify `HybridEmbedder` never calls `llm_client.get_embeddings()`.

### - [x] Task 6: Verbose System Prompt Tool Schema Bloat
* **Issue:** Loading JSON schemas for all 18 tools consumes 300+ context tokens on every turn.
* **Current Implementation:** Tool schemas are loaded statically into the system prompt.
* **Proposed Fix:** Dynamically register/hide tool schemas in the prompt depending on the current phase (e.g., disable shell tools during the planning phase).
* **Improvement Rate:** 7 / 10
* **Files Linked:** [core/prompts/system.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/prompts/system.py), [core/tools/registry.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/registry.py), [core/tools/schemas.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/schemas.py)

#### Implementation Steps
1. **Open** `core/tools/schemas.py`, locate `TOOL_SCHEMAS` dict at **L13**.
2. **Add a `phase_visibility` key** to each tool schema entry:
   ```python
   "READ_FILE": {
       "phase_visibility": ["plan", "code", "troubleshoot", "chat"],  # always visible
       ...
   },
   "RUN_COMMAND": {
       "phase_visibility": ["code", "troubleshoot"],  # hidden during plan/chat
       ...
   },
   ```
3. **Add a filter function** in `core/tools/schemas.py`:
   ```python
   def get_schemas_for_phase(phase: str) -> dict:
       return {name: schema for name, schema in TOOL_SCHEMAS.items()
               if phase in schema.get("phase_visibility", ["plan", "code", "troubleshoot", "chat"])}
   ```
4. **Open** `core/tools/registry.py`, locate where tool schemas are loaded (around **L88**).
5. **Modify** the registry's `get_tool_prompt_suffix()` or equivalent to accept a `phase` parameter and call `get_schemas_for_phase(phase)`.
6. **Open** `core/prompts/system.py`. In the `SYSTEM_PROMPT` at L7, the `[TOOL PIPELINE]` section (L24-34) is static. Replace it with a dynamic placeholder `{tool_pipeline}` and generate it at runtime from the filtered schema.
7. **In the engine** (`cli/main.py` and `rlm_engine_optimized.py`), pass `self._current_phase` when building the system prompt.
8. **Test:** Call `get_schemas_for_phase("plan")` and verify `RUN_COMMAND` is excluded. Call with `"code"` and verify it's included.

### - [x] Task 7: The TDD Test-Rewrite Loop Trap
* **Issue:** When tests fail, the model attempts to rewrite the tests to pass rather than fixing the code.
* **Current Implementation:** The harness allows edits to any workspace file, including tests, during error recovery.
* **Proposed Fix:** Make test files read-only during automated recovery epochs unless explicit user confirmation is received.
* **Improvement Rate:** 9 / 10
* **Files Linked:** [core/execution/feedback_loop.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/feedback_loop.py), [core/execution/autonomous_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/autonomous_harness.py)

#### Implementation Steps
1. **Open** `core/execution/autonomous_harness.py`, locate `HarnessConfig` dataclass at **L62**.
2. **Add a field** to track protected test file patterns:
   ```python
   test_file_patterns: list[str] = field(default_factory=lambda: [
       "test_", "_test.py", "tests/", "spec/", ".test.", ".spec."
   ])
   protect_tests_during_recovery: bool = True
   ```
3. **Create a helper method** on `AutonomousHarness`:
   ```python
   def _is_test_file(self, filepath: str) -> bool:
       basename = os.path.basename(filepath).lower()
       return any(pat in filepath.lower() for pat in self.config.test_file_patterns)
   ```
4. **In the tool execution path**, locate where `WRITE_FILE` and `EDIT_FILE` are dispatched (in `core/tools/implementations.py` — the `tool_write_file()` and `tool_edit_file()` functions).
5. **Add a guard parameter** `protect_tests: bool = False` to both functions. When `True`, check if the target path is a test file and return an error:
   ```python
   if protect_tests and _is_test_file(filepath):
       return "Error: Test files are protected during automated recovery. Fix the source code instead."
   ```
6. **In `AutonomousHarness._run_epoch()`** (around **L471**), when running in error-recovery mode, pass `protect_tests=True` to tool dispatches.
7. **Inject a directive** into the system prompt during recovery phases:
   ```python
   "CRITICAL: You MUST NOT modify test files during this recovery cycle. Fix the source code to make tests pass."
   ```
8. **Test:** Add a test in `core/tests/test_autonomous_harness.py` that attempts to write to `test_main.py` during recovery and verifies the write is blocked.

### - [x] Task 8: AST Graph Cache Invalidation Granularity
* **Issue:** The in-memory graph cache (`_graphs` dict at `graph_engine.py:L533`) invalidates the **entire** project graph when any single file is edited, causing a full rebuild on the next query. This is wasteful for single-file changes.
* **Current Implementation:** `get_project_graph()` at L535-544 already caches parsed graphs in memory and only reloads from disk on first access. Invalidation uses `_graphs.pop()` which drops the whole graph.
* **Proposed Fix:** Implement **incremental graph invalidation** — re-parse only the changed file's AST nodes and merge them into the cached graph, instead of discarding and rebuilding the entire graph.
* **Improvement Rate:** 5 / 10
* **Files Linked:** [core/flashlight/graph_engine.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/flashlight/graph_engine.py)

#### Implementation Steps
1. **Open** `core/flashlight/graph_engine.py`, locate `update_project_graph_file()` at **L547**.
2. **This function already exists** and calls `graph.update_file(abs_path, rel_path)` — verify `update_file()` merges correctly.
3. **Locate** all call-sites that do `_graphs.pop(key)` to invalidate the cache. Replace them with calls to `update_project_graph_file(project_root, changed_file)`.
4. **In** `core/tools/implementations.py`, search for where file writes trigger graph invalidation (grep for `_graphs.pop` or `invalidate`). Replace with:
   ```python
   from core.flashlight.graph_engine import update_project_graph_file
   update_project_graph_file(project_root, filepath)
   ```
5. **Add a `remove_file()` method** on `ProjectGraph` for file deletions:
   ```python
   def remove_file(self, rel_path: str) -> None:
       # Remove all nodes and edges referencing this file
       to_remove = [nid for nid in self.nodes if rel_path in nid]
       for nid in to_remove:
           del self.nodes[nid]
       self.edges = [(s, t, l) for s, t, l in self.edges
                     if s not in to_remove and t not in to_remove]
   ```
6. **Test:** Build a graph, modify one file, call `update_project_graph_file()`, and verify only that file's nodes changed while others remain intact.

### - [x] Task 9: L0 Working Memory Scratchpad size Fluctuation
* **Issue:** When context is full, the L0 scratchpad shrinks dynamically, causing the model to lose critical constraints right when it needs them most.
* **Current Implementation:** Headroom calculation dynamically scales L0 scratchpad tokens down under pressure.
* **Proposed Fix:** Allocate a static safety margin (e.g., 600 tokens) for L0 context that cannot be evicted under context pressure.
* **Improvement Rate:** 7 / 10
* **Files Linked:** [core/memory/manager.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/memory/manager.py), [core/memory/budget.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/memory/budget.py)

#### Implementation Steps
1. **Open** `core/memory/budget.py`, locate `ContextBudget` dataclass at **L26**.
2. **Change** `l0_min_tokens` from `150` to `600` at **L39**:
   ```python
   l0_min_tokens: int = 600  # Was 150 — static safety floor
   ```
3. **In the `l0_tokens` property** at **L67-73**, the `_clamp()` already enforces the floor. With `l0_min_tokens=600`, the L0 scratchpad will never shrink below 600 tokens even under maximum context pressure.
4. **Verify the budget math**: At 12k context, 600 tokens = ~5% reserved. System prompt (~300) + L0 floor (600) + tool schema (~300) = 1200 tokens reserved, leaving ~9000 for conversation. This is acceptable.
5. **Open** `core/memory/manager.py`, locate `format_l0_scratchpad()` (search for it).
6. **Add a priority-ordered rendering** — when the L0 budget is at the floor (600 tokens), ensure these items render first:
   - Active goal (always)
   - Failing tests / active errors (always)
   - Tried-and-failed log (always, max 3 entries)
   - Modified files list (if space permits)
   - Key decisions (if space permits)
7. **Test:** Create a `ContextBudget` with `used_tokens` close to `target_tokens` (e.g., 95% full) and assert `l0_tokens` returns exactly `600`.

### - [x] Task 18: Repetitive Tool Call Loops
* **Issue:** The model enters an infinite execution loop when a tool fails, resubmitting the identical arguments over and over.
* **Current Implementation:** Basic retry counts are tracked, but arguments are not verified for duplicates.
* **Proposed Fix:** Track the hash of the last 3 tool calls; if a duplicate is detected, block execution, temporarily elevate the temperature parameter, and inject a strict redirection prompt.
* **Improvement Rate:** 9 / 10
* **Files Linked:** [context-manager-cli/src/context_manager/cli/main.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py), [rlm_optimized/rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py)

#### Implementation Steps
1. **Open** `context-manager-cli/src/context_manager/cli/main.py`, locate the chain loop at **L668-706**.
2. **Add a dedup ring buffer** in `StreamingChatSession.__init__()` at **L225**:
   ```python
   import hashlib
   self._recent_tool_hashes: list[str] = []  # Last 3 tool call hashes
   _MAX_TOOL_DEDUP = 3
   ```
3. **Create a hash function** for tool calls:
   ```python
   def _hash_tool_call(self, name: str, args: dict) -> str:
       payload = f"{name}:{sorted(args.items())}"
       return hashlib.md5(payload.encode()).hexdigest()[:12]
   ```
4. **Inside the chain loop** (around L671-676), before executing each tool call:
   ```python
   call_hash = self._hash_tool_call(tool_name, tool_args)
   if call_hash in self._recent_tool_hashes:
       # Duplicate detected — break the loop
       self._inject_redirect_prompt(
           f"STOP: You just repeated the same '{tool_name}' call. "
           f"Try a DIFFERENT tool or approach."
       )
       self._params.temperature = min(0.9, self._params.temperature + 0.3)
       break
   self._recent_tool_hashes.append(call_hash)
   if len(self._recent_tool_hashes) > self._MAX_TOOL_DEDUP:
       self._recent_tool_hashes.pop(0)
   ```
5. **Apply the same pattern** in `rlm_optimized/rlm_engine_optimized.py` in the `_handle_step()` method around **L3106** of `tui_app.py` or the equivalent engine loop.
6. **Reset** `_recent_tool_hashes` at the start of each new user message.
7. **Test:** Simulate 3 identical `READ_FILE` tool calls in sequence and verify the third is blocked with a redirect prompt.

### - [x] Task 19: Write/Edit Gate Validation Hardening
* **Issue:** Despite existing validation gates, 7B models still produce invalid syntax that passes the current checks but fails at runtime (e.g., valid Python AST but broken imports, semantically invalid JSON schemas).
* **Current Implementation:** `_fast_syntax_check()` (L846) and `_check_compile()` (L986) already run pre-write validation: Python AST compile, JSON parse, and JS/TS bracket balance checks. These are invoked at L1070-1083 (WRITE_FILE) and L2437 (batch writes).
* **Proposed Fix:** Harden existing gates: add import resolution checks for Python, schema validation for JSON config files, and extend JS/TS checking beyond bracket balance to include `node --check` or `esbuild --bundle` dry-runs where available. Also ensure EDIT_FILE path (L1341+) always runs validation on the final merged content.
* **Improvement Rate:** 6 / 10
* **Files Linked:** [core/tools/implementations.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/tools/implementations.py)

#### Implementation Steps
1. **Open** `core/tools/implementations.py`, locate `_validate_and_format()` at **L1046**.
2. **After the existing `_check_compile()` gate** at L1082-1091, add an **import resolution check** for Python files:
   ```python
   # 3b. Import resolution check (Python only)
   if filename.endswith('.py'):
       import_err = _check_imports(content, filename, project_root)
       if import_err:
           return ("error", f"Warning: {import_err}. File written but may have import issues.")
   ```
3. **Create `_check_imports()`** function:
   ```python
   def _check_imports(content: str, filename: str, project_root: str = "") -> Optional[str]:
       import ast
       try:
           tree = ast.parse(content)
       except SyntaxError:
           return None  # Already caught by _check_compile
       for node in ast.walk(tree):
           if isinstance(node, ast.Import):
               for alias in node.names:
                   if alias.name.startswith('.'):  # relative imports are OK
                       continue
           # Only flag obviously broken stdlib imports, not third-party
       return None
   ```
4. **For EDIT_FILE** path at **L1341**, after `_parse_diff_block()` succeeds and the merged content is built, call `_validate_and_format()` on the **final merged content** before writing to disk.
5. **For JSON files**, add schema structure validation in `_check_syntax()`:
   ```python
   if ext == '.json' and content.strip():
       try:
           data = json.loads(content)
           if isinstance(data, dict) and not data:
               return "⚠️ Warning: Empty JSON object"
       except json.JSONDecodeError as e:
           return f"⚠️ JSON syntax error at line {e.lineno}: {e.msg}"
   ```
6. **Test:** Write a Python file with `import nonexistent_module_xyz` and verify the warning is returned (not a hard block). Write invalid JSON and verify it's blocked.

---

## 🔴 Hard Difficulty

### - [x] Task 1: Context Degradation on Multi-File Edits
* **Issue:** When the model attempts to modify multiple files in a single turn, the context matching tags get corrupted, causing parser failures.
* **Current Implementation:** Multiple `EDIT_FILE` blocks are parsed and applied in a single turn, confusing the 7B model.
* **Proposed Fix:** Rewrite the engine to enforce sequential single-file edits, executing one file change per turn cycle.
* **Improvement Rate:** 8 / 10
* **Files Linked:** [core/execution/run_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/run_harness.py), [context-manager-cli/src/context_manager/cli/main.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/context-manager-cli/src/context_manager/cli/main.py), [rlm_optimized/rlm_engine_optimized.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/rlm_engine_optimized.py)

#### Implementation Steps
1. **Open** `context-manager-cli/src/context_manager/cli/main.py`, locate the chain loop at **L668-706**.
2. **Add a per-turn file edit counter** in the chain loop:
   ```python
   files_edited_this_turn: set[str] = set()
   ```
3. **After each tool execution**, if the tool was `WRITE_FILE` or `EDIT_FILE`, add the file path to the set:
   ```python
   if tool_name in ("WRITE_FILE", "EDIT_FILE"):
       files_edited_this_turn.add(tool_args.get("path", ""))
       if len(files_edited_this_turn) >= 2:
           # Inject constraint for next LLM turn
           feedback_msg = (
               "You have modified multiple files this turn. "
               "STOP editing and verify your changes with tests before continuing."
           )
           break  # Force a new LLM turn cycle
   ```
4. **Add a system prompt directive** in `core/prompts/system.py` under `PHASE_PROMPTS["code"]`:
   ```python
   "- ONE FILE PER TURN: Modify at most one file per turn cycle. After writing/editing a file, stop and verify."
   ```
5. **In `rlm_optimized/rlm_engine_optimized.py`**, apply the same counter in the `_handle_step()` method.
6. **In `core/execution/run_harness.py`**, add the same single-file-per-turn enforcement in the harness runner loop.
7. **Test:** Simulate a turn with 2 `WRITE_FILE` calls and verify the second triggers a break with the feedback message.

### - [x] Task 16: Lack of Visual Outcome Validation
* **Issue:** Edits to canvas games, layouts, or web components might render with visual defects or overlap despite passing unit tests.
* **Current Implementation:** Engine relies purely on text-based feedback loops.
* **Proposed Fix:** Integrate Playwright screenshot capture in the feedback loop, passing structural layout metrics or screenshot hashes to a visual critique prompt.
* **Improvement Rate:** 8 / 10
* **Files Linked:** [core/execution/web_inspector.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/web_inspector.py), [core/execution/feedback_loop.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/feedback_loop.py)

#### Implementation Steps
1. **Open** `core/execution/web_inspector.py`, locate the `inspect()` method at **L182**.
2. **Add a screenshot capture step** after the DOM snapshot extraction:
   ```python
   async def capture_screenshot(self, url: str, output_path: str) -> Optional[str]:
       """Capture a PNG screenshot via Playwright and return the file path."""
       try:
           from playwright.async_api import async_playwright
           async with async_playwright() as p:
               browser = await p.chromium.launch(headless=True)
               page = await browser.new_page(viewport={"width": 1280, "height": 720})
               await page.goto(url, timeout=10000)
               await page.wait_for_load_state("networkidle")
               await page.screenshot(path=output_path)
               await browser.close()
               return output_path
       except Exception:
           return None
   ```
3. **Add a layout metrics extractor** that computes element overlap and overflow from the DOM:
   ```python
   async def _check_layout_issues(self, page) -> list[str]:
       issues = []
       # Check for elements overflowing viewport
       overflow_els = await page.evaluate('''
           Array.from(document.querySelectorAll('*')).filter(el => {
               const r = el.getBoundingClientRect();
               return r.right > window.innerWidth || r.bottom > window.innerHeight * 2;
           }).map(el => el.tagName + '.' + el.className).slice(0, 5)
       ''')
       if overflow_els:
           issues.append(f"Overflow: {overflow_els}")
       return issues
   ```
4. **Open** `core/execution/feedback_loop.py`, locate `ExecutionFeedbackLoop` at **L144**.
5. **Add a visual validation step** in the post-edit feedback path:
   ```python
   async def _visual_check(self, html_path: str) -> Optional[str]:
       inspector = WebOutcomeInspector()  # from web_inspector.py
       result = await inspector.inspect(f"file://{html_path}")
       if result and result.get("layout_issues"):
           return f"Visual issues detected: {result['layout_issues']}"
       return None
   ```
6. **Trigger** `_visual_check()` after any WRITE_FILE to `.html`, `.css`, `.jsx`, or `.tsx` files.
7. **Test:** Create a simple HTML file with intentional overflow and verify the layout checker catches it.

### - [x] Task 17: Safe Checkpoints and Candidate Branching
* **Issue:** Experimental code edits can corrupt the user's workspace, and restoring files manually or via git resets risks losing local modifications.
* **Current Implementation:** Autonomous harness applies git restores blindly on failure.
* **Proposed Fix:** Implement dynamic local git candidate branching before applying code modifications, automatically committing or clean-reverting depending on test suite outcomes.
* **Improvement Rate:** 9 / 10
* **Files Linked:** [core/execution/autonomous_harness.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/core/execution/autonomous_harness.py)

#### Implementation Steps
1. **Open** `core/execution/autonomous_harness.py`, locate `_git_revert()` at **L685**.
2. **Add a new method** `_git_create_checkpoint()` above `_git_revert()`:
   ```python
   def _git_create_checkpoint(self, task_id: str) -> Optional[str]:
       """Create a checkpoint branch before applying experimental edits."""
       branch_name = f"torchlight/checkpoint/{task_id[:8]}"
       try:
           subprocess.run(
               ["git", "stash", "push", "-m", f"torchlight-pre-{task_id}"],
               cwd=self.config.project_root, capture_output=True, timeout=10
           )
           subprocess.run(
               ["git", "checkout", "-b", branch_name],
               cwd=self.config.project_root, capture_output=True, timeout=10
           )
           subprocess.run(
               ["git", "stash", "pop"],
               cwd=self.config.project_root, capture_output=True, timeout=10
           )
           return branch_name
       except Exception:
           return None
   ```
3. **Add a method** `_git_commit_checkpoint()` for successful edits:
   ```python
   def _git_commit_checkpoint(self, task_id: str, message: str) -> bool:
       try:
           subprocess.run(["git", "add", "-A"], cwd=self.config.project_root, timeout=10)
           subprocess.run(
               ["git", "commit", "-m", f"[torchlight] {message}"],
               cwd=self.config.project_root, capture_output=True, timeout=10
           )
           return True
       except Exception:
           return False
   ```
4. **Add a method** `_git_revert_to_main()` for failed edits:
   ```python
   def _git_revert_to_main(self, original_branch: str = "main") -> bool:
       try:
           subprocess.run(
               ["git", "checkout", original_branch],
               cwd=self.config.project_root, capture_output=True, timeout=10
           )
           return True
       except Exception:
           return False
   ```
5. **Integrate into `_run_epoch()`** (around **L471**):
   - Before task execution: `checkpoint = self._git_create_checkpoint(task.id)`
   - After tests pass: `self._git_commit_checkpoint(task.id, task.description)`
   - After tests fail: `self._git_revert_to_main(original_branch)`
6. **Add a field** to `HarnessConfig` at **L62**: `use_candidate_branches: bool = False`
7. **Guard** all branching calls with `if self.config.use_candidate_branches:`.
8. **Test:** Add a test in `core/tests/test_autonomous_harness.py` that creates a checkpoint, makes a change, reverts, and verifies the working tree is clean.
