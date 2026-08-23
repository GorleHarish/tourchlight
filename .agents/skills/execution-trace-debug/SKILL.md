---
name: execution-trace-debug
description: >
  Systematic execution-flow tracing debugger. Traces the actual runtime path
  through multi-component systems step-by-step — entry point → data preparation
  → processing loop → output rendering — to find where the chain breaks. Use
  when facing empty outputs, wrong behavior, silent failures, agentic loop
  issues, or any bug where multiple modules interact. Especially effective for
  async pipelines, LLM agent loops, TUI/CLI rendering, and multi-layer
  request→response flows. Invoke with "trace debug", "trace the flow",
  "execution trace", "follow the path", or when a bug spans 3+ files.
argument-hint: "[entry-point or symptom description]"
---

# Execution-Flow Tracing Debugger

You are a systems debugger who **never guesses**. You trace the actual runtime
execution path, one hop at a time, from entry point to observed symptom, until
you find the exact line where reality diverges from intent.

## Core Principle

```
DON'T READ CODE TO UNDERSTAND IT.
READ CODE TO TRACE WHAT ACTUALLY EXECUTES.
```

Understanding architecture is not debugging. Debugging is answering:
"Given input X, what exact sequence of function calls fires, what data flows
through each boundary, and where does the chain produce the wrong output?"

## When to Use

- **Empty or wrong output** after a seemingly correct operation
- **Silent failures** — no error, but wrong result
- **Multi-component bugs** — symptom is 3+ files away from cause
- **Agentic/LLM loop bugs** — model response → parsing → tool exec → re-injection
- **"It works sometimes"** — race conditions, state-dependent branches
- **Async pipeline issues** — streaming, callbacks, event loops
- **TUI/CLI rendering bugs** — data exists but display is empty or garbled

**DO NOT use for:**
- Single-file syntax errors (just read the error)
- Missing dependency (just install it)
- Clear type mismatch shown in traceback (just fix the type)

---

## The 7-Step Trace Protocol

### Step 1: Anchor the Symptom

Capture the **exact observable failure** — not what you think is wrong, what
you literally see.

```
SYMPTOM LOG:
- What happened:    [empty ANSWER card after 52s]
- What should have: [code block with snake game implementation]
- Inputs:           [prompt="continue building snake game", mode=Code]
- Observable state: [6 LLM calls, 7 steps, Qwen 2.5 Coder 3B]
```

**Rules:**
- Screenshot or exact terminal output — not your paraphrase
- Include timing, counts, model, mode, config — anything measurable
- If the user gave you a screenshot, read it literally

### Step 2: Map the Entry Point

Find the **exact function** that receives the user's input and starts the
pipeline. This is your tracing origin.

```
TRACE ORIGIN:
├── User types "continue building snake game"
├── → CLI: cli/main.py::chat_loop() receives input
├── → Engine: rlm_engine_optimized.py::process_user_input(msg)
└── → First decision point: _detect_phase(msg) → "code"
```

**How to find it:**
1. Search for the input handler (CLI entrypoint, TUI message handler, API route)
2. Follow the first function call that processes the raw input
3. Stop when you reach the first branching decision

**Anti-pattern:** Don't start from the error location and read backwards.
Start from the input and read forwards.

### Step 3: Trace Data Preparation

Before the main processing loop, the system prepares context. This is the
**#1 most common failure zone** — data gets lost, truncated, or malformed
before the core logic ever sees it.

```
DATA PREPARATION CHAIN:
├── _prepare_messages(user_msg, phase="code")
│   ├── system_prompt = get_phase_system_prompt("code")  ← check: is task context injected?
│   ├── l0_scratchpad = format_l0_scratchpad()           ← check: does it include goal/files?
│   ├── history = memory.get_recent(3)                   ← check: is previous context present?
│   └── token_budget = ctx_size * 0.85                   ← check: does prepared content fit?
└── messages[] = [system, l0, history..., user_msg]      ← check: correct order & format?
```

**What to look for:**
- **Missing injection**: Task context, memory, history not being added
- **Truncation**: Token budget cutting essential context
- **Wrong format**: Messages not matching model's expected chat template
- **Stale state**: Previous session's state leaking in or current state missing

### Step 4: Trace the Processing Loop

Follow the **main loop iteration by iteration**. For agentic systems, this is
the think→act→observe cycle. For request→response, this is the handler chain.

```
LOOP TRACE (iteration by iteration):
│
├── Iteration 1:
│   ├── LLM call → response = "Let me think about..."
│   ├── _parse_response(response)
│   │   ├── has_tool_call? → NO
│   │   ├── has_final_answer? → NO
│   │   └── classified as: "thinking"          ← HERE: what branch does this take?
│   └── action: increment thinking_count=1, continue loop
│
├── Iteration 2:
│   ├── LLM call → response = "I need to consider..."
│   ├── _parse_response → "thinking" again
│   └── action: thinking_count=2, continue loop
│
├── Iteration 3:
│   ├── thinking_count == MAX_THINKING_LOOPS (3)
│   ├── action: force_extract_answer(last_response)  ← HERE: what does this produce?
│   └── result: empty string ""                       ← ROOT CAUSE CANDIDATE
│
└── Post-loop:
    ├── answer = ""
    ├── _handle_final_answer("")  ← renders empty card
    └── SYMPTOM REPRODUCED ✓
```

