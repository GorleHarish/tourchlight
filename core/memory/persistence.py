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

    def save_session(
        self,
        memory,
        session_name: Optional[str] = None,
        project_path: Optional[str] = None,
    ) -> str:
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_file = self.session_dir / f"{session_name}.json"
        messages_data = [
            {
                "role": msg.role.value
                if isinstance(msg.role, MessageRole)
                else str(msg.role),
                "content": msg.content,
                "images": getattr(msg, "images", []),
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
                "decisions": [str(x) for x in s.decisions],
                "arch_decisions": [str(x) for x in s.arch_decisions],
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
                sessions.append(
                    {
                        "name": data.get("name", f.stem),
                        "created": data.get("created", ""),
                        "message_count": len(data.get("messages", [])),
                        "total_tokens": data.get("total_tokens", 0),
                    }
                )
            except Exception:
                continue
        return sessions


def ensure_git_repository(
    project_path: Union[Path, str], force_init: bool = False
) -> Path:
    """
    Ensure target project directory exists and has a local Git repository initialized.
    Configures fallback user email and name if unconfigured.
    """
    path = Path(project_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    git_dir = path / ".git"
    fresh_init = not git_dir.exists()
    if not git_dir.exists() or force_init:
        try:
            subprocess.run(
                ["git", "init"], cwd=str(path), check=True, capture_output=True, timeout=5
            )
            res_email = subprocess.run(
                ["git", "config", "user.email"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if not res_email.stdout.strip():
                subprocess.run(
                    ["git", "config", "user.email", "torchlight@local.dev"],
                    cwd=str(path),
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
            res_name = subprocess.run(
                ["git", "config", "user.name"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if not res_name.stdout.strip():
                subprocess.run(
                    ["git", "config", "user.name", "Torchlight Agent"],
                    cwd=str(path),
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
            # Mark the repo as harness-managed ONLY when the harness itself
            # created it (fresh init), never for pre-existing user repositories.
            # Gates destructive blanket reverts in AutonomousHarness.
            if fresh_init:
                _write_harness_marker(path)
        except Exception:
            pass
    return path


def _write_harness_marker(project_path: Path) -> None:
    """Write a marker proving the harness itself initialized this git repo.

    Only written when the harness performs a fresh ``git init``. Pre-existing
    user repositories never receive the marker, so ``allow_blanket_revert``
    cannot destroy user work by accident.
    """
    try:
        marker_dir = project_path / ".torchlight"
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / ".harness_managed").write_text(
            "Managed by the Torchlight AutonomousHarness.\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def ensure_project_initialized(
    project_path: Union[Path, str], create_git: bool = False
) -> Path:
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
                "user_preferences": {
                    "compression_aggressiveness": "medium",
                    "enable_deduplication": True,
                    "dedup_similarity_threshold": 0.85,
                },
                "dedup_cache": {},
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
        content = (
            gitignore_file.read_text(encoding="utf-8")
            if gitignore_file.exists()
            else ""
        )
        if ".torchlight" not in content:
            separator = "" if not content or content.endswith("\n") else "\n"
            gitignore_file.write_text(
                content + f"{separator}.torchlight/\n", encoding="utf-8"
            )
    except Exception:
        pass

    # 4. Ensure .agents/skills directory exists for modular agent skills
    try:
        skills_dir = path / ".agents" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
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
    def __init__(
        self,
        project_dir: Union[Path, str],
        auto_init: bool = True,
        create_git: bool = False,
    ):
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
        data["next_steps"] = [str(x) for x in state.next_steps]
        data["files_modified"] = [str(x) for x in state.files_modified]
        data["files_read"] = [str(x) for x in state.files_read]
        data["decisions"] = [str(x) for x in state.decisions]
        data["arch_decisions"] = [str(x) for x in state.arch_decisions]
        data["tech_stack"] = [str(x) for x in state.tech_stack]
        data["failing_tests"] = [str(x) for x in state.failing_tests]
        data["errors_seen"] = [str(x) for x in state.errors_seen]
        data["tried_and_failed"] = [str(x) for x in state.tried_and_failed]

        if hasattr(state, "memory_objects") and state.memory_objects:
            objs = []
            for mo in state.memory_objects:
                objs.append(
                    {
                        "kind": mo.kind,
                        "summary": mo.summary,
                        "source": mo.source,
                        "file_paths": mo.file_paths,
                        "symbols": mo.symbols,
                        "commands": mo.commands,
                        "errors": mo.errors,
                        "text": mo.text,
                        "score": mo.score,
                        "embedding": mo.embedding,
                        "channel_id": getattr(mo, "channel_id", "default"),
                        "user_id": getattr(mo, "user_id", None),
                        "session_id": getattr(mo, "session_id", None),
                        "vector_tokens": getattr(mo, "vector_tokens", []),
                        "ast_symbols": getattr(mo, "ast_symbols", []),
                        "timestamp": mo.timestamp.isoformat()
                        if isinstance(mo.timestamp, datetime)
                        else str(mo.timestamp),
                    }
                )
            data["memory_objects"] = objs

        self.save(data)

    def add_memory_object(self, mem: MemoryObject) -> None:
        data = self.load()
        objs = data.get("memory_objects", [])
        obj_dict = {
            "kind": mem.kind,
            "summary": mem.summary,
            "source": mem.source,
            "file_paths": mem.file_paths,
            "symbols": mem.symbols,
            "commands": mem.commands,
            "errors": mem.errors,
            "text": mem.text,
            "score": mem.score,
            "embedding": mem.embedding,
            "channel_id": getattr(mem, "channel_id", "default"),
            "user_id": getattr(mem, "user_id", None),
            "session_id": getattr(mem, "session_id", None),
            "vector_tokens": getattr(mem, "vector_tokens", []),
            "ast_symbols": getattr(mem, "ast_symbols", []),
            "timestamp": mem.timestamp.isoformat()
            if isinstance(mem.timestamp, datetime)
            else str(mem.timestamp),
        }
        # Deduplicate by summary
        if not any(
            o.get("summary") == mem.summary for o in objs if isinstance(o, dict)
        ):
            objs.append(obj_dict)
            data["memory_objects"] = objs
            self.save(data)

    def get_memory_objects(
        self, channel_id: Optional[str] = None
    ) -> list[MemoryObject]:
        data = self.load()
        raw_objs = data.get("memory_objects", [])
        result = []
        for item in raw_objs:
            if not isinstance(item, dict):
                continue
            ch = item.get("channel_id", "default")
            if channel_id and ch and ch not in ("default", channel_id):
                continue
            try:
                ts = (
                    datetime.fromisoformat(item["timestamp"])
                    if item.get("timestamp")
                    else datetime.now()
                )
            except Exception:
                ts = datetime.now()

            result.append(
                MemoryObject(
                    kind=item.get("kind", "summary"),
                    summary=item.get("summary", ""),
                    source=item.get("source", ""),
                    file_paths=item.get("file_paths", []),
                    symbols=item.get("symbols", []),
                    commands=item.get("commands", []),
                    errors=item.get("errors", []),
                    text=item.get("text", ""),
                    score=item.get("score", 1.0),
                    embedding=item.get("embedding", []),
                    channel_id=ch,
                    user_id=item.get("user_id"),
                    session_id=item.get("session_id"),
                    vector_tokens=item.get("vector_tokens", []),
                    ast_symbols=item.get("ast_symbols", []),
                    timestamp=ts,
                )
            )
        return result

    def search_memory(
        self, query: str, channel_id: Optional[str] = None, top_k: int = 5
    ) -> list[tuple[MemoryObject, float]]:
        from .embeddings import HybridMemoryRetriever

        objects = self.get_memory_objects(channel_id=channel_id)
        retriever = HybridMemoryRetriever()
        return retriever.retrieve(query, objects, channel_id=channel_id, top_k=top_k)

    def load_user_preferences(self) -> dict:
        """Load user preferences from project memory."""
        data = self.load()
        return data.get("user_preferences", {
            "compression_aggressiveness": "medium",
            "enable_deduplication": True,
            "dedup_similarity_threshold": 0.85,
        })

    def save_user_preferences(self, preferences: dict) -> None:
        """Save user preferences to project memory."""
        data = self.load()
        data["user_preferences"] = preferences
        self.save(data)

    def load_dedup_cache(self) -> dict:
        """Load deduplication cache from project memory."""
        data = self.load()
        return data.get("dedup_cache", {})

    def save_dedup_cache(self, cache: dict) -> None:
        """Save deduplication cache to project memory."""
        data = self.load()
        data["dedup_cache"] = cache
        self.save(data)

    def export_context_profile(self, profile_path: Union[Path, str]) -> None:
        """Export current context profile and memory config to a file."""
        profile_path = Path(profile_path)
        data = {
            "exported_at": datetime.now().isoformat(),
            "user_preferences": self.load_user_preferences(),
            "memory_objects": [
                {
                    "kind": mo.kind,
                    "summary": mo.summary,
                    "source": mo.source,
                    "file_paths": mo.file_paths,
                    "timestamp": mo.timestamp.isoformat() if isinstance(mo.timestamp, datetime) else str(mo.timestamp),
                }
                for mo in self.get_memory_objects()[:50]
            ],
        }
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_context_profile(self, profile_path: Union[Path, str]) -> dict:
        """Import context profile from a file and merge into project memory."""
        profile_path = Path(profile_path)
        if not profile_path.exists():
            return {}
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("user_preferences"):
                self.save_user_preferences(data["user_preferences"])
            return data
        except Exception:
            return {}
