"""Git repository operations, risk classification, and status reporting."""

from __future__ import annotations

import subprocess
from typing import Any, Dict, Tuple


_GIT_SAFE_SUBCOMMANDS = {
    "status",
    "log",
    "diff",
    "show",
    "branch",
    "stash",
    "remote",
    "ls-files",
    "rev-parse",
    "describe",
    "blame",
    "shortlog",
}
_GIT_WRITE_SUBCOMMANDS = {"add", "restore", "stash", "checkout", "switch"}
_GIT_DESTRUCTIVE_SUBCOMMANDS = {"push", "reset", "rebase", "merge", "clean", "drop"}


def _git_run(cmd: str, project_root: str, timeout: int = 30) -> tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
        )
        output = (r.stdout or "").strip()
        if r.stderr:
            err = r.stderr.strip()
            if err and not output:
                output = err
        return r.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Git command timed out ({timeout}s)"
    except Exception as e:
        return False, f"Git error: {e}"


def tool_git_impl(args: dict, project_root: str) -> str:
    """GIT — execute git operations with safety classification."""
    subcommand = (args.get("subcommand") or args.get("cmd") or "status").strip().lower()
    message = args.get("message") or args.get("msg") or ""
    files = args.get("files") or args.get("path") or ""
    flag = args.get("flag") or ""
    staged = args.get("staged", False)
    count = args.get("count") or args.get("n") or ""

    ok, _ = _git_run("git rev-parse --is-inside-work-tree", project_root)
    if not ok:
        try:
            from core.memory.persistence import ensure_git_repository

            ensure_git_repository(project_root)
            ok, _ = _git_run("git rev-parse --is-inside-work-tree", project_root)
        except Exception:
            pass
        if not ok:
            return (
                "Not a git repository. Use RUN_COMMAND('git init') to initialize one."
            )

    if subcommand in _GIT_DESTRUCTIVE_SUBCOMMANDS:
        return (
            f"DESTRUCTIVE: git {subcommand} requires explicit user approval.\n"
            f"Ask the user to confirm this operation."
        )

    if subcommand == "status":
        cmd = "git status --short"
    elif subcommand == "diff":
        parts = ["git diff"]
        if staged:
            parts.append("--staged")
        if files:
            parts.append(f"-- {files}")
        if flag:
            parts.append(flag)
        cmd = " ".join(parts)
    elif subcommand == "log":
        n = count or "10"
        parts = [f"git log --oneline -{n}"]
        if files:
            parts.append(f"-- {files}")
        if flag:
            parts.append(flag)
        cmd = " ".join(parts)
    elif subcommand == "show":
        ref = flag or "HEAD"
        cmd = f"git show --stat {ref}"
    elif subcommand == "branch":
        pattern = flag or ""
        cmd = f"git branch -a {pattern}".strip()
    elif subcommand == "blame":
        if not files:
            return "GIT blame requires a file path. Usage: GIT(subcommand='blame', files='path/to/file.py')"
        cmd = f"git blame {files}"
    elif subcommand == "commit":
        if not message:
            return "GIT commit requires a message. Usage: GIT(subcommand='commit', message='fix: ...', files='file.py')"
        parts = []
        if files:
            parts.append(f"git add {files}")
            parts.append("&&")
        parts.append(f'git commit -m "{message}"')
        cmd = " ".join(parts)
    elif subcommand == "add":
        target = files or flag or "."
        cmd = f"git add {target}"
    elif subcommand == "restore":
        target = files or flag or "."
        parts = ["git restore"]
        if staged:
            parts.append("--staged")
        parts.append(target)
        cmd = " ".join(parts)
    elif subcommand == "stash":
        action = flag or "push"
        if action == "list":
            cmd = "git stash list"
        elif action == "pop":
            cmd = "git stash pop"
        elif action == "drop":
            cmd = "git stash drop"
        else:
            cmd = "git stash push -m 'torchlight stash'"
    elif subcommand == "remote":
        cmd = "git remote -v"
    elif subcommand == "shortlog":
        cmd = "git shortlog -sn --all"
    else:
        return f"Unknown git subcommand: '{subcommand}'. Supported: {', '.join(sorted(_GIT_SAFE_SUBCOMMANDS | _GIT_WRITE_SUBCOMMANDS))}"

    ok, output = _git_run(cmd, project_root)
    if not output:
        output = "(no output)"

    if len(output) > 4000:
        lines = output.splitlines()
        output = "\n".join(lines[:80]) + f"\n... [{len(lines)} total lines, truncated]"

    status_icon = "✅" if ok else "⚠️"
    return f"{status_icon} git {subcommand}:\n{output}"
