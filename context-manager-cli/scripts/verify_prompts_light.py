
import re
import os

def verify_file_content(file_path, expected_patterns):
    print(f"=== Verifying {os.path.basename(file_path)} ===")
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    all_ok = True
    for pattern in expected_patterns:
        if re.search(pattern, content):
            print(f"✅ Found: {pattern}")
        else:
            print(f"❌ Missing: {pattern}")
            all_ok = False
    print("\n")
    return all_ok

if __name__ == "__main__":
    # Verify skills/base.py
    skills_patterns = [
        r"Usage: \[SKILL:read_file\]",
        r"When to use: Use this to examine source code",
        r"Usage: \[SKILL:bash\]",
        r"When to use: Use to remember architectural decisions"
    ]
    verify_file_content("src/context_manager/skills/base.py", skills_patterns)
    
    # Verify cli/main.py
    cli_patterns = [
        r"## ⚠️ MANDATORY DIRECTIVE:",
        r"## Tool Execution Rules:",
        r"1\. \[CRITICAL\] Output <thought>\.\.\.</thought> before any tool call or response\."
    ]
    verify_file_content("src/context_manager/cli/main.py", cli_patterns)
    
    # Verify gui/app.py
    gui_patterns = [
        r"## Tool Documentation:",
        r"- READ_FILE\(\"path\"\):",
        r"4\. CHAIN OF THOUGHT: Output: <thought>\.\.\.</thought>",
        r"5\. POSITIONING: If you call a tool, it MUST be the very last thing"
    ]
    verify_file_content("src/context_manager/gui/app.py", gui_patterns)
