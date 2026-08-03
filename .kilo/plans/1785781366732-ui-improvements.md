# Plan: UI Improvements — Torchlight Codex IDE

**Scope:** Remaining work from `rlm_optimized/UI_IMPROVEMENTS_PLAN.md` Phases 5–6, plus bug fixes discovered during code review.

**Target:** `rlm_optimized/tui_app.py`, `rlm_optimized/tui_app.tcss`, `rlm_optimized/tui_widgets/`

---

## Decisions

- **Phase 5 (editor split pane): Implement, not remove.** The CSS skeleton and widget stubs (`open_file_tab`, `close_file_tab`, `_refresh_editor_split_view`) already exist. Removing them would delete working file-open infrastructure. Instead, compose the split pane and wire the tab bar.
- **Phase 6 (polish/a11y/performance): Break into two sub-tasks.** (6a) a11y and focus management; (6b) performance and streaming polish.
- **Bug fix: initialize `_show_plan_sidebar`** in `TorchlightApp.__init__` (currently missing, defaults to `True` via `getattr` fallback in `action_toggle_right_sidebar`).
- **Bug fix: make `_refresh_editor_split_view` functional** — it currently queries for `#tab-buttons-container` and `#editor-content-area` but does nothing with them.

---

## Task 1: Fix Latent Bugs (prerequisite)

1.1 In `TorchlightApp.__init__`, add `self._show_plan_sidebar = True`.
1.2 In `_refresh_editor_split_view`, implement tab-bar rendering:
    - Query `#tab-buttons-container` and `#editor-content-area`.
    - Clear the container, then for each entry in `self._open_tabs`, create a tab button (filename, close `×` on hover) and a corresponding content widget (read-only `TextArea` or `Static` with file content).
    - Activate the tab matching `self._active_tab_path`.
    - Bind tab button clicks to `_switch_tab` and close buttons to `close_file_tab`.
1.3 Run `ruff check rlm_optimized/` and `pytest core/tests/` to verify no regressions.

---

## Task 2: Phase 5 — Tabbed Editor Split Pane

2.1 In `tui_app.tcss`, remove the `/* PHASE 5 RESERVED */` comment block and promote the `#editor-split-pane`, `#tab-bar-header`, `#tab-buttons-container`, `#toggle-split-btn`, `#editor-content-area`, `#active-editor-view` selectors to active layout CSS.
2.2 In `TorchlightApp.compose()`, add the editor split pane to the `#main-ide-container`:
    - Left of chat (3fr): `#editor-split-pane` containing `#tab-bar-header` (scrollable tab buttons) and `#editor-content-area` (active tab content).
    - Right of chat (1fr): `#chat-container` + `#input-area` (existing).
    - Toggle button `#toggle-split-btn` in the terminal header bar.
2.3 Implement `_switch_tab(file_path)` method: update `_active_tab_path`, re-render tab buttons, show/hide editor content widgets.
2.4 Implement tab close behavior: clicking `×` on a tab calls `close_file_tab` and switches to the most recent tab.
2.5 Wire `on_toggle_split_btn` to show/hide `#editor-split-pane` and adjust the chat column width.
2.6 Add keyboard binding `ctrl+\` to toggle the split pane (standard IDE convention, not currently bound).
2.7 Add syntax highlighting to editor content widgets using `Rich.Syntax` (language by file extension).
2.8 Add dirty-marker dot on tab button for modified files (track `_open_tabs[path]["dirty"]` flag on WRITE/EDIT steps).
2.9 Add tests: `core/tests/test_tui_editor_pane.py` covering tab open/close/switch, split toggle, syntax highlighting.

---

## Task 3: Phase 6a — Accessibility & Focus Management

3.1 Audit all interactive widgets for `:focus`/`:hover`/`:disabled` CSS rules in `tui_app.tcss`. Add missing rules for Buttons, ToggleButton, and tab buttons.
3.2 Ensure `ApprovalModal.on_mount` sets focus to `#allow-btn` (already done, verify).
3.3 Add `focus` ring CSS for all interactive elements (border or outline using `$primary` or `$accent`).
3.4 Verify `PromptTextArea` suggestion dropdown handles keyboard navigation (↑/↓/Enter/Esc) — already implemented, add regression test.
3.5 Add `aria-label` or tooltip text on all icon-only buttons (copy, attach context, send, toggle sidebar).
3.6 Run `pytest core/tests/` to verify all existing tests still pass.

---

## Task 4: Phase 6b — Performance & Streaming Polish

4.1 Profile the streaming update path: ensure `call_after_refresh` coalescing is used in `_append_token` to avoid excessive re-renders during high-throughput token streams.
4.2 Consider replacing the `Markdown` widget re-render on every token with `RichLog` for the streaming body during active token delivery, switching to `Markdown` on completion. This avoids full re-layout on each token.
4.3 Add `call_after_refresh` coalescing to `_handle_step` — if multiple tool steps arrive in rapid succession, batch the DOM updates.
4.4 Verify the 120-child cap on `#chat-container` works correctly — old messages should be pruned from the DOM, not just hidden.
4.5 Add a `Lazy()` wrapper around the plan sidebar and agent memory panel so they don't consume layout resources when the sidebar is hidden.
4.6 Run `pytest core/tests/` to verify all existing tests still pass.

---

## Task 5: Theme & Visual Polish

5.1 Audit all themes in `_TORCHLIGHT_THEME`, `_BLUEPRINT_LIGHT_THEME`, and the built-in Textual themes (`nord`, `gruvbox`, `solarized-*`) for contrast issues. Run `./tui.sh` → `ctrl+t` through all themes and verify no unreadable text.
5.2 Ensure the `ShortcutsHelpModal` uses a grouped-by-category layout (keys / palette / slash commands) instead of a single flat list.
5.3 Add a custom `coding-agent` theme variant with adjusted colors for better readability of diff output (green/red contrast).
5.4 Run `ruff check rlm_optimized/` and `pytest core/tests/` to verify lint and tests.

---

## Validation

| Level | Command / Method |
|---|---|
| Unit | `pytest core/tests/` (all new + existing tests pass) |
| Lint | `ruff check rlm_optimized/` clean |
| Smoke | `./tui.sh` → start engine → run a multi-tool task → visually verify editor tabs, split toggle, a11y focus rings |
| Narrow terminal | resize to <80 cols → sidebar hides, chat takes 1fr, editor pane collapses |
| Theme sweep | `ctrl+t` through all themes → no unreadable contrast, no hardcoded hex regressions |
| Keyboard | `ctrl+\` toggles split pane, `ctrl+p` opens palette, `/` shows suggestions, all bindings shown in Footer |

---

## Non-Goals

- No changes to the agent engine, tool execution, approval decision logic, or model prompts.
- No context-budget changes — the UI must remain invisible to the LLM's token accounting.
- No web/browser UI (TUI stays terminal-only, per Torchlight's charter).
- No new dependencies beyond what Textual/Rich already provide.

---

## Effort & Sequencing

| Task | Effort | Notes |
|---|---|---|
| 1 Bug fixes | S | Unblocks everything; 2 small fixes |
| 2 Editor split pane | L | Largest single feature; gate on user need |
| 3a a11y | M | Audit + fix focus/hover/disabled rules |
| 3b Performance | M | Streaming coalescing + Lazy() panels |
| 4 Theme polish | S | Audit + shortcut grouping |
| 5 Validation | S | Run full suite + smoke test |

**Recommended sequence:** 1 → 3a → 3b → 4 → 2, with 5 as the final validation step.
