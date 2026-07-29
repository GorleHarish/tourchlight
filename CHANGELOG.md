# Changelog

All notable changes to Torchlight will be documented in this file.

## [v1.9.0] - 2026-07-29

### Added & Improved
- **Enhanced Web Browsing & Stealth Anti-Blocking Engine**:
  - **Structure-Preserving HTML Parser (`StructurePreservingHTMLParser`)**: Isolates `<pre><code>` blocks, parameter tables, lists, and headings while stripping navigation bars, sidebars, footers, and script noise.
  - **Stealth Browser Request Headers (`_get_browser_headers`)**: Passes realistic browser fingerprints (`Sec-Ch-Ua`, `Sec-Fetch-Dest`, `Accept-Language`) and HTTP/2 headers to prevent generic scraper blocks.
  - **Remote Headless Playwright Fallback (`_fetch_remote_playwright`)**: Tier-2 fallback engine routing remote URLs through Playwright when HTTP GET returns 403, 429, Cloudflare anti-bot challenges, or empty JavaScript SPAs.
  - **Version-Aware Dependency Query Augmentation (`_augment_query_with_project_deps`)**: Auto-inspects `pyproject.toml` and `package.json` in project root to lock `DOC_SEARCH` queries to active library versions (e.g. `pydantic v2`, `react v19`).
  - **Web Tool Unit Tests (`test_enhanced_web_tools.py`)**: Unit test suite verifying structure-preserving HTML parsing, header generation, version query augmentation, and web tool execution.

## [v1.8.0] - 2026-07-29

### Added & Improved
- **Zero-Context Code Quality Harness**: Deterministic post-processing, formatting, and multi-language validation engine operating inside the Python harness layer without consuming LLM context tokens:
  - **Format-on-Save (`_format_code_on_save`)**: Automatically runs local code formatters (`ruff format`/`black` for Python, `prettier` for JS/TS/JSON/CSS/HTML, `gofmt` for Go, `rustfmt` for Rust) on file write/edit tool execution with a 2-second timeout.
  - **Multi-Language Syntax & Bracket Validator (`_check_syntax`)**: Inline AST/JSON/JS bracket parsing validating Python syntax, JSON structural integrity, and JS/TS/C bracket balancing (stripping string literals and comments).
  - **Stub & Placeholder Detector (`_detect_stubs`)**: Scans written code for lazy LLM placeholder comments (`# TODO: implement`, `// ... existing code`, `pass # stub`) and appends warning notes to tool output to ensure complete implementation.
  - **POSIX Whitespace & Tab Normalizer (`_normalize_whitespace`)**: Converts mixed tabs to 4 spaces, strips trailing line whitespace, and guarantees trailing newlines (strictly preserving tab indentation for `Makefile`, `Go`, `TSV`, and `.mk` files).
  - **Harness Test Suite (`test_code_quality_harness.py`)**: Unit tests covering format-on-save, syntax validation, stub detection, Makefile tab preservation, and fuzzy edit matching.

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
