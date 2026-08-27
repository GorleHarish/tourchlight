"""Code formatting, file and syntax verification, interactive user query, and game testing engines."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def tool_format_code_impl(args: dict, project_root: str) -> str:
    """FORMAT_CODE — beautify a code snippet."""
    snippet = args.get("snippet", "")
    language = args.get("language", "python")
    if language.lower() in ("python", "py"):
        try:
            import black

            return black.format_str(snippet, mode=black.Mode())
        except ImportError:
            return f"'black' not installed. Returning raw snippet:\n{snippet}"
    return snippet


def tool_verify_impl(args: dict, project_root: str) -> str:
    """VERIFY — verify a file exists and optionally contains expected content or compiles."""
    try:
        from core.tools.implementations import _check_syntax, _check_compile

        path = args.get("path", "")
        expected_snippet = args.get("expected_snippet")
        do_compile = bool(args.get("compile", False))
        p = os.path.join(project_root, path) if not os.path.isabs(path) else path
        if not os.path.exists(p):
            return f"Verification FAILED: File does not exist at {path}"
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        notes = []
        if expected_snippet:
            if expected_snippet in content:
                notes.append("expected content found")
            else:
                return f"Verification WARNING: File exists but expected snippet was NOT found in {path}"
        if do_compile:
            syntax_note = _check_syntax(content, p)
            if syntax_note:
                detail = syntax_note.replace("\n⚠️ Syntax Warning", "").strip()
                return f"Verification FAILED: Syntax error in {path}: {detail}"
            compile_note = _check_compile(content, p, project_root)
            if compile_note:
                return f"Verification FAILED: Syntax error in {path}: {compile_note}"
            notes.append("compile check passed")
        suffix = (f" ({'; '.join(notes)})") if notes else ""
        return f"Verification SUCCESS: File exists at {path}{suffix}"
    except Exception as e:
        return f"Verification ERROR: {e}"


def tool_ask_user_impl(args: dict, project_root: str) -> str:
    """ASK_USER — ask the user a question with structured options and custom input."""
    questions_list = args.get("questions")
    if isinstance(questions_list, list) and questions_list:
        lines = ["[AWAITING USER INPUT] Multiple questions for review:"]
        for q_idx, q in enumerate(questions_list, 1):
            q_text = q.get("question", f"Question {q_idx}")
            q_opts = q.get("options", [])
            is_m = bool(q.get("is_multi_select", False))
            opt_type = "Checkbox (Multi-Select)" if is_m else "Radio (Single Choice)"
            lines.append(f"\n{q_idx}. {q_text} [{opt_type}]")
            for idx, opt in enumerate(q_opts, 1):
                marker = "[ ]" if is_m else "( )"
                lines.append(f"  {marker} {idx}. {opt}")
        if args.get("allow_custom_input", True):
            lines.append("\n  [ ] Custom text input / feedback (reply with your answers)")
        return "\n".join(lines)

    question = args.get("question", "")
    options = args.get("options", [])
    is_multi = bool(args.get("is_multi_select", False))
    allow_custom = bool(args.get("allow_custom_input", True))

    lines = [f"[AWAITING USER INPUT] {question}"]
    if options and isinstance(options, list):
        opt_type = "Checkbox (Multi-Select)" if is_multi else "Radio (Single Choice)"
        lines.append(f"Input Type: {opt_type}")
        for idx, opt in enumerate(options, 1):
            marker = "[ ]" if is_multi else "( )"
            lines.append(f"  {marker} {idx}. {opt}")
        if allow_custom:
            marker = "[ ]" if is_multi else "( )"
            lines.append(f"  {marker} {len(options) + 1}. Custom text input (reply with your own answer)")
    return "\n".join(lines)


def tool_set_phase_impl(args: dict, project_root: str) -> str:
    """SET_PHASE — switch active agent phase."""
    phase = str(args.get("phase", "code")).lower().strip()
    reason = args.get("reason", "")
    reason_str = f" Reason: {reason}" if reason else ""
    return f"Agent phase switched to '{phase}' successfully.{reason_str}"

def tool_play_and_verify_game_impl(args: dict, project_root: str) -> str:
    """Plays an HTML game autonomously, analyzing frame buffers and runtime events."""
    path = str(args.get("path", "")).strip()
    duration_ms = int(args.get("duration_ms", args.get("wait_ms", 3000)))
    return play_and_verify_game(
        path=path, duration_ms=duration_ms, project_root=project_root
    )


def tool_self_improve_game_impl(args: dict, project_root: str) -> str:
    """Executes closed-loop autonomous repair and verification on an HTML game."""
    path = str(args.get("path", "")).strip()
    max_iterations = int(args.get("max_iterations", 3))
    duration_ms = int(args.get("duration_ms", 2500))
    return self_improve_game(
        path=path,
        max_iterations=max_iterations,
        duration_ms=duration_ms,
        project_root=project_root,
    )


def play_and_verify_game(
    path: str = "",
    duration_ms: int = 3000,
    project_root: str = ".",
    **kwargs: Any,
) -> str:
    """Plays an HTML game autonomously, analyzing frame buffers and runtime events."""
    if not path:
        return "PLAY_AND_VERIFY_GAME requires 'path' parameter."

    full_path = (
        Path(project_root) / path if not Path(path).is_absolute() else Path(path)
    )

    try:
        from core.execution.game_inspector import HtmlGamePlayer

        player = HtmlGamePlayer(
            output_dir=Path(project_root) / ".torchlight" / "screenshots"
        )
        res = player.play_and_verify(
            file_path=str(full_path)
            if not path.startswith(("http://", "https://"))
            else path,
            duration_ms=duration_ms,
        )
        return res.to_markdown()
    except Exception as e:
        return f"Error playing and verifying HTML game: {e}"


def self_improve_game(
    path: str = "",
    max_iterations: int = 3,
    duration_ms: int = 2500,
    project_root: str = ".",
    **kwargs: Any,
) -> str:
    """Executes closed-loop autonomous repair and verification on an HTML game."""
    if not path:
        return "SELF_IMPROVE_GAME requires 'path' parameter."

    full_path = (
        Path(project_root) / path if not Path(path).is_absolute() else Path(path)
    )

    try:
        from core.execution.game_self_improver import GameSelfImprover

        improver = GameSelfImprover(project_root=Path(project_root))
        report = improver.run_self_improvement_cycle(
            file_path=str(full_path),
            max_iterations=max_iterations,
            duration_ms=duration_ms,
        )
        return report.to_markdown()
    except Exception as e:
        return f"Error executing HTML game self-improvement cycle: {e}"
