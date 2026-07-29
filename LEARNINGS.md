# Architectural Learnings & Engineering Principles

This document summarizes key learnings and design principles established during the development and optimization of **Torchlight Agent**.

---

## 1. Context Engineering & Memory Architecture

### A. Context Overhead vs Available Headroom
- **Insight:** In local LLM setups (4k–12k context windows), system prompts and tool schemas consume up to 25–35% of total budget before any conversation turns are added.
- **Principle:** Every component must have a explicit token budget. Flashlight beams (AST subgraphs) must scale dynamically to model capacity (e.g. 1 file × 50 lines for 4k models vs 3 files × 120 lines for 12k models).

### B. The L0 Working Memory Scratchpad
- **Insight:** Sliding-window context truncation causes models to forget active goals, modified files, and failing test names.
- **Principle:** Maintain a machine-managed L0 scratchpad (`format_l0_scratchpad()`) injected into the system prompt on every turn. This provides continuous grounding even when older history turns are summarized.

### C. Active File Pinning
- **Insight:** Rereading files after compression bloats history with duplicate tokens.
- **Principle:** Maintain a FIFO buffer (max 2 files) of active file slices (`_pinned_files`) that survive context compression without inflating conversation turn length.

---

## 2. Prompt Engineering & Agent Steering

### A. Phase-Tailored Prompt Injection
- **Insight:** A single static system prompt leads to suboptimal model behavior (e.g. attempting full file rewrites during planning or being overly verbose during surgical coding).
- **Principle:** Dynamically inject phase instructions (`get_phase_system_prompt(phase)`) alongside temperature presets (`plan`: 0.3, `code`: 0.1, `troubleshoot`: 0.2).

### B. Anti-Symptom-Patching Directives
- **Insight:** Coding agents tend to fix bugs by masking symptoms (e.g. inserting `try/except: pass`, returning dummy fallbacks, or removing failing assertions).
- **Principle:** Include explicit anti-patching rules in system prompts to enforce root-cause investigation and un-truncated traceback analysis.

### C. Non-Verbose 3-Tier Output Discipline
- **Insight:** Streaming full code blocks into assistant chat text consumes huge context budgets and causes screen buffer overflow.
- **Principle:** Enforce a strict text output ceiling (<40 words) and mandate that code modifications occur strictly via structured tool payloads (`WRITE_FILE`/`EDIT_FILE`).

---

## 3. Autonomous Execution & Verification

### A. Surgical Traceback Extraction
- **Insight:** Full test suite stdout/stderr dumps contain noise (passing test lists, ANSI codes) that consume context.
- **Principle:** Extract strictly failing traceback sections (35–40 lines max) using regex parsers before feeding test results back to the agent loop.

### B. Test-Driven Local Reverts
- **Insight:** Multi-epoch autonomous runners can degrade codebases if bad changes accumulate.
- **Principle:** Automatically execute local Git reverts (`git checkout -- .`) when test suites fail across consecutive micro-epochs.

---

## 4. Web Browsing, Anti-Blocking & Documentation Engineering

### A. Structure-Preserving Content Extraction vs HTML Fluff
- **Insight:** Naive HTML tag stripping (`re.sub(r"<[^>]+>", " ")`) destroys code block syntax, indentation, and API table formatting while flooding context windows with navigation headers and footer noise.
- **Principle:** Use structured HTML parsers (`StructurePreservingHTMLParser`) that explicitly isolate `<pre><code>` blocks, parameter tables, and headers while dropping script, nav, and footer tags.

### B. Multi-Tier Anti-Blocking Escalation Ladder
- **Insight:** Simple HTTP GET requests with generic user-agents fail on 403 Forbidden, 429 Rate Limits, or Cloudflare bot checks, while headless browsers consume higher VRAM/latency if used for every request.
- **Principle:** Implement a multi-tier fallback ladder: Jina Reader API → Stealth HTTP GET with browser sec headers (`Sec-Ch-Ua`, `Sec-Fetch-Dest`) → Remote Headless Playwright Chromium browser.

### C. Version-Locked Documentation Queries
- **Insight:** Web searches for popular libraries (React, Pydantic, Next.js) often return outdated version documentation, leading models to hallucinate obsolete or deprecated API parameters.
- **Principle:** Inspect project dependency manifests (`pyproject.toml`, `package.json`) to automatically augment search queries with active package versions (e.g. `query + " v2"`).

