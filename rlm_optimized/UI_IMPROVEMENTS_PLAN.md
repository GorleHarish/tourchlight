# UI Improvements Plan — Industry-Standard Coding Agent UI

**Target:** `rlm_optimized/tui_app.py` + `rlm_optimized/tui_app.tcss` (Torchlight Codex IDE)
**Goal:** Evolve the existing terminal IDE into a UI matching industry-standard coding agents
(Claude Code, Cursor, VS Code Copilot Chat, Aider, OpenCode) without changing the agent engine.

---

## 1. Current State Audit

### What exists today (`tui_app.py` — 2,684 lines)

| Region | Location | Notes |
|---|---|---|
| HUD header | `compose()` L970–981 | Badges + mode/model/compact/help buttons |
| Explorer sidebar | L985–1003 | `DirectoryTree` (`#file-tree`) + health/plan `Collapsible`s |
| Agent split pane | L1006–1024 | `#chat-container` (VerticalScroll), `#user-input` `TextArea`, send btn, spinner |
| Telemetry bar | L1027–1028 | `#context-meter-bar` — plain text, no progress bar |
| Bottom nav dock | L1031–1035 | SHELL / CONTEXT / LOGS / SYS buttons |
| Streaming | L1919–1989 | `Static` text inside a "💭 Thinking…" `Collapsible`; tool-call parsed via regex |
| Step display | L1993–… | Plain `Static` lines; tool actions rendered as inline text |
| Approval flow | `ApprovalModal` L121, `_handle_approval` L2484 | Shows raw args, **no diff preview** |
| Modals | L232–789 | FolderPicker, ModelPicker, CopySelection, SessionModePicker, FileAction, AgentStatus, ShortcutsHelp |
| Responsive | `on_resize` L1669 | Toggles `narrow-terminal` / `short-terminal` classes |
| Tests | `core/tests/test_tui_plan_panel.py` | Validates `_build_plan_text` output — **keep this logic intact** when refactoring |

### Dead / broken code to resolve

- **Tabbed editor split pane is skeleton-only.** CSS for `#editor-split-pane`, `#tab-bar-header`,
  `#tab-buttons-container`, `#editor-content-area`, `#active-editor-view`, `#toggle-split-btn`
  exists (`tui_app.tcss` L57–143) but is **not composed**. `open_file_tab` L1045,
  `close_file_tab` L1103, `_refresh_editor_split_view` L1114 (no-op), `on_toggle_split_btn` L1140
  reference widgets that don't exist. → **Decide: implement fully or remove** (Phase 5).
- **Dead CSS selectors** for `#sidebar`, `#status-bar`, `#status-left/right`, `#meta-panel`,
  `#shortcuts-panel`, `#engine-btn-bar-*` — no matching compose. Clean up in Phase 0.
- **Hardcoded `#000000`** in `tui_app.tcss` L177/L182 violates the theme-variable rule. Fix.

### Rendering gaps vs. industry standard

1. Chat is **plain `Static` text** — no Markdown, no code-block syntax highlighting, no rich cards.
2. **Tool calls are inline strings** ("⚡ Preparing tool action…"), not structured cards with
   status, duration, and collapsible output.
3. **No inline diff rendering** for file edits; approval modal shows raw JSON args only.
4. **Context meter is text**, not a real progress/gauge bar.
5. **No command palette**, no slash-command autocomplete, no @-mention file hints.
6. File tree has **no git status decorations** (M/A/D/U).
7. Status info is scattered across HUD badges + sidebar panels; no single focused status bar.

---

## 2. Industry Benchmark

| Agent | Signature UI patterns to adopt |
|---|---|
| **Claude Code** | Message transcript; collapsible *thinking*; tool calls as inline list items with ✓/status; per-step cost/token; approval with diff |
| **Cursor / Windsurf** | Git-aware file tree, diff review (accept/reject), command palette (Ctrl+K), agent mode, tabbed editor |
| **VS Code Copilot Chat** | Markdown-rendered responses, code-block copy button, diff accept, clickable file references |
| **Aider** | Git-backed diffs, `/command` autocomplete, model switch, read-only vs. editable file states |
| **OpenCode** | Tool-call cards in transcript, composer parts, slash commands, status bar w/ token & cost counters |

