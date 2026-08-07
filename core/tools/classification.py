"""
Tool risk classification for Torchlight.

Shared between CLI and TUI frontends.
"""

import re


# ── Risk tiers ─────────────────────────────────────────────────────────────

AUTO = "auto"        # safe reads and searches, execute immediately
CONFIRM = "confirm"  # writes and installs, prompt for approval
REVIEW = "review"    # destructive or irreversible, explicit approve


# ── Safe commands (always AUTO risk) ───────────────────────────────────────

_SAFE_COMMANDS = {
    "ls", "la", "ll", "cat", "head", "tail", "echo", "pwd", "which",
    "find", "grep", "rg", "awk", "sed", "wc", "diff", "file",
    "python -m pytest", "pytest", "python -m mypy", "mypy",
    "python -m flake8", "flake8", "ruff check",
    "git status", "git log", "git diff", "git show", "git branch",
    "git stash list", "git remote", "git fetch",
    "npm test", "npm run test", "npx jest",
    "cargo test", "cargo check", "cargo clippy",
    "sysctl", "vm_stat", "top -l", "df", "diskutil list",
    "pip list", "pip show", "pip freeze",
    "cat package.json", "cat Cargo.toml", "cat pyproject.toml",
    "node --version", "python --version", "python3 --version",
    "tree",
}


_SAFE_PATTERNS = [
    r'^git\s+(?:status|log|diff|show|branch|blame|rev-parse|tag|remote|stash\s+list|fetch)\b',
    r'^python[3]?\s+-c\b',
    r'^(?:cat|head|tail|grep|rg|wc|file|type|ls|dir|which|whereis|find|pwd|echo)\b',
    r'^(?:pip\s+(?:show|list|freeze)|npm\s+(?:ls|list|outdated)|cargo\s+(?:tree|metadata|check|test|clippy))\b',
    r'^(?:pytest|mypy|flake8|ruff\s+check)\b',
]
_SAFE_RE = re.compile("|".join(_SAFE_PATTERNS), re.IGNORECASE)


# ── Destructive patterns (always REVIEW risk) ─────────────────────────────

_DESTRUCTIVE_PATTERNS = [
    r'\brm\s', r'\bgit\s+push\b', r'\bgit\s+reset\b', r'\bgit\s+rebase\b',
    r'\bgit\s+merge\b', r'\bgit\s+clean\b',
    r'\bdrop\s+table\b', r'\btruncate\s+table\b', r'\bchmod\b', r'\bchown\b',
    r'\bsudo\b', r'>\s*/', r'\bmkfs\b', r'\bdd\b', r'\bkill\b', r'\bpkill\b',
    r'\bshutdown\b', r'\breboot\b',
]
_DESTRUCTIVE_RE = re.compile("|".join(_DESTRUCTIVE_PATTERNS), re.IGNORECASE)


# ── Confirm patterns (writes/install, CONFIRM risk) ───────────────────────

_CONFIRM_PATTERNS = [
    r'\bpip\s+install\b', r'\bpip3\s+install\b', r'\bnpm\s+install\b',
    r'\byarn\s+add\b', r'\bcargo\s+add\b', r'\bbrew\s+install\b',
    r'\bgit\s+add\b', r'\bgit\s+commit\b', r'\bgit\s+stash\b',
    r'\bgit\s+checkout\b', r'\bgit\s+switch\b', r'\bgit\s+restore\b',
    r'\bpython\s+.*\.py\b',
    r'\bnode\s+', r'\btouch\b', r'\bmkdir\b', r'\bcp\b', r'\bmv\b',
]
_CONFIRM_RE = re.compile("|".join(_CONFIRM_PATTERNS), re.IGNORECASE)


def classify_command(cmd: str) -> str:
    """
    Classify a shell command into AUTO, CONFIRM, or REVIEW risk tier.

    Priority: REVIEW > safe list / safe regex > CONFIRM > default CONFIRM
    """
    cmd_stripped = cmd.strip()
    if _DESTRUCTIVE_RE.search(cmd_stripped):
        return REVIEW
    if _SAFE_RE.search(cmd_stripped):
        return AUTO
    for safe in _SAFE_COMMANDS:
        if cmd_stripped.startswith(safe) or cmd_stripped == safe:
            return AUTO
    if _CONFIRM_RE.search(cmd_stripped):
        return CONFIRM
    return CONFIRM  # default: ask for confirmation


def classify_tool(tool_name: str, args: dict = None) -> str:
    """
    Classify a tool call into AUTO, CONFIRM, or REVIEW risk tier.
    """
    tool_upper = tool_name.upper() if tool_name else ""
    if tool_upper in ("READ_FILE", "GREP", "READ_SYMBOLS", "SEARCH_AST", "LIST_DIR", "INSPECT_WEB", "SAVE_MEMORY", "UPDATE_TASK_GRAPH", "SET_PHASE"):
        return AUTO
    if tool_upper in ("WRITE_FILE", "EDIT_FILE"):
        return CONFIRM
    if tool_upper == "RUN_COMMAND" and args:
        cmd = args.get("command", args.get("cmd", ""))
        return classify_command(cmd)
    return CONFIRM

