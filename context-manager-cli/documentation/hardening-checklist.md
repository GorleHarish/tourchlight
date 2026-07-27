# Torchlight Hardening Checklist

Practical post-v3 hardening checklist focused on correctness, stability, and long-session reliability.

Related docs:
- [Architecture](architecture.md)
- [Excellence Roadmap](excellence-roadmap.md)

## Purpose

This document tracks verification work that should happen regardless of bigger roadmap items. It is about making the current architecture dependable, not redesigning it.

Focus areas:
- runtime stability
- provider and model truthfulness
- small-model efficiency
- process hygiene
- memory durability

## Already Completed

The following hardening items are already in place:

- tests cover the tool registry, phase detection, token counter, and memory models
- tests cover deterministic slash-command routing for `/read`, `/write`, `/edit`, `/run`, `/git`, and `/memory`
- tests cover invalid `/write` and `/edit` forms
- execution-policy routing exists for explicit safe requests
- working-set construction is explicit and status-visible
- provider/model truth is exposed across CLI health output and phase detection
- failure-classified retry status and stronger stop/cancel handling are in place

## Highest-Risk Areas

1. Runtime-only errors that static typing misses.
2. Efficiency regressions on 3B-7B local models.
3. Stale development processes after repeated relaunches.
4. Hidden mismatches between displayed commands and deterministic runtime behavior.

## Checklist

### 1. Slash Command Verification

Keep checking:
- every command exposed by `/context/commands` has deterministic routing or an explicitly UI-only behavior
- malformed command input returns a clean user-facing error
- command descriptions match actual required syntax

Recommended next step:
- extend unit coverage for every slash command parse path, including invalid payload cases

### 2. Runtime Hardening

Keep checking:
- touched modules compile cleanly
- targeted tests cover the agent coordinator, phase detection, and tool registry
- background exceptions surface as one readable error instead of noisy cascades

Recommended next steps:
- add startup self-checks for imports, prompt loading, and provider reachability

### 3. Process Hygiene

Keep checking:
- relaunches do not leave stale terminal processes behind

Recommended next step:
- expose lightweight process status in CLI output

### 4. Provider and Model Verification

Keep checking:
- LM Studio and Ollama model discovery works at startup
- the terminal output always reflects active model state accurately
- selected model, recommended model, and actual active model do not silently diverge

Recommended next steps:
- add a provider health check with connection test and model refresh

### 5. Local-Model Efficiency

Keep checking:
- chain depth limits are honored consistently
- retrieval does not overfill 4k-8k contexts
- tool outputs remain bounded
- deterministic routes bypass unnecessary freeform reasoning

Recommended next step:
- formalize small-model presets that tune runtime behavior beyond just token limits

### 6. Context-Rot and Memory Durability

Keep checking:
- needles survive compression
- needles survive session save and load
- memory objects are retrieved in later relevant turns
- context pressure UI reflects real runtime state
- compression events appear in activity and context views

Recommended next steps:
- add a replay-style long-session fixture
- add a richer memory inspector for needles, objects, compression history, retrieval hits, and per-turn working-set composition

### 7. Retry And Cancel Semantics

Keep checking:
- failed tool steps emit a clear retry reason
- retries do not silently reuse the same strategy
- stop requests terminate running commands
- cancelled turns do not remain stuck in a busy state

Recommended next step:
- expose the latest retry classification and strategy history in a more inspectable way than a single status line

## Exit Criteria

This checklist is in good shape when:
- runtime failures are visible and classifiable
- small-model sessions stay within budget without feeling blind
- provider state is explicit instead of inferred
- long debugging sessions retain the right needles
- dev relaunches are clean and repeatable
