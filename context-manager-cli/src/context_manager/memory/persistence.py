import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Union
import math
import re

from .models import Message, MessageRole, SessionState, MemoryNeedle, MemoryObject

try:
    from core.memory.persistence import (
        ensure_project_initialized,
        init_new_project,
        ensure_git_repository,
    )
except ImportError:

    def ensure_git_repository(project_path: Union[Path, str]) -> Path:
        path = Path(project_path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        git_dir = path / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(["git", "init"], cwd=str(path), check=True, capture_output=True)
                res_email = subprocess.run(
                    ["git", "config", "user.email"], cwd=str(path), capture_output=True, text=True
                )
                if not res_email.stdout.strip():
                    subprocess.run(
                        ["git", "config", "user.email", "torchlight@local.dev"],
                        cwd=str(path),
                        check=True,
                        capture_output=True,
                    )
                res_name = subprocess.run(
                    ["git", "config", "user.name"], cwd=str(path), capture_output=True, text=True
                )
                if not res_name.stdout.strip():
                    subprocess.run(
                        ["git", "config", "user.name", "Torchlight Agent"],
                        cwd=str(path),
                        check=True,
                        capture_output=True,
                    )
            except Exception:
                pass
        return path

    def ensure_project_initialized(
        project_path: Union[Path, str], create_git: bool = False
    ) -> Path:
        path = Path(project_path).resolve()
        path.mkdir(parents=True, exist_ok=True)

        memory_file = path / ".context-memory.json"
        if not memory_file.exists():
            try:
                default_data = {
                    "facts": [],
                    "arch_decisions": [],
                    "tried_and_failed": [],
                    "tech_stack": [],
                    "needle_ledger": [],
                    "memory_objects": [],
                    "created": datetime.now().isoformat(),
                }
                with open(memory_file, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        if create_git:
            ensure_git_repository(path)

        try:
            skills_dir = path / ".agents" / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        return path

    def init_new_project(project_path: Union[Path, str]) -> Path:
        return ensure_project_initialized(project_path, create_git=True)


class SessionPersistence:
    def __init__(self, session_dir: Optional[Path] = None):
        if session_dir is None:
            self.session_dir = Path.home() / ".context-manager" / "sessions"
        else:
            self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def save_session(
        self,
        memory: "TieredMemory",
        session_name: Optional[str] = None,
        project_path: Optional[str] = None,
    ) -> str:
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
                # Core
                "intent": s.intent,
                "current_task": s.current_task,
                "next_steps": s.next_steps,
                # File tracking
                "files_modified": s.files_modified,
                "files_read": s.files_read,
                # Decisions
                "decisions": [str(x) for x in s.decisions],
                "arch_decisions": [str(x) for x in s.arch_decisions],
                # Dev-session specific
                "tech_stack": s.tech_stack,
                "failing_tests": s.failing_tests,
                "errors_seen": s.errors_seen,
                "dependencies_added": s.dependencies_added,
                "tried_and_failed": s.tried_and_failed,
                "active_file": s.active_file,
                "current_blocker": s.current_blocker,
                # Long-term memory
                "semantic_context": s.semantic_context,
                "needle_ledger": [
                    {
                        "kind": item.kind,
                        "value": item.value,
                        "source": item.source,
                        "weight": item.weight,
                        "timestamp": item.timestamp.isoformat(),
                    }
                    for item in s.needle_ledger
                ],
                "memory_objects": [
                    {
                        "kind": item.kind,
                        "summary": item.summary,
                        "source": item.source,
                        "file_paths": item.file_paths,
                        "symbols": item.symbols,
                        "commands": item.commands,
                        "errors": item.errors,
                        "text": item.text,
                        "score": item.score,
                        "embedding": item.embedding,
                        "timestamp": item.timestamp.isoformat(),
                    }
                    for item in s.memory_objects
                ],
            },
            "messages": messages_data,
            "total_tokens": memory.total_tokens,
        }

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        return str(session_file)

    def load_session(self, session_name: str, memory: "TieredMemory") -> bool:
        session_file = self.session_dir / f"{session_name}.json"
        if not session_file.exists():
            candidates = list(self.session_dir.glob(f"{session_name}*.json"))
            if candidates:
                session_file = candidates[0]
            else:
                return False

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            memory.clear()

            sd = data.get("state", {})
            memory.state = SessionState(
                # Core
                intent=sd.get("intent", ""),
                current_task=sd.get("current_task", ""),
                next_steps=sd.get("next_steps", []),
                # File tracking
                files_modified=sd.get("files_modified", []),
                files_read=sd.get("files_read", []),
                # Decisions
                decisions=[str(x) for x in sd.get("decisions", [])],
                arch_decisions=[str(x) for x in sd.get("arch_decisions", [])],
                # Dev-session specific
                tech_stack=sd.get("tech_stack", []),
                failing_tests=sd.get("failing_tests", []),
                errors_seen=sd.get("errors_seen", []),
                dependencies_added=sd.get("dependencies_added", []),
                tried_and_failed=sd.get("tried_and_failed", []),
                active_file=sd.get("active_file", ""),
                current_blocker=sd.get("current_blocker", ""),
                # Long-term memory
                semantic_context=sd.get("semantic_context", []),
                needle_ledger=[
                    MemoryNeedle(
                        kind=item.get("kind", "general"),
                        value=item.get("value", ""),
                        source=item.get("source", ""),
                        weight=item.get("weight", 1.0),
                        timestamp=datetime.fromisoformat(item["timestamp"])
                        if item.get("timestamp")
                        else datetime.now(),
                    )
                    for item in sd.get("needle_ledger", [])
                    if item.get("value")
                ],
                memory_objects=[
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
                        timestamp=datetime.fromisoformat(item["timestamp"])
                        if item.get("timestamp")
                        else datetime.now(),
                    )
                    for item in sd.get("memory_objects", [])
                    if item.get("summary")
                ],
            )

            for msg_data in data.get("messages", []):
                try:
                    role = MessageRole(msg_data["role"])
                except (ValueError, KeyError):
                    role = MessageRole.USER

                msg = Message(
                    role=role,
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    token_count=msg_data.get("token_count", 0),
                    metadata=msg_data.get("metadata", {}),
                )
                memory.messages.append(msg)

            # Recalculate token count from loaded messages
            memory._cached_msg_tokens = sum(m.token_count for m in memory.messages)
            if hasattr(memory, "_total_tokens"):
                try:
                    delattr(memory, "_total_tokens")
                except AttributeError:
                    pass
            return True

        except (json.JSONDecodeError, KeyError):
            return False

    def list_sessions(self) -> list[dict]:
        sessions = []
        for session_file in sorted(self.session_dir.glob("*.json"), reverse=True):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sd = data.get("state", {})
                sessions.append(
                    {
                        "name": data.get("name", session_file.stem),
                        "created": data.get("created", ""),
                        "project_path": data.get("project_path", ""),
                        "message_count": len(data.get("messages", [])),
                        "total_tokens": data.get("total_tokens", 0),
                        # Surface key dev-session fields for the session list view
                        "tech_stack": sd.get("tech_stack", []),
                        "active_file": sd.get("active_file", ""),
                        "failing_tests": sd.get("failing_tests", []),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return sessions

    def delete_session(self, session_name: str) -> bool:
        session_file = self.session_dir / f"{session_name}.json"
        if session_file.exists():
            session_file.unlink()
            return True
        return False


class ProjectMemory:
    def __init__(self, project_path: Optional[Union[Path, str]] = None, auto_init: bool = True):
        self.project_path = Path(project_path).resolve() if project_path else None
        self.memory_file = (
            (self.project_path / ".context-memory.json") if self.project_path else None
        )
        self._cache = None
        self._mtime = 0.0
        if self.project_path and auto_init:
            ensure_project_initialized(self.project_path)

    def load(self) -> dict:
        if not self.memory_file or not self.memory_file.exists():
            return self._default_memory()
        try:
            # Basic mtime caching to avoid redundant disk reads during polling
            curr_mtime = self.memory_file.stat().st_mtime
            if self._cache is not None and curr_mtime <= self._mtime:
                return self._cache

            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache = data
                self._mtime = curr_mtime
                return data
        except (json.JSONDecodeError, Exception):
            return self._default_memory()

    def save(self, memory: dict) -> None:
        if not self.memory_file:
            return
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=2, ensure_ascii=False)

            # Update cache to keep it in sync without re-reading from disk
            self._cache = memory
            self._mtime = self.memory_file.stat().st_mtime
        except Exception:
            pass

    def update(
        self, fact: str, embedding: Optional[list] = None, memory: Optional[dict] = None
    ) -> dict:
        """Add a fact (and optional embedding) to project memory.

        Signature accepts both the old positional style:
            update(fact, embedding)
        and the keyword style described in the README:
            update(key, value)  →  update(fact=key, embedding=None)
        """
        if memory is None:
            memory = self.load()
        entry: dict = {
            "text": fact,
            "timestamp": datetime.now().isoformat(),
        }
        if embedding is not None:
            entry["embedding"] = embedding
        memory.setdefault("facts", []).append(entry)
        self.save(memory)
        return memory

    def search(
        self, query_embedding: list[float], top_k: int = 2, threshold: float = 0.70
    ) -> list[dict]:
        facts = self.load().get("facts", [])
        if not facts:
            return []

        def cosine(v1, v2):
            if not v1 or not v2:
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

        scored = [
            (cosine(query_embedding, f.get("embedding", [])), f)
            for f in facts
            if f.get("embedding")
        ]
        scored = [(s, f) for s, f in scored if s >= threshold]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:top_k]]

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: Optional[list[float]] = None,
        top_k: int = 4,
    ) -> list[dict]:
        memory = self.load()
        query_terms = self._normalize_terms(query_text)
        scored: list[tuple[float, dict]] = []

        for item in memory.get("memory_objects", []):
            haystack = " ".join(
                [
                    item.get("summary", ""),
                    item.get("text", ""),
                    " ".join(item.get("file_paths", [])),
                    " ".join(item.get("symbols", [])),
                    " ".join(item.get("commands", [])),
                    " ".join(item.get("errors", [])),
                ]
            )
            lexical = self._lexical_score(query_terms, haystack)
            semantic = 0.0
            if query_embedding and item.get("embedding"):
                semantic = self._cosine(query_embedding, item.get("embedding", []))
            score = lexical + (0.35 * semantic) + float(item.get("score", 1.0)) * 0.02
            if score > 0:
                scored.append((score, item))

        for item in memory.get("needle_ledger", []):
            haystack = " ".join(
                [item.get("kind", ""), item.get("value", ""), item.get("source", "")]
            )
            score = (
                self._lexical_score(query_terms, haystack) + float(item.get("weight", 1.0)) * 0.01
            )
            if score > 0:
                scored.append(
                    (
                        score,
                        {
                            "kind": "needle",
                            "summary": item.get("value", ""),
                            "source": item.get("source", ""),
                            "file_paths": [],
                            "symbols": [],
                            "commands": [],
                            "errors": [],
                            "text": item.get("value", ""),
                            "score": item.get("weight", 1.0),
                        },
                    )
                )

        # Backward compatibility: also search legacy "facts" format
        for item in memory.get("facts", []):
            text = item.get("text", "")
            if not text:
                continue
            score = self._lexical_score(query_terms, text)
            if score > 0:
                scored.append(
                    (
                        score,
                        {
                            "kind": "fact",
                            "summary": text[:220],
                            "source": item.get("source", "save_memory"),
                            "file_paths": [],
                            "symbols": [],
                            "commands": [],
                            "errors": [],
                            "text": text,
                            "score": 1.0,
                        },
                    )
                )

        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for _, item in scored:
            key = (item.get("kind", ""), item.get("summary", item.get("text", "")))
            if key in seen:
                continue
            seen.add(key)
            results.append(item)
            if len(results) >= top_k:
                break
        return results

    def add_memory_object(self, memory_object: dict, memory: Optional[dict] = None) -> dict:
        if memory is None:
            memory = self.load()
        memory.setdefault("memory_objects", []).append(memory_object)
        memory["memory_objects"] = memory["memory_objects"][-160:]
        self.save(memory)
        return memory

    def add_needle(self, needle: dict, memory: Optional[dict] = None) -> dict:
        if memory is None:
            memory = self.load()
        memory.setdefault("needle_ledger", []).append(needle)
        memory["needle_ledger"] = memory["needle_ledger"][-300:]
        self.save(memory)
        return memory

    def persist_session_state(self, state: SessionState):
        """Merge current session's key findings into long-term project memory."""
        mem = self.load()

        def _exists(path_str: str) -> bool:
            if not self.project_path:
                return True  # Fallback
            try:
                p = Path(path_str)
                if not p.is_absolute():
                    p = self.project_path / p
                return p.exists()
            except Exception:
                return False

        # Unique merge for architectural decisions
        existing_arch = set(str(x) for x in mem.get("arch_decisions", []))
        for d in state.arch_decisions:
            d = str(d).strip()
            if d and d not in existing_arch:
                mem.setdefault("arch_decisions", []).append(d)
                existing_arch.add(d)

        # Unique merge for tried & failed
        existing_failed = set(str(x) for x in mem.get("tried_and_failed", []))
        for f in state.tried_and_failed:
            f = str(f).strip()
            if f and f not in existing_failed:
                mem.setdefault("tried_and_failed", []).append(f)
                existing_failed.add(f)

        # Merge tech stack
        existing_tech = set(str(x) for x in mem.get("tech_stack", []))
        for t in state.tech_stack:
            t = str(t).strip()
            if t and t not in existing_tech:
                mem.setdefault("tech_stack", []).append(t)
                existing_tech.add(t)

        existing_needles = {
            (item.get("kind", ""), item.get("value", "")) for item in mem.get("needle_ledger", [])
        }
        for needle in state.needle_ledger[-200:]:
            if needle.kind == "file" and not _exists(needle.value):
                continue
            key = (needle.kind, needle.value)
            if key in existing_needles:
                continue
            mem.setdefault("needle_ledger", []).append(
                {
                    "kind": needle.kind,
                    "value": needle.value,
                    "source": needle.source,
                    "weight": needle.weight,
                    "timestamp": needle.timestamp.isoformat(),
                }
            )

        existing_objects = {
            (item.get("kind", ""), item.get("summary", ""))
            for item in mem.get("memory_objects", [])
        }
        for obj in state.memory_objects[-120:]:
            # Filter internal file paths
            if obj.file_paths:
                obj.file_paths = [f for f in obj.file_paths if _exists(f)]

            key = (obj.kind, obj.summary)
            if key in existing_objects:
                continue
            mem.setdefault("memory_objects", []).append(
                {
                    "kind": obj.kind,
                    "summary": obj.summary,
                    "source": obj.source,
                    "file_paths": obj.file_paths,
                    "symbols": obj.symbols,
                    "commands": obj.commands,
                    "errors": obj.errors,
                    "text": obj.text,
                    "score": obj.score,
                    "embedding": obj.embedding,
                    "timestamp": obj.timestamp.isoformat(),
                }
            )

        # Cleanup existing long-term needles/objects from deleted files
        mem["needle_ledger"] = [
            n
            for n in mem.get("needle_ledger", [])
            if n.get("kind") != "file" or _exists(n.get("value", ""))
        ]
        for obj in mem.get("memory_objects", []):
            if obj.get("file_paths"):
                obj["file_paths"] = [f for f in obj["file_paths"] if _exists(f)]

        mem["last_updated"] = datetime.now().isoformat()
        mem["needle_ledger"] = mem.get("needle_ledger", [])[-300:]
        mem["memory_objects"] = mem.get("memory_objects", [])[-160:]
        self.save(mem)

    def _default_memory(self) -> dict:
        return {
            "facts": [],
            "arch_decisions": [],
            "tried_and_failed": [],
            "tech_stack": [],
            "needle_ledger": [],
            "memory_objects": [],
            "created": datetime.now().isoformat(),
        }

    def update_tech_stack(self, tech_stack: list[str]):
        memory = self.load()
        existing = set(memory.get("tech_stack", []))
        new_tech = [t for t in tech_stack if t not in existing]
        if new_tech:
            memory["tech_stack"] = list(existing) + new_tech
            self.save(memory)

    @staticmethod
    def _normalize_terms(text: str) -> list[str]:
        return [
            term for term in re.findall(r"[A-Za-z0-9_./:-]+", (text or "").lower()) if len(term) > 2
        ]

    @staticmethod
    def _lexical_score(query_terms: list[str], haystack: str) -> float:
        if not query_terms or not haystack:
            return 0.0
        lower = haystack.lower()
        score = 0.0
        for term in query_terms:
            if term in lower:
                score += 1.0
                if "/" in term or "." in term or "::" in term:
                    score += 0.8
        return score

    @staticmethod
    def _cosine(v1: list[float], v2: list[float]) -> float:
        if not v1 or not v2:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0