**What to trace at each iteration:**
1. **Input to the step**: What data enters this iteration?
2. **Decision points**: Which branch does it take? Log the condition values.
3. **Output of the step**: What data exits? Is it correct?
4. **State mutations**: What global/shared state changes?

### Step 5: Trace the Output Path

Follow the result from the processing loop to the **final rendering**. The bug
might be in how the result is displayed, not how it's computed.

```
OUTPUT PATH:
├── engine returns: answer="<FINAL_ANSWER>code here</FINAL_ANSWER>"
├── sanitize_assistant_text(answer)
│   ├── strips <FINAL_ANSWER> tags  ← check: does this extract content or delete it?
│   └── result = "code here"
├── tui_app.py::_handle_step(result)
│   ├── creates AnswerCard widget
│   └── renders markdown
└── DISPLAYED TO USER
```

**Common output-path bugs:**
- Sanitizer strips the actual content along with wrapper tags
- Renderer receives correct data but wrong widget type
- Async rendering completes before data arrives (empty frame)
- Character encoding mangles the content

### Step 6: Identify the Divergence Point

You now have a complete trace. Find the **exact line** where actual behavior
diverges from intended behavior.

```
DIVERGENCE ANALYSIS:
├── Expected: _parse_response returns tool_call for WRITE_FILE
├── Actual:   _parse_response classifies all responses as "thinking"
├── WHY:      3B model doesn't emit <tool_call> tags, emits markdown code blocks
├── Divergence point: _parse_response() line 340, regex doesn't match model output
└── ROOT CAUSE: Parser expects <tool_call>JSON</tool_call>, model emits ```json\n{}```
```

**Test your root cause claim:**
- If I fix this one point, does the full trace produce correct output?
- Does this explain ALL observed symptoms, not just the primary one?
- Is this the **earliest** point of divergence, or is there an upstream cause?

### Step 7: Fix at the Divergence Point

Now — and ONLY now — implement the fix.

```
FIX SPECIFICATION:
├── File: core/tools/schemas.py:L340
├── Change: Add fallback regex for markdown JSON code blocks
├── Test: Send "continue building snake game" → expect WRITE_FILE tool call
├── Scope: Only this parser function, no architectural changes
└── Verify: Full trace produces correct output end-to-end
```

---

## Trace Documentation Template

Use this template to document your trace. It forces rigor.

```markdown
## Execution Trace: [Bug Title]

### Symptom
- Observed: [exact output/behavior]
- Expected: [what should happen]
- Inputs: [exact inputs, config, model, mode]

### Trace Path
1. **Entry**: [function(args)] → [what it returns/does]
2. **Preparation**: [what context is assembled]
3. **Loop iteration 1**: [input → decision → output]
4. **Loop iteration N**: [input → decision → output]
5. **Output**: [final rendering path]

### Divergence Point
- **Line**: [file:line_number]
- **Expected**: [what this line should produce]
- **Actual**: [what this line actually produces]
- **Why**: [mechanical explanation, not speculation]

### Root Cause
[One sentence: component X does Y because Z, but it should do W]

### Fix
[Minimal change at the divergence point]

### Verification
[How to confirm the fix resolves the full trace]
```

---

## Multi-Component Trace Patterns

### Pattern A: Request→Transform→Render Pipeline

Common in CLI/TUI apps, web servers, data processing.

```
TRACE TEMPLATE:
Input → [Validate] → [Transform] → [Process] → [Format] → [Render]
         ↑ check      ↑ check       ↑ check     ↑ check    ↑ check
         shape         mutation      logic        shape      display
```

At each `↑ check` point, verify:
- **Shape**: Is the data structure correct? (type, keys, length)
- **Content**: Are the values correct? (not empty, not stale, not truncated)
- **Timing**: Has this step completed before the next step reads it?

### Pattern B: Agentic Think→Act→Observe Loop

Common in LLM agent systems, autonomous pipelines.

```
TRACE TEMPLATE:
                    ┌─────────────────────────────────────┐
                    │                                     │
User Input → [Prepare Context] → [LLM Call] → [Parse Response]
                                                    │
                                    ┌───────────────┼───────────────┐
                                    ↓               ↓               ↓
                              [Tool Call]     [Thinking]      [Final Answer]
                                    │               │               │
                              [Execute Tool]  [Nudge/Loop]    [Render Output]
                                    │               │
                              [Inject Result]  [Check Limit]
                                    │               │
                                    └───→ [LLM Call] ←──┘
```

Trace each path separately. The bug is almost always in:
1. **Context preparation** (missing task injection)
2. **Response classification** (wrong branch taken)
3. **Loop termination** (force-extract produces empty result)

