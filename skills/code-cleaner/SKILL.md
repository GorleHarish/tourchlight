---
name: code-cleaner
description: Automated dead code, debug logging, and trailing whitespace cleaner
icon: 🧹
risk_level: confirm
category: workflow
tags: [cleanup, lint, refactor, format]
---

# Code Cleaner Skill

A practical workflow skill for sanitizing and polishing source code before committing.

## Purpose & Triggers
Use when the user asks to clean up, declutter, remove debug logs, or normalize formatting in their project.

## Workflow Instructions
1. **Audit Targets**: Run `GIT status` or `SEARCH_AST` to identify modified or target files.
2. **Detect Cleanups**:
   - Check for leftover debug statements (`print()`, `console.log()`, `debugger;`, `TODO: remove`).
   - Check for unused imports and unreferenced local variables.
   - Check for trailing whitespace, inconsistent indentation, or missing EOF newlines.
3. **Apply Minimal Edits**:
   - Use `EDIT_FILE` to surgically clean up lines without altering business logic.
   - When appropriate, trigger project linters (e.g. `ruff check --fix`, `prettier --write`).
4. **Verify**:
   - Run project test suites to confirm that behavior is intact.
   - Run `GIT diff` to inspect changes.
