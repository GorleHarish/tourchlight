import ast
import os
import glob

def generate_ast_for_directory(directory="."):
    python_files = glob.glob(os.path.join(directory, "**/*.py"), recursive=True)
    output_file = "ast_output.txt"
    
    with open(output_file, "w", encoding="utf-8") as out_file:
        for file_path in python_files:
            if ".venv" in file_path or "venv" in file_path or "rlm_optimized" in file_path:
                continue
                
            out_file.write(f"{'='*60}\nFile: {file_path}\n{'='*60}\n")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source_code = f.read()
                
                parsed_ast = ast.parse(source_code, filename=file_path)
                ast_str = ast.dump(parsed_ast, indent=4)
                out_file.write(ast_str + "\n\n")
                print(f"✓ Generated AST for: {file_path}")
            except Exception as e:
                err_msg = f"Error processing {file_path}: {e}"
                out_file.write(err_msg + "\n\n")
                print(f"✗ {err_msg}")

if __name__ == "__main__":
    generate_ast_for_directory()