**Common denominator (the "industry standard" bar):**
- Transcript = structured cards, not raw text. Every agent activity is a card: *message, thinking,
  tool call, diff, error, checkpoint*.
- Keyboard-first. Everything reachable without a mouse; palettes for command discovery.
- Streaming is progressive and live (status, tokens/sec, cursor).
- Approval safety shows the *actual change* (diff) before the action.
- One consolidated, glanceable status bar (model, phase, context %, tokens, TPS, errors).
- Narrow-terminal graceful degradation.

---

## 3. Design Principles (non-negotiable)

1. **CSS-first, theme-variable only.** All styling in `.tcss`/`CSS` class attributes; zero
   `styles.set()`; zero hardcoded `#hex`. Reference `$primary`, `$surface`, `$error`, etc.
2. **Cards over strings.** Each agent activity is a structured widget. Color encodes status
   (running/success/error/needs-approval).
3. **Zero engine change.** UI reads `engine.on_step` / `on_token` / `on_status_change` /
   `approval_fn` / `solve_async`; those APIs stay stable.
4. **Zero LLM context overhead.** All rendering is client-side. Never inject file/diff content
   into the model context for the sake of the UI.
5. **Lazy + bounded DOM.** `Lazy()`/`Reveal()` for non-critical panels; keep the 120-child cap
   on the transcript (replace with virtualized `ListView` if needed).
6. **Keyboard-first + discoverable.** Every feature bound to a key shown in Footer; palette for
   everything else.
7. **Responsive.** `@media`/class toggles collapse sidebar & dock on narrow/short terminals.
8. **Live streaming UX.** Tokens appear as they arrive; tool cards flip from *running* → *done*.

---

## 4. Target Architecture (widget extraction)

The 2,684-line `tui_app.py` is past maintainable size. Extract per-widget modules (each with its
own optional `.tcss`) while keeping `TorchlightApp` as the composition root:

```
rlm_optimized/
├── tui_app.py              # App shell: compose, bindings, engine wiring (shrinks a lot)
├── tui_app.tcss            # Shell + responsive rules only
└── tui_widgets/
    ├── __init__.py
    ├── transcript.py       # TranscriptView — Markdown cards, streaming, scroll mgmt
    ├── thinking_block.py   # Collapsible thinking per step
    ├── tool_card.py        # ToolCallCard — name, params, status, timing, output
    ├── diff_view.py        # DiffView — unified diff with add/del/context coloring
    ├── command_palette.py  # CommandPalette (ModalScreen) — fuzzy command search
    ├── status_bar.py       # StatusBar — model, phase, context gauge, tokens, TPS, errors
    ├── file_tree.py        # GitFileTree — DirectoryTree + git status decorations
    ├── approval.py         # ApprovalModal v2 — diff-preview + args summary
    ├── editor_pane.py      # TabbedEditor — (Phase 5)
    └── tui_widgets.tcss    # Per-widget styles (or per-file .tcss)
```

Re-export nothing from `core/` that changes behavior. Keep `_build_plan_text` /
`_build_system_health_text` / `_build_context_progress_text` **pure helpers** so
`test_tui_plan_panel.py` keeps passing (move + re-import if refactored).

---

## 5. Phased Roadmap

> Phases are independently shippable. Order = dependency + risk-ordered. Each phase ends green:
> `pytest core/tests/` + manual smoke run of `./tui.sh`.

**Status: Phase 0 ✅ done** — dead CSS removed, hardcoded `#000000` replaced with the built-in
warning Button variant's theme-computed contrast, `tui_widgets/` package created with
`format.build_plan_text` (verbatim move of `_build_plan_text`), dead `#sidebar`/`#meta-panel`/
`#context-progress-badge` updates removed, `test_tui_plan_panel.py` now exercises the real helper
and was hardened for Textual 8.2.8 (CSS parse signature + modal-compose within `run_test()`).

