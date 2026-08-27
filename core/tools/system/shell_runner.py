"""Safe shell command execution and process timeout management."""

from __future__ import annotations

import re
import subprocess
from typing import Any, Dict

from core.tools.system.memory_ops import tool_search_ast_impl


_SAFE_COMMANDS_SET = {
    "ls",
    "la",
    "ll",
    "cat",
    "head",
    "tail",
    "echo",
    "pwd",
    "which",
    "find",
    "grep",
    "rg",
    "awk",
    "sed",
    "wc",
    "diff",
    "file",
    "python -m pytest",
    "pytest",
    "python -m mypy",
    "mypy",
    "python -m flake8",
    "flake8",
    "ruff check",
    "git status",
    "git log",
    "git diff",
    "git show",
    "git branch",
    "git stash list",
    "git remote",
    "git fetch",
    "npm test",
    "npm run test",
    "npx jest",
    "cargo test",
    "cargo check",
    "cargo clippy",
    "sysctl",
    "vm_stat",
    "top -l",
    "df",
    "diskutil list",
    "pip list",
    "pip show",
    "pip freeze",
    "node --version",
    "python --version",
    "python3 --version",
    "tree",
}

_LONG_CMDS = (
    "pip install",
    "pip3 install",
    "npm install",
    "yarn",
    "cargo build",
    "gradle",
    "./gradlew",
    "mvn ",
    "make ",
    "cmake",
)


def tool_run_command_impl(args: dict, project_root: str) -> str:
    """RUN_COMMAND — execute a shell command."""
    cmd = args.get("cmd", "")
    cmd_clean = cmd.strip()

    # Intercept accidental internal AST tool or Python function calls routed to RUN_COMMAND
    if "get_project_structure" in cmd_clean:
        return tool_search_ast_impl({"action": "structure"}, project_root)

    if cmd_clean.startswith("semantic_search"):
        match = re.search(
            r'semantic_search\((?:query_string=)?["\'](.*?)["\']', cmd_clean
        )
        q = (
            match.group(1)
            if match
            else cmd_clean.replace("semantic_search", "").strip("() '\"")
        )
        return tool_search_ast_impl({"action": "search", "query": q}, project_root)

    if cmd_clean.startswith("SEARCH_AST"):
        match = re.search(r"SEARCH_AST\((.*?)\)", cmd_clean, re.IGNORECASE)
        payload = match.group(1) if match else ""
        if "structure" in payload.lower():
            return tool_search_ast_impl({"action": "structure"}, project_root)
        return tool_search_ast_impl(
            {"action": "search", "query": payload}, project_root
        )

    timeout = 180 if any(cmd_clean.startswith(c) for c in _LONG_CMDS) else 30

    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if out and err:
            output = f"{out}\n--- stderr ---\n{err}"
        else:
            output = out or err or "(no output)"
        if "undefined" in output:
            output = "\n".join(
                l for l in output.splitlines() if l.strip() and l.strip() != "undefined"
            )
        status = "OK" if r.returncode == 0 else f"Exit {r.returncode}"
        return f"{status}\n```\n{output[:3000]}\n```"
    except subprocess.TimeoutExpired:
        return f"Command timed out ({timeout}s). For long installs use a background process."
    except Exception as e:
        return f"Error: {e}"
