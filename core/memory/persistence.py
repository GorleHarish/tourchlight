"""
Session and project memory persistence for Torchlight.
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Union

from .models import Message, MessageRole, SessionState, MemoryNeedle, MemoryObject


class SessionPersistence:
    def __init__(self, session_dir: Optional[Path] = None):
        if session_dir is None:
            self.session_dir = Path.home() / ".torchlight" / "sessions"
        else:
            self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, memory, session_name: Optional[str] = None, project_path: Optional[str] = None) -> str:
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_file = self.session_dir / f"{session_name}.json"
        messages_data = [
            {
                "role": msg.role.value if isinstance(msg.role, MessageRole) else str(msg.role),
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "token_count": msg.token_count,
                "metadata": msg.metadata,
            }
            for msg in memory.messages
        ]

        s = memory.state
        session_data = {
            "name": session_name,
            "created": datetime.now().isoformat(),
            "project_path": project_path,
            "state": {
                "intent": s.intent,
                "current_task": s.current_task,
                "next_steps": s.next_steps,
                "files_modified": s.files_modified,
                "files_read": s.files_read,
                "decisions": s.decisions,
                "arch_decisions": s.arch_decisions,
                "tech_stack": s.tech_stack,
                "failing_tests": s.failing_tests,
                "errors_seen": s.errors_seen,
                "dependencies_added": s.dependencies_added,
                "tried_and_failed": s.tried_and_failed,
                "active_file": s.active_file,
                "current_blocker": s.current_blocker,
            },
            "messages": messages_data,
            "total_tokens": memory.total_tokens,
        }

        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)
        return str(session_file)

    def load_session(self, session_name: str) -> Optional[dict]:
        session_file = self.session_dir / f"{session_name}.json"
        if not session_file.exists():
            return None
        with open(session_file) as f:
            return json.load(f)

    def list_sessions(self) -> list[dict]:
        sessions = []
        for f in sorted(self.session_dir.glob("*.json"), reverse=True):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                sessions.append({
                    "name": data.get("name", f.stem),
                    "created": data.get("created", ""),
                    "message_count": len(data.get("messages", [])),
                    "total_tokens": data.get("total_tokens", 0),
                })
            except Exception:
                continue
        return sessions


def ensure_git_repository(project_path: Union[Path, str], force_init: bool = False) -> Path:
    """
    Ensure target project directory exists and has a local Git repository initialized.
    Configures fallback user email and name if unconfigured.
    """
    path = Path(project_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    git_dir = path / ".git"
    if not git_dir.exists() or force_init:
        try:
            subprocess.run(["git", "init"], cwd=str(path), check=True, capture_output=True)
            res_email = subprocess.run(["git", "config", "user.email"], cwd=str(path), capture_output=True, text=True)
            if not res_email.stdout.strip():
                subprocess.run(["git", "config", "user.email", "torchlight@local.dev"], cwd=str(path), check=True, capture_output=True)
            res_name = subprocess.run(["git", "config", "user.name"], cwd=str(path), capture_output=True, text=True)
            if not res_name.stdout.strip():
                subprocess.run(["git", "config", "user.name", "Torchlight Agent"], cwd=str(path), check=True, capture_output=True)
        except Exception:
            pass
    return path


def ensure_project_initialized(project_path: Union[Path, str], create_git: bool = False) -> Path:
    """
    Ensure target project directory exists and has `.context-memory.json` persistent memory file auto-created.
    If create_git is True (e.g. when initializing a new target project or via AutonomousHarness),
    initializes a local Git repository.
    """
    path = Path(project_path).resolve()
    path.mkdir(parents=True, exist_ok=True)

    # 1. Ensure persistent memory file (.context-memory.json) exists and is a valid file
    memory_file = path / ".context-memory.json"
    if memory_file.exists() and memory_file.is_dir():
        try:
            import shutil
            shutil.rmtree(memory_file)
        except Exception:
            pass

    if not memory_file.exists():
        try:
            default_data = {
                "facts": [],
                "arch_decisions": [],
                "tried_and_failed": [],
                "tech_stack": [],
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "needle_ledger": [],
                "memory_objects": [],
            }
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # 2. Ensure local Git repo is initialized if requested
    if create_git:
        ensure_git_repository(path)

    # 3. Ensure .gitignore contains .torchlight/ to prevent dirty git status
    gitignore_file = path / ".gitignore"
    try:
        content = gitignore_file.read_text(encoding="utf-8") if gitignore_file.exists() else ""
        if ".torchlight" not in content:
            separator = "" if not content or content.endswith("\n") else "\n"
            gitignore_file.write_text(content + f"{separator}.torchlight/\n", encoding="utf-8")
    except Exception:
        pass

    return path



def init_new_project(project_path: Union[Path, str]) -> Path:
    """
    Explicitly initialize a new project directory with both persistent memory files
    and a local Git repository.
    """
    return ensure_project_initialized(project_path, create_git=True)


class ProjectMemory:
    def __init__(self, project_dir: Union[Path, str], auto_init: bool = True, create_git: bool = False):
        self.project_dir = Path(project_dir).resolve()
        self.memory_file = self.project_dir / ".context-memory.json"
        if auto_init:
            ensure_project_initialized(self.project_dir, create_git=create_git)

    def load(self) -> dict:
        # Self-heal persistent memory file on disk if deleted manually or invalid
        if not self.memory_file.exists() or not self.memory_file.is_file():
            ensure_project_initialized(self.project_dir)

        if self.memory_file.exists() and self.memory_file.is_file():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                # Corrupt or unparseable JSON on disk: self-heal by writing default structure
                default_data = {
                    "facts": [],
                    "arch_decisions": [],
                    "tried_and_failed": [],
                    "tech_stack": [],
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "needle_ledger": [],
                    "memory_objects": [],
                }
                try:
                    self.save(default_data)
                except Exception:
                    pass
                return default_data

        return {
            "facts": [],
            "arch_decisions": [],
            "tried_and_failed": [],
            "tech_stack": [],
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "needle_ledger": [],
            "memory_objects": [],
        }

    def save(self, data: dict) -> None:
        data["last_updated"] = datetime.now().isoformat()
        self.project_dir.mkdir(parents=True, exist_ok=True)

        temp_file = self.project_dir / f".context-memory.json.tmp.{os.getpid()}"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, self.memory_file)
        except Exception:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def update(self, fact: str, embedding: Optional[list] = None) -> None:
        data = self.load()
        if fact not in data.get("facts", []):
            data.setdefault("facts", []).append(fact)
        self.save(data)

    def update_tech_stack(self, techs: list[str]) -> None:
        data = self.load()
        for t in techs:
            if t not in data.get("tech_stack", []):
                data.setdefault("tech_stack", []).append(t)
        self.save(data)

    def persist_session_state(self, state: SessionState) -> None:
        data = self.load()
        data["intent"] = state.intent
        data["current_task"] = state.current_task
        data["next_steps"] = state.next_steps
        data["files_modified"] = state.files_modified
        data["files_read"] = state.files_read
        data["decisions"] = state.decisions
        data["arch_decisions"] = state.arch_decisions
        data["tech_stack"] = state.tech_stack
        data["failing_tests"] = state.failing_tests
        data["errors_seen"] = state.errors_seen
        data["tried_and_failed"] = state.tried_and_failed
        self.save(data)

