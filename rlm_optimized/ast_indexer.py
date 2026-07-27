import ast
import kuzu
import glob
import os
import shutil
import argparse
from sentence_transformers import SentenceTransformer
from rlm_optimized.config import AST_DB_DIRNAME

def init_db(db_path):
    """Initialize the Kuzu graph database with the AST schema and vector embeddings."""
    if os.path.exists(db_path):
        try:
            if os.path.isdir(db_path):
                shutil.rmtree(db_path, ignore_errors=True)
            else:
                os.remove(db_path)
        except Exception as e:
            print(f"[init_db] Warning deleting existing DB at {db_path}: {e}")
        
    db = kuzu.Database(db_path, buffer_pool_size=268435456)
    conn = kuzu.Connection(db)
    
    conn.execute("CREATE NODE TABLE IF NOT EXISTS File(filepath STRING, PRIMARY KEY (filepath))")
    conn.execute("CREATE NODE TABLE IF NOT EXISTS ClassDef(id STRING, name STRING, docstring STRING, line_start INT64, line_end INT64, embedding FLOAT[384], PRIMARY KEY (id))")
    conn.execute("CREATE NODE TABLE IF NOT EXISTS FunctionDef(id STRING, name STRING, args STRING, docstring STRING, source_code STRING, ast_dump STRING, embedding FLOAT[384], PRIMARY KEY (id))")
    
    conn.execute("CREATE REL TABLE IF NOT EXISTS File_HAS_CLASS(FROM File TO ClassDef)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS File_HAS_FUNCTION(FROM File TO FunctionDef)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS Class_HAS_FUNCTION(FROM ClassDef TO FunctionDef)")
    
    try:
        conn.execute("MATCH (n) DETACH DELETE n")
    except Exception:
        pass
        
    return conn

class IndexVisitor(ast.NodeVisitor):
    def __init__(self, conn, filepath, source_lines, encoder):
        self.conn = conn
        self.filepath = filepath
        self.source_lines = source_lines
        self.encoder = encoder
        self.current_class_id = None

    def get_source_code(self, node):
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            return "\n".join(self.source_lines[node.lineno - 1:node.end_lineno])
        return ""

    def visit_ClassDef(self, node):
        docstring = ast.get_docstring(node) or ""
        class_id = f"{self.filepath}::{node.name}"
        
        text_to_embed = f"Class: {node.name}\nDocstring: {docstring}"
        embedding = self.encoder.encode(text_to_embed).tolist()
        
        self.conn.execute(
            "CREATE (c:ClassDef {id: $id, name: $name, docstring: $doc, line_start: $ls, line_end: $le, embedding: $emb})",
            parameters={"id": class_id, "name": node.name, "doc": docstring, "ls": node.lineno, "le": node.end_lineno, "emb": embedding}
        )
        self.conn.execute(
            "MATCH (f:File {filepath: $filepath}), (c:ClassDef {id: $class_id}) CREATE (f)-[:File_HAS_CLASS]->(c)",
            parameters={"filepath": self.filepath, "class_id": class_id}
        )
        
        prev_class_id = self.current_class_id
        self.current_class_id = class_id
        self.generic_visit(node)
        self.current_class_id = prev_class_id

    def visit_FunctionDef(self, node):
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._handle_function(node)

    def _handle_function(self, node):
        docstring = ast.get_docstring(node) or ""
        source_code = self.get_source_code(node)
        
        args = [arg.arg for arg in node.args.args]
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        args_str = ", ".join(args)
        
        try:
            ast_dump = ast.dump(node, indent=2)
        except TypeError:
            ast_dump = ast.dump(node)
            
        parent_id = self.current_class_id if self.current_class_id else self.filepath
        func_id = f"{parent_id}::{node.name}"
        
        text_to_embed = f"Function: {node.name}\nArgs: {args_str}\nDocstring: {docstring}\nSource: {source_code}"
        embedding = self.encoder.encode(text_to_embed).tolist()
        
        self.conn.execute(
            "CREATE (fn:FunctionDef {id: $id, name: $name, args: $args, docstring: $doc, source_code: $src, ast_dump: $ast, embedding: $emb})",
            parameters={"id": func_id, "name": node.name, "args": args_str, "doc": docstring, "src": source_code, "ast": ast_dump, "emb": embedding}
        )
        
        if self.current_class_id:
            self.conn.execute(
                "MATCH (c:ClassDef {id: $class_id}), (fn:FunctionDef {id: $func_id}) CREATE (c)-[:Class_HAS_FUNCTION]->(fn)",
                parameters={"class_id": self.current_class_id, "func_id": func_id}
            )
        else:
            self.conn.execute(
                "MATCH (f:File {filepath: $filepath}), (fn:FunctionDef {id: $func_id}) CREATE (f)-[:File_HAS_FUNCTION]->(fn)",
                parameters={"filepath": self.filepath, "func_id": func_id}
            )

def index_directory(directory=".", db_path=None):
    directory = os.path.abspath(directory)
    if db_path is None:
        db_path = os.path.join(directory, AST_DB_DIRNAME)

    print(f"Indexing {directory}")
    print(f"Graph DB target: {db_path}")
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    
    conn = init_db(db_path)
    python_files = glob.glob(os.path.join(directory, "**/*.py"), recursive=True)
    
    for file_path in python_files:
        if ".venv" in file_path or "venv" in file_path:
            continue
            
        try:
            rel_path = os.path.relpath(file_path, directory)
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            source_lines = source_code.splitlines()
            
            parsed_ast = ast.parse(source_code, filename=file_path)
            conn.execute("CREATE (f:File {filepath: $filepath})", parameters={"filepath": rel_path})
            
            visitor = IndexVisitor(conn, rel_path, source_lines, encoder)
            visitor.visit(parsed_ast)
        except SyntaxError:
            print(f"Skipping {file_path} (Syntax Error)")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
    print(f"✓ Kuzu graph indexing complete. Saved to {db_path}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the Torchlight AST knowledge graph for a project.")
    parser.add_argument("directory", nargs="?", default=".", help="Project directory to index (default: current directory)")
    args = parser.parse_args()
    index_directory(args.directory)