**Status: Phase 1 ✅ done** — transcript is now structured cards. New
`tui_widgets/transcript.py` (`MessageCard` Markdown turn cards with role label + timestamp +
word/token footer, `StreamingView` live turn with `▍` cursor + tps/tokens/latency meta,
`TranscriptView` = the `#chat-container` scroll container with a FIFO-tracked 120-child cap)
and `tui_widgets/thinking_block.py` (`thinking_block()` per-step `Collapsible`, `Static`
fallback). `tui_app.py`: user turns and final answers render as `MessageCard`s, streaming goes
through `StreamingView` (cheap `Static` body during the stream, Markdown on completion),
per-step reasoning uses `thinking_block`. Also fixed a latent `NameError`: `re` was used in
`_append_token` but never imported — any `<tool_call>` silently froze streaming. New tests:
`core/tests/test_tui_transcript_widgets.py` (7 tests incl. an app-wiring smoke that drives the
real `MessageCard`/`StreamingView` path). Full suite: 238 passed; ruff clean on new files.

**Status: Phase 2 ✅ done** — every tool call is a status-aware card. New
`tui_widgets/tool_card.py` (`ToolCallCard` with risk-tier icon + AUTO/CONFIRM/REVIEW badge
(from `core/tools/classification`), target, elapsed ms, status glyph, collapsible params +
truncated output — auto-expanded on error/denied, risk re-derivation when `RUN_COMMAND` args
escalate) and `tui_widgets/trajectory_rail.py` (`TrajectoryRail` — a collapsed 4-col
status-colored dot rail pinned to the right of the transcript; dots flip running→ok/error/
denied, FIFO-capped at 80, tooltip shows the tool name, hidden on narrow terminals).
`tui_app.py`: `<tool_call>` stream markers mount a single pending card + rail dot
(`_ensure_pending_tool_card`), `_handle_step` completes both; non-streaming engines get a
fresh completed card + dot; `action_clear` resets the rail. New tests:
`core/tests/test_tui_tool_cards.py` (7 tests incl. risk escalation + app-wiring smoke) and
`core/tests/test_tui_trajectory_rail.py` (7 tests incl. pruning + app-wiring smoke). One
pre-existing assertion bug in the denied-status test fixed (`frozenset` membership). Full
suite: 254 passed + 1 unrelated web-inspector network flake.

**Status: Phase 3 ✅ done** — inline diffs + approval diff preview. New
`tui_widgets/diff_view.py`: pure `render_unified_diff(old, new, path=…)` (`difflib`, no Rich/
Textual → trivially unit-tested), `diff_summary` (`+N −M` stat), `diff_markup` (colored Rich
lines, 80-line cap), `build_diff_preview(tool_name, args, project_root, old_text=…)` which reads
disk state and reconstructs the before/after faithfully (handles pre-edit and post-edit disk
states for `EDIT_FILE`, plus `CODE_FILE_WRITE`), and the `DiffView` card widget. `tui_app.py`:
`ApprovalModal` gained an optional `⬇ DIFF PREVIEW` section (scrollable, max 120 lines) shown
for diffable writes; `_handle_approval` snapshots pre-write file contents into
`self._prewrite_snapshots` (engine always routes CONFIRM/REVIEW writes through approval, so the
snapshot captures the true "before"); `_handle_step` pops the snapshot and mounts a `DiffView`
card under successful WRITE/EDIT steps. Zero LLM context involvement. New tests:
`core/tests/test_tui_diff_view.py` (16 tests incl. snapshot override, CODE_FILE_WRITE, modal
diff rendering, app-wiring smoke). Full suite: 271 passed; ruff clean on all new files.

### Phase 0 — Baseline cleanup (foundation)
**Objective:** remove dead code, enforce CSS discipline, lock engine API contract.