### Pattern C: Event-Driven / Async Pipeline

Common in TUI widgets, WebSocket handlers, stream processors.

```
TRACE TEMPLATE:
Event Emitted → [Handler Registered?] → [Handler Fires?] → [State Updated?] → [UI Refreshed?]
                 ↑ check binding         ↑ check timing     ↑ check mutation    ↑ check render
```

Async bugs are almost always:
1. **Handler not registered** (wrong event name, wrong lifecycle)
2. **Race condition** (handler fires before data ready, or after UI disposed)
3. **State mutation not triggering re-render** (missing reactivity)

---

## Trace Acceleration Techniques

### Targeted grep before reading

Don't read files top-to-bottom. Grep for the specific function/variable that
connects one component to the next.

```bash
# Find where user message enters the engine
grep -rn "process_user_input\|handle_message\|on_submit" --include="*.py"

# Find what calls the parser
grep -rn "_parse_response\|parse_response" --include="*.py"

# Find the rendering endpoint
grep -rn "AnswerCard\|_handle_step\|final_answer" --include="*.py"
```

### AST-first for large codebases

Use `SEARCH_AST` / `graphify query` before reading source:

```
graphify query "what calls _parse_response?"
graphify path "_parse_response" "AnswerCard"
```

This gives you the call chain without reading 500 lines of code.

### Instrument with breadcrumbs

When the trace is ambiguous, add temporary logging at each boundary:

```python
# Add at each trace point — remove after debugging
import sys
print(f"[TRACE] {__name__}:{func.__name__} | input={repr(data)[:200]}", file=sys.stderr)
```

**Rules for breadcrumbs:**
- Print to stderr (won't interfere with stdout pipelines)
- Truncate data to 200 chars (don't flood the log)
- Include module and function name (grep-friendly)
- Remove ALL breadcrumbs after the fix

---

## Hard Rules

1. **No fixes before completing Step 6.** If you haven't identified the
   divergence point, you don't have a root cause.

2. **One hop at a time.** Don't skip from entry point to error. Trace every
   intermediate function call.

3. **Verify data at boundaries.** Every time data crosses from one module to
   another, check its shape and content.

4. **Trace forwards, not backwards.** Start from the user's input, not from
   the error. Backward tracing misses silent data corruption.

5. **Document as you go.** If you can't write down the trace, you haven't
   actually traced it.

6. **The first divergence wins.** If you find the output is wrong at step 3,
   don't keep tracing to step 7. Fix step 3 first.

7. **Never speculate.** "I think this might be the issue" is not a trace
   result. "Line 340 returns '' because the regex doesn't match" is.

---

## Anti-Patterns (What This Skill Prevents)

| Anti-Pattern | What Happens | This Skill's Fix |
|---|---|---|
| **Shotgun debugging** | Change 5 things, hope one works | Trace to single divergence point |
| **Symptom patching** | Fix the rendering, miss the data bug | Trace from input to output |
| **Architecture astronaut** | Redesign the system to fix one bug | Fix at the exact divergence line |
| **Log reading** | Stare at logs hoping to spot the issue | Structured trace with boundary checks |
| **"I know this codebase"** | Skip tracing because you wrote it | Trace anyway — memory lies, code doesn't |
| **Depth-first rabbit hole** | Deep-dive one function for 30 min | One hop at a time, breadth across the chain |

---

## Example: Empty Answer Card After LLM Agent Loop

Full trace following this protocol:

```
SYMPTOM: Empty ANSWER card, 52s, 6 LLM calls, Qwen 3B, Code mode

ENTRY: tui_app.py::_on_submit("continue building snake game")
  → engine.process_user_input(msg)

PREPARATION: _prepare_messages()
  → system_prompt = CODE_PROMPT  ✓
  → l0_scratchpad = format_l0_scratchpad()  ← MISSING: no task context from previous turn
  → history = [] (first message in session)  ✓
  → messages = [system, l0, user_msg]  ✓ but l0 is thin

LOOP:
  iter 1: LLM → "I'll implement the snake game..." (no tool_call tag)
          _parse_response → classified as "thinking" (no <tool_call>, no <FINAL_ANSWER>)
          thinking_count = 1

  iter 2: nudge injected → "Please use tools to implement"
          LLM → ```json\n{"tool": "WRITE_FILE"...}```
          _parse_response → classified as "thinking" (regex expects <tool_call>, not ```)
          thinking_count = 2

  iter 3: thinking_count == MAX_THINKING_LOOPS
          force_extract_answer(last_response)
          → searches for <FINAL_ANSWER>...</FINAL_ANSWER> → not found
          → returns ""

OUTPUT: _handle_final_answer("") → AnswerCard("") → empty card

DIVERGENCE: _parse_response() line 340
  Expected: detect ```json tool call and execute it
  Actual:   only matches <tool_call> XML tags, misses markdown format

ROOT CAUSE: Parser has single-format assumption, 3B model emits alternative format

FIX: Add fallback regex in _parse_response for markdown JSON code blocks
```
