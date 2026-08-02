import os
import io
import sys
import re
import signal
import traceback

try:
    import kuzu
except ImportError:
    kuzu = None
from contextlib import redirect_stdout, redirect_stderr
from typing import Callable, Optional
from rlm_optimized.config import AST_DB_DIRNAME

_encoder = None


def _resolve_ast_db_path(project_root: str) -> str:
    """Resolve the AST graph DB path relative to the active project_root —
    never the process cwd — so a /cd to a different workspace can't
    silently query a stale or wrong-project graph."""
    return os.path.join(project_root or os.getcwd(), AST_DB_DIRNAME)


def _ast_db_missing_message() -> str:
    return (
        "⚠️ No AST knowledge graph indexed for this workspace yet. "
        "Ask the user to run /index in the TUI to build it, or continue "
        "using LIST_DIR / GREP / READ_FILE instead."
    )


def _get_encoder():
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder


class _KuzuConnectionPool:
    """Singleton manager for active Kùzu graph database connections."""

    _instance: Optional["_KuzuConnectionPool"] = None

    def __init__(self):
        self.db_path: Optional[str] = None
        self.db = None
        self.conn = None

    @classmethod
    def get_instance(cls) -> "_KuzuConnectionPool":
        if cls._instance is None:
            cls._instance = _KuzuConnectionPool()
        return cls._instance

    def get_connection(self, project_root: str = "."):
        if kuzu is None:
            return None
        target_path = _resolve_ast_db_path(project_root)
        if not os.path.isdir(target_path):
            return None

        if self.db_path != target_path or self.conn is None:
            self.close()
            try:
                self.db = kuzu.Database(target_path, buffer_pool_size=268435456)
                self.conn = kuzu.Connection(self.db)
                self.db_path = target_path
            except Exception:
                self.close()
                return None
        return self.conn

    def close(self):
        self.conn = None
        self.db = None
        self.db_path = None


def get_kuzu_connection(project_root: str = "."):
    return _KuzuConnectionPool.get_instance().get_connection(project_root)


def get_project_structure(project_root: str = "."):
    db_path = _resolve_ast_db_path(project_root)
    if not os.path.isdir(db_path):
        return _ast_db_missing_message()
    conn = get_kuzu_connection(project_root)
    if conn is None:
        return f"Error opening Kuzu graph database at {db_path}."
    try:
        results = conn.execute(
            "MATCH (f:File)-[:File_HAS_CLASS]->(c:ClassDef) RETURN f.filepath, c.name"
        )
        structure_map = {}
        while results.has_next():
            row = results.get_next()
            filepath = row[0]
            structure_map.setdefault(filepath, []).append(f"[Class] {row[1]}")

        results2 = conn.execute(
            "MATCH (f:File)-[:File_HAS_FUNCTION]->(fn:FunctionDef) RETURN f.filepath, fn.name"
        )
        while results2.has_next():
            row = results2.get_next()
            filepath = row[0]
            structure_map.setdefault(filepath, []).append(f"[Function] {row[1]}")

        structure = [f"{fp}: {', '.join(items)}" for fp, items in structure_map.items()]
        return "\n".join(structure) if structure else "No AST indexed."
    except Exception as e:
        return f"Error retrieving project structure: {e}"


def get_class_signature(class_name, project_root: str = "."):
    db_path = _resolve_ast_db_path(project_root)
    if not os.path.isdir(db_path):
        return _ast_db_missing_message()
    conn = get_kuzu_connection(project_root)
    if conn is None:
        return f"Error opening Kuzu graph database at {db_path}."
    try:
        results = conn.execute(
            "MATCH (c:ClassDef {name: $name}) RETURN c.docstring LIMIT 1",
            parameters={"name": class_name},
        )
        if not results.has_next():
            return f"Class {class_name} not found."

        docstring = results.get_next()[0]
        methods_res = conn.execute(
            "MATCH (c:ClassDef {name: $name})-[:Class_HAS_FUNCTION]->(fn:FunctionDef) RETURN fn.name, fn.args",
            parameters={"name": class_name},
        )

        sig = [f"class {class_name}:"]
        if docstring:
            sig.append(f'    """{docstring}"""')
        while methods_res.has_next():
            m = methods_res.get_next()
            sig.append(f"    def {m[0]}({m[1]})")

        return "\n".join(sig)
    except Exception as e:
        return f"Error retrieving class signature: {e}"


def get_function_ast(func_name, project_root: str = "."):
    db_path = _resolve_ast_db_path(project_root)
    if not os.path.isdir(db_path):
        return _ast_db_missing_message()
    conn = get_kuzu_connection(project_root)
    if conn is None:
        return f"Error opening Kuzu graph database at {db_path}."
    try:
        res = conn.execute(
            "MATCH (fn:FunctionDef {name: $name}) RETURN fn.ast_dump LIMIT 1",
            parameters={"name": func_name},
        )
        if res.has_next():
            return res.get_next()[0]
        return f"Function {func_name} not found."
    except Exception as e:
        return f"Error retrieving function AST: {e}"


