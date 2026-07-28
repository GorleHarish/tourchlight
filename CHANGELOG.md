# Changelog

All notable changes to Torchlight will be documented in this file.

## [v1.7.0] - 2026-07-29

### Added
- **Phase-Tailored System Prompt Injection**: System prompt generator (`get_phase_system_prompt()`) appending phase-specific instructions for `plan`, `code`, `troubleshoot`, and `chat` modes.
- **Anti-Symptom-Patching Directives**: Hardcoded directives in `SYSTEM_PROMPT` prohibiting masking symptoms, swallowing exceptions, returning dummy fallbacks, or deleting failing unit tests.
- **Dynamic L0 Working Memory Scratchpad**: `format_l0_scratchpad()` in `TieredMemory` formatting active goal, modified files, active errors, failing tests, and key decisions into system context on every turn.
- **Context Headroom Calculation**: `get_available_headroom()` in `TieredMemory` for computing remaining token capacity prior to tool formatting.
- **Comprehensive Unit Testing**: Added `core/tests/test_prompts_and_memory.py` testing phase prompt generation, anti-patching rules, L0 scratchpad formatting, and headroom calculations.

### Fixed & Improved
- **CLI Phase Prompt Integration**: Front-end CLI loop now dynamically injects phase prompts based on task phase detection (`_detect_phase()`).
