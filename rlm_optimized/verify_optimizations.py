#!/usr/bin/env python3
import sys
import os
import py_compile

# List of files to verify syntax
FILES_TO_CHECK = [
    "rlm_optimized/config.py",
    "rlm_optimized/prompts.py",
    "rlm_optimized/repl_sandbox.py",
    "rlm_optimized/llamacpp_client.py",
    "rlm_optimized/rlm_engine_optimized.py",
    "rlm_optimized/ast_indexer.py",
    "rlm_optimized/ollama_client.py",
    "rlm_optimized/cloud_client.py",
    "rlm_optimized/rlm_engine.py",
    "rlm_optimized/main.py",
    "rlm_optimized/main_optimized.py",
    "rlm_optimized/generate_ast.py",
]

def check_syntax():
    print("[VERIFY] Running static syntax check for RLM optimized modules...")
    all_passed = True
    
    for filepath in FILES_TO_CHECK:
        if not os.path.exists(filepath):
            print(f"  ✗ {filepath}: File does not exist")
            all_passed = False
            continue
            
        try:
            py_compile.compile(filepath, doraise=True)
            print(f"  ✓ {filepath}: Syntax is correct.")
        except py_compile.PyCompileError as e:
            print(f"  ✗ {filepath}: Syntax error: {e}")
            all_passed = False
            
    if all_passed:
        print("[VERIFY] All RLM optimized python modules passed syntax compilation check.")
    else:
        print("[VERIFY] ERROR: One or more modules failed syntax validation.")
        sys.exit(1)

if __name__ == "__main__":
    check_syntax()