def get_function_source(func_name, project_root: str = "."):
    db_path = _resolve_ast_db_path(project_root)
    if not os.path.isdir(db_path):
        return _ast_db_missing_message()
    conn = get_kuzu_connection(project_root)
    if conn is None:
        return f"Error opening Kuzu graph database at {db_path}."
    try:
        res = conn.execute(
            "MATCH (fn:FunctionDef {name: $name}) RETURN fn.source_code LIMIT 1",
            parameters={"name": func_name},
        )
        if res.has_next():
            return res.get_next()[0]
        return f"Function {func_name} not found."
    except Exception as e:
        return f"Error retrieving function source: {e}"


def semantic_search(query_string, top_k=3, project_root: str = "."):
    db_path = _resolve_ast_db_path(project_root)
    if not os.path.isdir(db_path):
        return _ast_db_missing_message()
    conn = get_kuzu_connection(project_root)
    if conn is None:
        return f"Error opening Kuzu graph database at {db_path}."
    try:
        encoder = _get_encoder()
        query_emb = encoder.encode(query_string).tolist()

        q_class = "MATCH (c:ClassDef) RETURN c.id, c.name, array_cosine_similarity(c.embedding, $emb) AS sim ORDER BY sim DESC LIMIT $k"
        res_class = conn.execute(q_class, parameters={"emb": query_emb, "k": top_k})
        class_results = []
        while res_class.has_next():
            row = res_class.get_next()
            class_results.append(
                f"[Class] ID: {row[0]}, Name: {row[1]}, Sim: {row[2]:.3f}"
            )

        q_func = "MATCH (fn:FunctionDef) RETURN fn.id, fn.name, array_cosine_similarity(fn.embedding, $emb) AS sim ORDER BY sim DESC LIMIT $k"
        res_func = conn.execute(q_func, parameters={"emb": query_emb, "k": top_k})
        func_results = []
        while res_func.has_next():
            row = res_func.get_next()
            func_results.append(
                f"[Function] ID: {row[0]}, Name: {row[1]}, Sim: {row[2]:.3f}"
            )

        return "Semantic Search Results:\n" + "\n".join(class_results + func_results)
    except Exception as e:
        return f"Error in semantic search: {e}"


def get_local_subgraph(node_id, project_root: str = "."):
    db_path = _resolve_ast_db_path(project_root)
    if not os.path.isdir(db_path):
        return _ast_db_missing_message()
    conn = get_kuzu_connection(project_root)
    if conn is None:
        return f"Error opening Kuzu graph database at {db_path}."
    try:
        if os.path.isabs(node_id):
            node_id = os.path.relpath(node_id, project_root)
        neighbors = []

        if node_id.endswith(".py"):
            res = conn.execute(
                "MATCH (f:File)-[*1..2]-(m) WHERE f.filepath = $id RETURN label(m), coalesce(m.id, m.filepath) LIMIT 20",
                {"id": node_id},
            )
            while res.has_next():
                r = res.get_next()
                neighbors.append(f"[{r[0]}] {r[1]}")
        else:
            res1 = conn.execute(
                "MATCH (n:ClassDef)-[*1..2]-(m) WHERE n.id = $id RETURN label(m), coalesce(m.id, m.filepath) LIMIT 20",
                {"id": node_id},
            )
            while res1.has_next():
                r = res1.get_next()
                neighbors.append(f"[{r[0]}] {r[1]}")

            res2 = conn.execute(
                "MATCH (n:FunctionDef)-[*1..2]-(m) WHERE n.id = $id RETURN label(m), coalesce(m.id, m.filepath) LIMIT 20",
                {"id": node_id},
            )
            while res2.has_next():
                r = res2.get_next()
                neighbors.append(f"[{r[0]}] {r[1]}")

        if not neighbors:
            return f"No neighbors found for node '{node_id}'."
        return f"Local subgraph for {node_id}:\n" + "\n".join(set(neighbors))
    except Exception as e:
        return f"Error retrieving local subgraph: {e}"


from rlm_optimized.config import CODE_TIMEOUT_SECONDS, ALLOWED_MODULES


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError(f"Code execution timed out after {CODE_TIMEOUT_SECONDS}s")


