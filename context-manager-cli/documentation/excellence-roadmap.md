# Torchlight Excellence Roadmap

Longer-horizon roadmap for making Torchlight feel closer to top-tier coding agents while staying strong on local models.

Related docs:
- [Architecture](architecture.md)
- [Hardening Checklist](hardening-checklist.md)

## Goal

Make Torchlight feel much closer to Claude Code and Codex quality without depending on large hosted models. The strategy is software-heavy: move more structure, routing, recovery, and working-set control into the runtime.

## Design Principle

For constrained local models, agent quality comes from moving non-essential cognition out of the model and into the system.

That means Torchlight should:
- route obvious intents deterministically
- build the smallest useful working set for each turn
- preserve exact technical needles across long sessions
- recover from weak outputs automatically
- make action selection and retries visible

## Target Quality Tiers

### Tier A: Constrained local mode

For 3B models and 4k-8k contexts.

Expected behavior:
- deterministic routing
- aggressive working-set control
- bounded tool output
- shallow tool chains
- strong interception of weak-model outputs

### Tier B: Balanced local mode

For 7B models and 8k-16k contexts.

Expected behavior:
- broader retrieval
- deeper troubleshooting loops
- more flexible planning
- richer tool use without losing transparency

### Tier C: Strong local mode

For larger-context local setups.

Expected behavior:
- same architecture
- wider budgets
- deeper tool chains
- richer retrieval and planning

The product should stay architecturally consistent across all tiers rather than becoming a different system for stronger hardware.

## Current Strengths

Torchlight already has:
- a layered prompt stack in [prompts.py](../../context-manager-cli/src/context_manager/prompts.py)
- hierarchical memory in [manager.py](../../context-manager-cli/src/context_manager/memory/manager.py)
- a structured runtime in [cli/main.py](../../context-manager-cli/src/context_manager/cli/main.py)
- deterministic slash-command routing in [tools/core.py](../../context-manager-cli/src/context_manager/tools/core.py)
- local provider support for LM Studio and Ollama

The roadmap is about tightening and extending these strengths, not replacing them.

## P0: Highest-Leverage Work

### 1. Execution Policy Router

Add a pre-generation execution router that can classify requests into modes such as:
- direct command
- surgical read
- surgical edit
- test or debug loop
- documentation verification
- freeform reasoning

Why it matters:
- obvious intents should bypass expensive open-ended reasoning
- small models need more deterministic guidance

Likely touchpoints:
- [cli/main.py](../../context-manager-cli/src/context_manager/cli/main.py)

Status:
- implemented in a first practical form

### 2. Explicit Working-Set Builder

Build the prompt from an explicit, budget-aware working set:
- current task
- active file
- flashlight hits
- top needles
- top memory objects
- most relevant recent tool result
- compact state summary

Why it matters:
- prompt assembly becomes inspectable and tunable
- 4k mode stops paying for irrelevant baggage

Status:
- implemented in a first practical form with visible working-set status and Context-pane visibility

### 3. Stronger Action Extraction

Improve interceptors that can convert weak-model prose into real actions when confidence is high:
- shell suggestion to `RUN_COMMAND`
- code block plus file cue to `WRITE_FILE`
- explicit replacement language to `EDIT_FILE`
- verification language to `VERIFY`

Why it matters:
- weaker local models often describe the action instead of taking it
- the runtime can salvage those turns safely

### 4. Provider and Model Truth Model

Make provider state first-class and explicit:
- provider
- endpoint
- selected model
- recommended model
- active model
- reason for any mismatch

Why it matters:
- the user should never have to guess what model actually answered

Status:
- implemented in a first practical form across CLI phase detection, health output, and UI badges

### 5. Failure-Classified Retries

Classify failures before retrying:
- provider unreachable
- model missing
- parse failure
- no relevant context
- command failure
- tool timeout
- ambiguous task

Why it matters:
- retries should explain what changed
- repeated identical failures should stop

Status:
- implemented in a first practical form with failure classification, retry strategy updates, and stronger cancel behavior

## P1: Important Follow-On Work

### 1. Runtime Presets for Small Models

Add full runtime presets such as:
- `3B Fast`
- `3B Surgical`
- `7B Balanced`
- `7B Debug`

Each preset should tune more than token count:
- chain depth
- recent window
- summary trigger
- retrieval count
- beam size
- tool result budget
- interception aggressiveness

### 2. Richer Memory Inspection

Expose inspectable memory internals:
- top needles
- memory objects
- retrieval hits
- compression history
- current working-set allocation

This is now the most important follow-on area, because the runtime has become more structured than the UI surfaces currently reveal.

Recent progress:
- the CLI now shows the latest working set and retry strategy
- a short rolling history is visible in `/status`

Remaining gap:
- inspection is still summary-level rather than full per-turn drill-down

### 3. Better Verification Loops

Extend the `DOC_SEARCH` and `WEB_VERIFY` pattern into a stronger correctness loop:
- verify before writing framework-heavy code
- surface verification confidence in activity
- route “not found” cases into authoritative docs automatically

### 4. Better Activity Semantics

Make activity more legible:
- show selected execution policy
- show retry reason and attempt number
- show whether a tool action was model-emitted or interceptor-promoted

Part of this is already landed, but it still needs deeper inspection surfaces and better history than a single live status line.

## P2: Longer-Horizon Upgrades

### 1. Smarter Retrieval

Keep flashlight as the fast default, but explore:
- richer symbol scoring
- stronger recency weighting
- optional semantic retrieval for large repos

### 2. Adaptive Prompt Compression

Make prompt assembly adapt more aggressively to:
- model size
- task shape
- failure class
- current context pressure

### 4. Terminal UX Polish

Continue improving the agent feel in the terminal:
- clearer active model truth
- more inspectable context assembly
- better long-session navigation
- cleaner slash command and tool output coordination

## Success Criteria

The roadmap is succeeding when Torchlight:
- spends fewer tokens to solve the same tasks
- routes obvious requests without model confusion
- retains the right technical needles deep into long sessions
- recovers from weak local-model output instead of exposing it directly to the user
- makes its internal decisions visible enough that power users can trust and tune it
