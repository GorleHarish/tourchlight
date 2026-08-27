"""Project memory persistence, dynamic task graph mutations, and AST knowledge querying."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from core.tools.fs_tools import _global_memory_mgr, tool_read_symbols_impl


def tool_save_memory_impl(args: dict, project_root: str) -> str:
    """SAVE_MEMORY — save a fact, decision, or failed strategy to project memory."""
    fact = str(args.get("entry") or args.get("fact", ""))
    category = args.get("category", "decision")
    channel_id = args.get("channel_id", "default")

    if not fact or not fact.strip():
        return "No memory entry provided."
    fact = fact.strip()
    if len(fact) > 300:
        return "Memory entry too long — keep under 300 chars."

    try:
        from core.memory.persistence import ProjectMemory
        from core.memory.models import MemoryObject
        from core.memory.embeddings import tokenize_text
        from datetime import datetime

        pm = ProjectMemory(Path(project_root))
        cat = category.lower()
        mem = pm.load()
        if "arch" in cat or "decision" in cat:
            if fact not in mem.get("arch_decisions", []):
                mem.setdefault("arch_decisions", []).append(fact)
            if fact not in mem.get("decisions", []):
                mem.setdefault("decisions", []).append(fact)
            pm.save(mem)
        elif "fail" in cat or "tried" in cat:
            if fact not in mem.get("tried_and_failed", []):
                mem.setdefault("tried_and_failed", []).append(fact)
            pm.save(mem)
        elif "tech" in cat or "stack" in cat:
            pm.update_tech_stack([fact])
        else:
            pm.update(fact)

        mo = MemoryObject(
            kind=category,
            summary=fact,
            source="SAVE_MEMORY",
            channel_id=channel_id,
            vector_tokens=tokenize_text(fact),
            timestamp=datetime.now(),
        )
        pm.add_memory_object(mo)

        if _global_memory_mgr is not None:
            _global_memory_mgr.record_memory(
                fact, category=category, channel_id=channel_id
            )

        return f"Saved to project memory ({cat}, channel={channel_id}): '{fact[:100]}'"
    except Exception as e:
        return f"Failed to write memory file: {e}"


def tool_update_task_graph_impl(args: dict, project_root: str) -> str:
    """UPDATE_TASK_GRAPH — dynamically mutate sub-tasks in .torchlight/goal_spec.json."""
    action = (args.get("action") or "").lower().strip()
    task_id = args.get("task_id") or args.get("id", "")
    description = args.get("description") or args.get("desc", "")
    depends_on = args.get("depends_on") or args.get("deps", [])
    target_files = args.get("target_files") or args.get("files", [])

    if not action:
        return "UPDATE_TASK_GRAPH requires 'action' argument (add_subtask, skip_task, update_status)."

    g_path = Path(project_root) / ".torchlight" / "goal_spec.json"
    if not g_path.exists():
        return f"No active goal specification found at {g_path}. Initialize goal first."

    try:
        with open(g_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tasks = data.get("tasks", [])
        phase = args.get("phase")
        task_num = args.get("task_number") or args.get("number")
        if action in ("add_subtask", "add_task"):
            existing_ids = [str(t.get("id") or "") for t in tasks]
            if not task_id:
                from core.tools.task_helpers import _stable_task_id

                task_id = _stable_task_id(existing_ids)
            new_task = {
                "id": task_id,
                "description": description or f"Sub-task {task_id}",
                "task_number": task_num,
                "phase": phase,
                "target_files": target_files
                if isinstance(target_files, list)
                else [target_files],
                "depends_on": depends_on
                if isinstance(depends_on, list)
                else [depends_on],
                "outputs_summary": None,
                "status": "pending",
                "attempts": 0,
                "max_attempts": 3,
                "failure_reasons": [],
                "completed_at": None,
            }
            tasks.append(new_task)
            data["tasks"] = tasks
            with open(g_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            from core.tools.task_helpers import (
                insert_task_into_plan,
                sync_workspace_tasks,
            )

            insert_task_into_plan(
                project_root, new_task["description"], status="pending"
            )
            sync_workspace_tasks(project_root)
            return f"Successfully added sub-task '{task_id}' to goal spec."

        elif action in ("skip_task", "skip"):
            if not task_id:
                return "UPDATE_TASK_GRAPH action 'skip_task' requires 'task_id'."
            found = False
            task_desc = ""
            from core.tools.task_helpers import _is_task_match
            for t in tasks:
                t_num = str(t.get("task_number") or "")
                if t.get("id") == task_id or t.get("description") == task_id or (t_num and t_num == str(task_id)) or _is_task_match(str(task_id), str(t.get("description") or "")):
                    t["status"] = "skipped"
                    task_desc = t.get("description") or t.get("id")
                    found = True
                    break
            if not found:
                return f"Task '{task_id}' not found in goal spec."
            with open(g_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            from core.tools.task_helpers import mark_task_status

            mark_task_status(project_root, task_desc or task_id, status="skipped")
            return f"Task '{task_id}' marked as SKIPPED."

        elif action in ("update_status", "status"):
            status_val = args.get("status", "pending")
            found = False
            task_desc = ""
            from core.tools.task_helpers import _is_task_match
            for t in tasks:
                t_num = str(t.get("task_number") or "")
                if t.get("id") == task_id or t.get("description") == task_id or (t_num and t_num == str(task_id)) or _is_task_match(str(task_id), str(t.get("description") or "")):
                    t["status"] = status_val
                    task_desc = t.get("description") or t.get("id")
                    found = True
                    break
            if not found:
                return f"Task '{task_id}' not found in goal spec."
            with open(g_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            from core.tools.task_helpers import mark_task_status

            mark_task_status(project_root, task_desc or task_id, status=status_val)
            return f"Task '{task_id}' status updated to '{status_val}'."

        else:
            return f"Unsupported UPDATE_TASK_GRAPH action: {action}. Supported: add_subtask, skip_task, update_status."

    except Exception as e:
        return f"Failed to update task graph: {e}"

def tool_search_ast_impl(args: dict, project_root: str) -> str:
    """Query AST Knowledge Graph (search, path, subgraph, structure, update, summary)."""
    query = str(args.get("query", "")).strip().lstrip("@")
    action = str(args.get("action", "search")).strip().lower()
    top_k = int(args.get("top_k", 5))

    from core.flashlight.graph_engine import get_project_graph
    from core.utils.image_utils import is_image_file

    if query and is_image_file(query):
        return f"ℹ️ '{os.path.basename(query)}' is an image file and does not contain AST code symbols. Visual context is attached for vision models, or use VIEW_IMAGE to inspect."

    graph = get_project_graph(project_root)

    if action in ("update", "reindex", "build"):
        gdict = graph.build()
        return f"✅ AST Graph re-indexed successfully: {gdict['node_count']} nodes, {gdict['edge_count']} edges saved to `.torchlight/graph.json`."
    elif action in (
        "search",
        "query",
        "semantic",
        "signature",
        "signatures",
        "symbol",
        "symbols",
        "definition",
        "definitions",
    ):
        if not query:
            return graph.get_structure()
        res = graph.query(query, top_k=top_k)
        if "No AST graph nodes found" in res:
            graph.build()
            rebuilt_res = graph.query(query, top_k=top_k)
            if "No AST graph nodes found" not in rebuilt_res:
                return rebuilt_res
            if query.lower() in ("main", "app", "index", "root"):
                return graph.get_structure()
            possible_file = os.path.join(project_root, query) if not os.path.isabs(query) else query
            if os.path.exists(possible_file) or "." in query or "/" in query or "\\" in query:
                sym_res = tool_read_symbols_impl({"path": query}, project_root)
                if not sym_res.startswith("Error") and "File not found" not in sym_res and "requires a file path" not in sym_res:
                    return f"AST Node search fallback (READ_SYMBOLS for {query}):\n{sym_res}"
            return rebuilt_res
        return res
    elif action in ("path", "find_path"):
        target = str(args.get("target", args.get("to", ""))).strip().lstrip("@")
        if not target and "," in query:
            parts = query.split(",", 1)
            query, target = parts[0].strip().lstrip("@"), parts[1].strip().lstrip("@")
        res = graph.find_path(query, target)
        if "Path search failed" in res:
            graph.build()
            return graph.find_path(query, target)
        return res
    elif action in ("subgraph", "sub_graph", "deps", "depend", "dependencies", "graph"):
        res = graph.get_subgraph(query)
        if "not found in AST index" in res:
            graph.build()
            return graph.get_subgraph(query)
        return res
    elif action in ("structure", "project", "get_project_structure", "get_structure"):
        return graph.get_structure()
    elif action in ("summary", "info"):
        return f"Project AST Graph: {graph.graph_file}\nNodes: {len(graph.nodes)} | Edges: {len(graph.edges)}"
    else:
        res = graph.query(query, top_k=top_k)
        if "No AST graph nodes found" in res:
            graph.build()
            rebuilt_res = graph.query(query, top_k=top_k)
            if "No AST graph nodes found" not in rebuilt_res:
                return rebuilt_res
            possible_file = os.path.join(project_root, query) if not os.path.isabs(query) else query
            if os.path.exists(possible_file) or "." in query or "/" in query:
                sym_res = tool_read_symbols_impl({"path": query}, project_root)
                if not sym_res.startswith("Error") and "File not found" not in sym_res and "requires a file path" not in sym_res:
                    return f"AST Node search fallback (READ_SYMBOLS for {query}):\n{sym_res}"
            return rebuilt_res
        return res