class REPLSandbox:
    def __init__(
        self,
        llm_query_fn: Optional[Callable] = None,
        project_root: Optional[str] = None,
    ):
        self._llm_query_fn = llm_query_fn
        self._project_root = project_root or os.getcwd()
        self._namespace = self._build_namespace()

    def set_project_root(self, project_root: str) -> None:
        """Update the active project root (e.g. after /cd) so the AST
        knowledge-graph functions bound into the sandbox namespace look
        in the right place instead of a stale or wrong workspace."""
        self._project_root = project_root
        self._namespace["get_project_structure"] = lambda: get_project_structure(
            self._project_root
        )
        self._namespace["get_class_signature"] = lambda name: get_class_signature(
            name, self._project_root
        )
        self._namespace["get_function_ast"] = lambda name: get_function_ast(
            name, self._project_root
        )
        self._namespace["get_function_source"] = lambda name: get_function_source(
            name, self._project_root
        )
        self._namespace["semantic_search"] = lambda query, top_k=3: semantic_search(
            query, top_k, self._project_root
        )
        self._namespace["get_local_subgraph"] = lambda node_id: get_local_subgraph(
            node_id, self._project_root
        )

    def _build_namespace(self) -> dict:
        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "chr": chr,
            "dict": dict,
            "divmod": divmod,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "format": format,
            "frozenset": frozenset,
            "hasattr": hasattr,
            "hash": hash,
            "hex": hex,
            "int": int,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "iter": iter,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "next": next,
            "oct": oct,
            "ord": ord,
            "pow": pow,
            "print": print,
            "range": range,
            "repr": repr,
            "reversed": reversed,
            "round": round,
            "set": set,
            "slice": slice,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
            "__import__": self._safe_import,
        }

        namespace = {"__builtins__": safe_builtins}
        for module_name in ALLOWED_MODULES:
            try:
                mod = __import__(module_name)
                namespace[module_name] = mod
            except ImportError:
                pass

        import os as _os, sys as _sys, pathlib as _pathlib

        namespace["os"] = _os
        namespace["sys"] = _sys
        namespace["pathlib"] = _pathlib
        namespace["Path"] = _pathlib.Path

        if self._llm_query_fn:
            namespace["llm_query"] = self._llm_query_fn

        namespace["get_project_structure"] = lambda: get_project_structure(
            self._project_root
        )
        namespace["get_class_signature"] = lambda name: get_class_signature(
            name, self._project_root
        )
        namespace["get_function_ast"] = lambda name: get_function_ast(
            name, self._project_root
        )
        namespace["get_function_source"] = lambda name: get_function_source(
            name, self._project_root
        )
        namespace["semantic_search"] = lambda query, top_k=3: semantic_search(
            query, top_k, self._project_root
        )
        namespace["get_local_subgraph"] = lambda node_id: get_local_subgraph(
            node_id, self._project_root
        )

        return namespace

    def _safe_import(self, name, *args, **kwargs):
        if name in ALLOWED_MODULES:
            return __import__(name, *args, **kwargs)
        raise ImportError(
            f"Module '{name}' is not allowed. Available: {', '.join(ALLOWED_MODULES)}"
        )

    def execute(self, code: str, cwd: Optional[str] = None) -> dict:
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        result = {"stdout": "", "stderr": "", "success": False, "error": None}

        has_sigalrm = hasattr(signal, "SIGALRM")
        old_handler = None

        old_cwd = os.getcwd()
        if cwd and os.path.isdir(cwd):
            try:
                os.chdir(cwd)
            except OSError:
                pass

        # Clean up any surrounding markdown code fences (e.g. ```python ... ```)
        if isinstance(code, str):
            code = re.sub(r"^\s*```(?:python|py)?\s*\n?", "", code, flags=re.IGNORECASE)
            code = re.sub(r"\n?\s*```\s*$", "", code).strip()

        # Pre-execution syntax & natural language check
        import ast

        try:
            ast.parse(code)
        except SyntaxError:
            words = code.split()
            prose_indicators = sum(
                1
                for w in words
                if w.lower().strip("`'\",.")
                in {
                    "the",
                    "is",
                    "are",
                    "was",
                    "were",
                    "will",
                    "would",
                    "should",
                    "could",
                    "have",
                    "has",
                    "had",
                    "been",
                    "being",
                    "this",
                    "that",
                    "with",
                    "from",
                    "into",
                    "since",
                    "because",
                    "however",
                    "therefore",
                    "i",
                    "we",
                    "they",
                    "he",
                    "she",
                    "it",
                    "my",
                    "your",
                    "if",
                    "were",
                    "executing",
                    "here",
                    "generating",
                    "result",
                    "file",
                    "asking",
                }
            )
            if len(words) > 3 and (prose_indicators / max(len(words), 1)) > 0.1:
                result["error"] = (
                    "Content appears to be natural language/prose, not executable Python code."
                )
                try:
                    os.chdir(old_cwd)
                except OSError:
                    pass
                return result

        if has_sigalrm:
            try:
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(CODE_TIMEOUT_SECONDS)
            except (ValueError, AttributeError):
                has_sigalrm = False

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, self._namespace)
            result["success"] = True
        except TimeoutError as e:
            result["error"] = str(e)
        except ImportError as e:
            result["error"] = f"Import error: {e}"
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        finally:
            if has_sigalrm:
                try:
                    signal.alarm(0)
                    if old_handler is not None:
                        signal.signal(signal.SIGALRM, old_handler)
                except (ValueError, AttributeError):
                    pass
            try:
                os.chdir(old_cwd)
            except OSError:
                pass

        result["stdout"] = stdout_capture.getvalue()
        result["stderr"] = stderr_capture.getvalue()
        return result

    def reset(self):
        self._namespace = self._build_namespace()

    def get_variables(self) -> dict:
        skip = set(ALLOWED_MODULES) | {"__builtins__", "llm_query"}
        return {
            k: repr(v)
            for k, v in self._namespace.items()
            if k not in skip and not k.startswith("_")
        }

    def set_llm_query_fn(self, fn: Callable):
        self._llm_query_fn = fn
        self._namespace["llm_query"] = fn
