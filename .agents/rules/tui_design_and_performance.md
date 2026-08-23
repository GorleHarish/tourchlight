# Textual & Rich TUI Performance and Design Rules

Rules and design patterns for building lag-free, visually artifact-free Terminal User Interfaces (TUIs) in Textual and Rich within this codebase.

## 1. Widget Border & Alignment Discipline

- **Never Mix `border: round` with `border-left: thick`**: Combining rounded corners with thick left borders causes 1-character horizontal elbow tick protrusions (`▌`). Always use uniform solid borders (`border: solid $panel; border-left: solid $accent;`) on card containers like `ToolCallCard`, `MessageCard`, and `StreamingView`.
- **Flat Modal Buttons**: Always style modal and action buttons with `border: none; padding: 0 1; height: 3;`. This prevents Textual's default 3-row tall box borders (`╭─`, `╰─`) from protruding as tab ears when button variants change dynamically (e.g., `SEND ↗` → `⏹ STOP`).

## 2. Modal Backdrop Opacity

- **100% Opaque Solid Dark Modal Backdrop**: Always style `ModalScreen` with a 100% solid dark background (e.g., `ModalScreen { background: #0d1117; align: center middle; }`). Never use semi-transparent `rgba()` opacity, which causes background text, vertical trajectory lines (`│`, `┆`), and active worker updates to bleed through modal overlays.

## 3. High-Performance Log Rendering

- **Use `RichLog.write()` for Log Streams**: Never execute `$O(N)` string list re-joins (`\n.join(deque)`) on `Static` widgets for continuous logs. Always use `RichLog` with direct `.write()` calls.
- **Rich Markup Formatting**: Convert raw markdown bold markers (like `**text**`) to Rich markup tags (`[bold]text[/bold]`) before writing to `RichLog` so output log traces render cleanly without raw asterisks.

## 4. Telemetry & Disk I/O Throttling

- **Cache Disk-Bound Telemetry Calls**: Wrap file-backed status calls (such as reading `goal_spec.json` and `tasks.md` via `get_workspace_task_status_summary`) in a 2.0-second TTL cache (`_cached_task_summary_ts`).
- **Status Bar Segment Repaint Deduplication**: In `StatusBar.update_status()`, check `_last_segments` before invoking `Widget.update()` to skip redundant DOM repaints when state markup is unchanged.

## 5. Renderable AST Caching & Adaptive Streaming

- **LRU Cache Markdown & Syntax Trees**: Use `@lru_cache(maxsize=128)` on code block extractors (`extract_code_blocks`) and Pygments `Syntax` object creation (`_build_cached_syntax`) in `transcript.py`.
- **TPS-Adaptive Stream Throttling**: Scale `_token_throttle_interval` dynamically (e.g., `0.033s` → `0.045s`) when streaming throughput exceeds 60 tokens/sec.
- **Resize Event Debouncing**: Debounce `on_resize()` events with a 100ms timer (`set_timer`) to prevent continuous layout recalculation during window dragging.
