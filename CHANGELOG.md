# Changelog

All notable changes to Torchlight will be documented in this file.

## [v1.7.0] - 2026-07-29

### Added
- **Manual Compact Button**: Added an explicit `🗜️ Compact` button to the TUI input header bar ([tui_app.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/tui_app.py)) next to the model selector and context progress badge, providing an immediate visual trigger for manual context compaction.
- **Phase-Tailored System Prompt Injection**: System prompt generator (`get_phase_system_prompt()`) appending phase-specific instructions for `plan`, `code`, `troubleshoot`, and `chat` modes.
- **Anti-Symptom-Patching Directives**: Hardcoded directives in `SYSTEM_PROMPT` prohibiting masking symptoms, swallowing exceptions, returning dummy fallbacks, or deleting failing unit tests.
- **Dynamic L0 Working Memory Scratchpad**: `format_l0_scratchpad()` in `TieredMemory` formatting active goal, modified files, active errors, failing tests, and key decisions into system context on every turn.
- **Context Headroom Calculation**: `get_available_headroom()` in `TieredMemory` for computing remaining token capacity prior to tool formatting.
- **Comprehensive Unit Testing**: Added `core/tests/test_prompts_and_memory.py` testing phase prompt generation, anti-patching rules, L0 scratchpad formatting, and headroom calculations.

### Fixed & Improved
- **Live Context Progress Bar UI Update**: Fixed UI context token percentage calculation in [tui_app.py](file:///Users/harishgorle/Desktop/opencode/tourchlight%20v1_i6/rlm_optimized/tui_app.py) (`_build_context_progress_text`) to use live memory token count (`mem.total_tokens`) rather than a static estimation heuristic, ensuring the progress bar and percentage immediately drop upon compaction.
- **12k TurboQuant Context Budget Calibration**: Formally documented the 12,288 token context budget breakdown in `AGENTS.md` and `LEARNINGS.md`, detailing allocation for L0 scratchpad, full 3-file AST flashlight beam (~1.5k tokens), and ~9.6k tokens (~80%) conversation headroom.
- **CLI Phase Prompt Integration**: Front-end CLI loop now dynamically injects phase prompts based on task phase detection (`_detect_phase()`).
