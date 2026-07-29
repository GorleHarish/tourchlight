# Changelog

All notable changes to Torchlight will be documented in this file.

## [v1.9.1] - 2026-07-29

### Fixed & Improved
- **Robust Reasoning & Answer Tag Parsing**:
  - **Explicit `<think>` Block Extraction**: Isolated `<think>...</think>` and `<thought>...</thought>` reasoning tags emitted by reasoning models (Qwen 2.5, DeepSeek R1, Gemma) into the Reasoning UI block instead of leaking them into answer output.
  - **Mid-Sentence Tag Split Prevention**: Fixed an issue in `_parse_response` where `<FINAL_ANSWER>` tags mentioned mid-sentence (e.g., `"I will use <FINAL_ANSWER> to..."`) caused reasoning text to be truncated mid-sentence and sentence fragments assigned to the Final Answer panel.
  - **Direct Plain-Text Answer Support**: Non-tool conversational responses without explicit `<FINAL_ANSWER>` tags are now cleanly extracted as final answers, eliminating infinite thinking loop degradation and unnecessary prompt nudges.
  - **Template Placeholder Filtering**: Added filtering for template artifact tags like `<FINAL_ANSWER>your answer</FINAL_ANSWER>` copied from prompt examples.
  - **Unit Test Coverage**: Added comprehensive test cases in `core/tests/test_rlm_engine.py` covering reasoning extraction, mid-sentence tag prevention, and direct text answer parsing (245 tests passing).

## [v1.9.0] - 2026-07-29

### Added & Improved
- **Enhanced Web Browsing & Stealth Anti-Blocking Engine**:
  - **Structure-Preserving HTML Parser (`StructurePreservingHTMLParser`)**: Isolates `<pre><code>` blocks, parameter tables, lists, and headings while stripping navigation bars, sidebars, footers, and script noise. Uses depth tracking (`code_depth`, `skip_depth`) to cleanly render nested `<pre><code>` tags without duplicate backtick fences.
  - **Stealth Browser Request Headers (`_get_browser_headers`)**: Passes realistic browser fingerprints (`Sec-Ch-Ua`, `Sec-Fetch-Dest`, `Accept-Language`) and HTTP/2 headers to prevent generic scraper blocks.
  - **Remote Headless Playwright Fallback (`_fetch_remote_playwright`)**: Tier-2 fallback engine routing remote URLs through Playwright when HTTP GET returns 403, 429, Cloudflare anti-bot challenges, or empty JavaScript SPAs.
  - **Indirect Prompt Injection Sanitization**: Automatically escapes `<tool_call>` tags in fetched web page content to prevent poisoned web pages from injecting unauthorized tool calls into LLM conversation history.
  - **Version-Aware Dependency Query Augmentation (`_augment_query_with_project_deps`)**: Auto-inspects `pyproject.toml` (Poetry & PEP 621 array syntax) and `package.json` in project root to lock `DOC_SEARCH` queries to active library versions (e.g. `pydantic v2`, `react v19`).
  - **Unified System Prompt Alignment**: Declared `WEB_FETCH`, `DOC_SEARCH`, `WEB_SEARCH`, and `WEB_VERIFY` explicitly in `[TOOL PIPELINE]` across core system prompts (`core/prompts/system.py`), CLI prompts (`prompts.py`), and small-context prompts (`prompts_minimal.py`).
  - **Web Tool Unit Tests (`test_enhanced_web_tools.py`)**: Unit test suite verifying structure-preserving HTML parsing, depth tracking, header generation, version query augmentation, prompt injection sanitization, and web tool execution (198 tests passing).


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