- Delete dead CSS selectors (`#sidebar`, `#status-bar`, `#meta-panel`, `#engine-btn-bar-*`,
  `#shortcuts-panel`); replace hardcoded `#000000`.
- Decide fate of editor-split CSS skeleton: park it until Phase 5 (leave selectors but annotate),
  or remove now.
- Add a widget-extraction skeleton (`tui_widgets/` package + empty `.tcss`) and move
  `_build_*` text helpers into a `tui_widgets/format.py`.
- Update `test_tui_plan_panel.py` imports accordingly (logic unchanged).
- **Acceptance:** lint clean (`ruff check rlm_optimized/`), all tests pass, app boots.

### Phase 1 — Rich transcript & streaming (highest impact) ✅ done
**Objective:** match the "transcript of cards" bar. → `tui_widgets/transcript.py`,
`thinking_block.py`.

- Replace plain `Static` chat rendering with **`Markdown`** widgets for user & assistant turns
  (code blocks get syntax highlighting for free via Textual's `Markdown`).
- **Thinking block per step:** reuse `Collapsible` (`💭 Thinking…`) but instantiate one per step
  and auto-expand while streaming, auto-collapse on completion.
- **Streaming widget upgrade:** render partial output as live `Markdown` (progressive), keep the
  `<tool_call>` regex-based *"preparing tool"* hint but emit it as a structured pending card
  instead of inline text.
- **Message chrome:** wrap turns in `.message-card` (border-left accent, subtle background,
  `:hover` highlight). Add a timestamp + token/char counter footer to assistant cards.
- Cap DOM: keep 120-child pruning; swap to `ListView` virtualization if DOM stays hot.
- **Acceptance:** markdown/headers/code blocks render; streaming is smooth; test harness.

### Phase 2 — Tool call cards & trajectory timeline ✅ done
**Objective:** every tool call is a status-aware card. → `tui_widgets/tool_card.py`.

- Render each `Step`'s tool call as a **ToolCallCard**:
  - Header row: tool icon (per-risk-tier color from `core/tools/classification.py`), tool name,
    risk badge (AUTO/CONFIRM/REVIEW), elapsed ms, status glyph (⏳ running / ✓ ok / ✗ error).
  - Params section: `Collapsible` showing a compact key/value summary (path, cmd, query).
  - Output section: `Collapsible` with truncated output (cap ~40 lines, escape markup).
- Wire `engine.on_step` to append cards; on a later step referencing the same tool, mark prior
  card done instead of stacking "Preparing…" strings.
- Add a collapsed **trajectory rail** on the right edge (optional): dots colored by outcome.
  → done: `TrajectoryRail` (4-col status rail, FIFO-capped, hidden on narrow terminals).
- **Acceptance:** a 5-tool task shows 5 cards, each with status + timing + expandable output.
  → done (24 widget tests incl. rail).

### Phase 3 — Inline diffs & approval diff preview (safety UX) ✅ done
**Objective:** show *what changed* before and after. → `tui_widgets/diff_view.py`,
`approval.py`.

- `DiffView`: unified diff widget (new/old file pair, hunks with green/red/context lines,
  line numbers). Build a pure `render_unified_diff(old, new)` helper; unit-test it.
- **WRITE_FILE / EDIT_FILE steps** render a DiffView card in the transcript (compute via
  `difflib` against current file contents read from disk — UI layer only). → done.
- **ApprovalModal v2:** for CONFIRM/REVIEW file writes, show the diff preview inside the modal
  (scrollable) + concise risk line, keeping Allow/Deny + `y`/`n` bindings. For shell commands
  show the exact command with a highlighted exec summary. → done (diff preview section).
- **Acceptance:** approving a write shows the green/red change; deny path unchanged; tests for
  `render_unified_diff`. → done (16 tests incl. snapshot override + modal diff).

### Phase 4 — IDE shell polish
**Objective:** discoverability + glanceability. → `command_palette.py`, `status_bar.py`,
`file_tree.py`.

- **Command palette** (`ctrl+p`): fuzzy-search over all actions (bindings + slash commands +
  file open). Reuse existing `ModelPickerModal`/`ShortcutsHelpModal` building blocks.
  ⚠️ Do **not** bind anything else to `ctrl+p` — it is the standard palette key (Textual default
  and every IDE). "Compact Context" lives on `ctrl+n`; `ctrl+k` must stay free for the input
  widget (TextArea uses it to delete to end of line).
- **Slash-command autocomplete** in `#user-input`: on `/`, show a suggestion `ListView` below
  the TextArea (fuzzy filter on `_handle_slash_command` L1687 names); Enter accepts, Esc dismisses.
  Optionally `@`-mention file completion from the tree.
- **Consolidated status bar** (replace HUD badge sprawl + text meter): one row →
  `model ▸ phase ▸ [context progress bar ████░ 62%] ▸ TPS ▸ tokens ▸ errors ▸ git branch`.
  Use a real proportional bar (fill = blocks based on fraction, colored `$warning`→`$error`).
- **Git-aware file tree:** decorate `DirectoryTree` entries with `M/A/D/U/??` from
  `git status --porcelain` (cheap, refreshed on write; cache invalidation only). Row prefix badges
  like VS Code.
- **Acceptance:** palette opens at `ctrl+p`; `/comp<Tab>` completes; context gauge renders as a
  bar; tree shows modified files.

**Status: Phase 4 ✅ done** — IDE shell polish. New `tui_widgets/command_palette.py`,
`status_bar.py`, `file_tree.py` (all pure helpers trivially unit-tested + thin Textual widgets,
CSS-first, theme vars only):

- **Command palette** (`Ctrl+P`): `CommandPalette(ModalScreen)` fuzzy-searches app bindings +
  slash commands + project files (prefix > substring > subsequence scoring; dot/vendor dirs
  excluded, capped at 200 files). Enter runs, Esc cancels, ↑/↓/Home/End navigate.
- **Prompt autocomplete**: `PromptTextArea(TextArea)` subclass turns Enter into submit (stock
  widget consumes it) and hooks `update_suggestion()` to compute `/cmd` + `@file` completions
  rendered in an `#input-suggestions` `ListView` below the input — Enter/Tab accept, Esc dismisses,
  ↑/↓ move highlight. Required overriding the `control` property on `SubmitRequested` for
  `@on(msg, "#id")` selector matching.
- **Consolidated status bar**: `StatusBar(Horizontal)` with 7 segments (phase + server,
  model, proportional context gauge `███░░ 62%` colored green→yellow→red, TPS, tokens, errors,
  git branch) replacing the old plain-text meter; `update_status_bar()` rewired via
  `_context_usage()` / `_git_branch()`. Responsive rules hide TPS/errors (narrow) and the
  gauge (very narrow) via CSS.
- **Git-aware file tree**: `GitFileTree(DirectoryTree)` decorates labels with `M/A/D/U/??` from a
  single `git status --porcelain` pass (`parse_git_status_porcelain` handles renames/quoted
  paths); `_populate_node` override renders per-node; nested-dir keys computed with
  `os.path.relpath` (DirectoryTree resolves `/var`→`/private/var`, which broke `Path.relative_to`).
  Refreshed on mount, `/cd`, WRITE/EDIT, and folder-open.
- New tests: `core/tests/test_tui_status_bar.py` (9), `test_tui_command_palette.py` (13),
  `test_tui_file_tree.py` (9) — 30 Phase-4 tests. Full suite: **301 passed**; ruff clean on all
  new/changed files. Headless smoke (palette open/filter/select, `/` suggestions, git-decorated
  tree, status bar) verified end-to-end.
- Also fixed a latent `repl_sandbox` bug: `REPLSandbox.execute` armed the 10 s `SIGALRM` timeout
  *before* the natural-language early-return, which skipped the `finally` that cancels it — the
  leaked timer later fired mid-suite and flaked unrelated TUI tests. The alarm is now armed only
  around `exec`.
- Post-Phase-4 bugfix: **duplicate plan entries in the plan panel**. Root cause was duplicate
  `- [ ]` lines *within* a single plan file (e.g. summary + detailed checklist, or repeated
  `UPDATE_TASK_GRAPH add_subtask`), not multi-file aggregation — `build_plan_text` reads only one
  source. `build_plan_text` (in `format.py`) now dedupes markdown/JSON tasks (normalized
  case-insensitive text, first occurrence wins) and sets `total` from the deduped list;
  `get_workspace_pending_tasks` (in `core/tools/task_helpers.py`) dedupes the same way so the
  engine verification gate matches the panel. 2 regression tests in
  `core/tests/test_tui_plan_panel.py`. Suite: **303 passed**; ruff clean on all changed files.

### Phase 5 — Tabbed editor split pane (implement or remove)
**Decision gate:** this is the largest single feature. Implement only if desired; otherwise delete
the skeleton to reduce maintenance surface.

- *Implement:* compose `#editor-split-pane` (left of chat, 3fr) with `#tab-bar-header`
  (scrollable tab buttons + close `×`), `#editor-content-area` hosting a read-only
  `TextArea`/`Static` with **syntax highlighting** (Rich `Syntax`, language by extension), live
  `on_node_selected` open, dirty-marker dot on tab, `ctrl+\` split toggle.
- *Remove:* drop `open_file_tab`/`close_file_tab`/`_refresh_editor_split_view`/toggle-split CSS
  and keep file-open → external editor (FileActionModal) as the flow.
- **Acceptance (if implement):** open file from tree → tab appears, content highlighted, close
  works, toggle split hides/shows; focus moves to editor.

### Phase 6 — Polish, a11y, performance
- Every interactive widget: `:focus`/`:hover`/`:disabled` rules (audit all Buttons).
- `@media (width < 80)` collapse sidebar; `(height < 24)` hide dock & telemetry.
- Theme audit across built-ins (`nord`, `gruvbox`, `solarized-*`, `coding-agent` custom if added).
- Upgrade `ShortcutsHelpModal` to grouped-by-category layout (keys / palette / slash commands).
- Perf: profile streaming update path; ensure `call_after_refresh` coalescing; consider
  `RichLog` for high-frequency token output instead of full `Markdown` re-render.

---

## 6. Verification Strategy

| Level | Command / Method |
|---|---|
| Unit | `pytest core/tests/` (keep `test_tui_plan_panel.py` green) |
| New unit tests | `render_unified_diff`, tool-card status transitions, palette filter, git-deco parsing |
| Lint | `ruff check core/ context-manager-cli/src/ rlm_optimized/` |
| Smoke | `./tui.sh` → start engine → run a multi-tool task → visually verify cards/diffs/status |
| Narrow terminal | resize to <80 cols → sidebar hides, chat takes 1fr |
| Theme sweep | `ctrl+t` through all themes → no unreadable contrast, no hardcoded hex regressions |

---

## 7. Non-Goals

- No changes to the agent engine, tool execution, approval *decision* logic, or model prompts.
- No context-budget changes — the UI must remain invisible to the LLM's token accounting.
- No web/browser UI (TUI stays terminal-only, per Torchlight's charter).
- No new dependencies beyond what Textual/Rich already provide (avoid e.g. heavy diff libs —
  `difflib` suffices).

---

## 8. Effort & Sequencing

| Phase | Effort | Notes |
|---|---|---|
| 0 Baseline | S | Unblocks everything |
| 1 Rich transcript | M | Biggest perceived value-per-effort — do first |
| 2 Tool cards | M | Depends on Phase 1 transcript slots |
| 3 Diffs + approval | M | Safety-critical; do before power-user features |
| 4 Shell polish | M | Palette + status bar + git tree |
| 5 Editor pane | L | Optional; gate on user need |
| 6 Polish | S–M | Continuous, fold into each phase's done-definition where possible |

**Recommended sequence:** 0 → 1 → 2 → 3 → 4 → 6, with 5 as a separately gated decision.
