## Codebase Exploration & Token Optimization Hard Rules
- **MANDATORY Graphify-First Search & Relationship Analysis**: For understanding codebase architecture, module relationships, dependencies, call paths, or finding specific components, ALWAYS use `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` (or `query_graph` MCP tool) before reading raw source files line by line or running mass grep scans.
- **Dependency & Relationship Tracing**: Use `graphify path` to trace dependencies between components and `graphify explain` to analyze callers, callees, and structural links with minimal token overhead.
- **Token Conservation**: Rely on targeted graph queries and scoped subgraphs to save context tokens while preserving high analytical quality and accuracy.
- **Keep Graph Current**: After modifying code files in a session, run `graphify update .` to keep the knowledge graph up to date.
- **TUI Performance & Design Rules (MANDATORY for all UI changes)**: Whenever creating or modifying UI components, widgets, modals, layouts, or CSS, ALWAYS strictly follow [.agents/rules/tui_design_and_performance.md](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/.agents/rules/tui_design_and_performance.md) (solid borders, 100% opaque backdrops, `RichLog.write()`, 2.0s telemetry TTL cache, and TPS-adaptive throttling).

## Deterministic Trajectory & SLM Reliability Hard Rules (99%+ Accuracy for Small Models)
- **Single-Path State Transitions**: All error recovery hints and loop gates must inject a single, unambiguous `<tool_call>` template rather than open-ended multi-bullet guidance, keeping 3B models strictly on-rails.
- **Anchor-Enforced Code Modifications**: Single-line edits (`s_l == e_l`) strictly require `old_text` to anchor replacements; unanchored 1-line overwrites are hard-rejected at the tool contract level to prevent typewriter stepping loops.
- **Block-Level Edit Discipline**: Function and module implementations must be written as full multi-line blocks (`EDIT_FILE` with $e_l - s_l \ge 1$) or full files (`WRITE_FILE`) in a single turn.
- **Sliding 1-Line Stepping Detection**: `TrajectoryLock` detects consecutive single-line edits (`L{k}-L{k}`) across turns and immediately blocks the crawl with a direct `WRITE_FILE` directive.
- **Auto-Interception of Markdown JSON**: When SLMs emit markdown code blocks (` ```json `) inside simulated walkthroughs, `_parse_response` extracts and executes the first balanced tool call on turn 1.
- **Deterministic New File Creation (Zero-Read Onboarding)**: For tasks marked `[NEW]` or targeting non-existent files, agents must immediately emit `WRITE_FILE` with complete initial code rather than probing with `READ_FILE` or `SEARCH_AST`.
- **Actionable Tool-Call Injection on Missing Files**: `READ_FILE`, `EDIT_FILE`, and `TrajectoryLock` on non-existent files must never recommend exploratory shell checks (`ls` / `find`). They must directly inject a concrete `<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "<path>", "content": "..."}}</tool_call>` template to guarantee single-path recovery.
- **Execution-Flow Tracing Protocol**: When debugging multi-component bugs, agentic loop stalls, or empty output cards, apply the 7-step forward execution trace (`.agents/skills/execution-trace-debug/SKILL.md`) from entry point to divergence before modifying code.

