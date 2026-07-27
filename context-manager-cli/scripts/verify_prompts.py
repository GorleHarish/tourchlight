
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from context_manager.skills.base import create_default_registry
from context_manager.prompts import SYSTEM_PROMPT

def verify_cli_prompt():
    print("=== CLI Prompt Verification ===")
    registry = create_default_registry()
    prompts = registry.get_all_prompts()
    print(prompts)
    
    # Check for keywords
    expected = ["Usage:", "When to use:", "Output:", "read_file"]
    for word in expected:
        if word not in prompts:
            print(f"❌ CLI prompt missing: {word}")
        else:
            print(f"✅ CLI prompt contains: {word}")
    print("\n")

def verify_gui_prompt():
    print("=== GUI Prompt Verification ===")
    print(SYSTEM_PROMPT)
    
    # Check for keywords
    expected = [
        "## Tool Documentation",
        "READ_FILE(",
        "WRITE_FILE(",
        "RUN_COMMAND(",
        "CHAIN OF THOUGHT",
        "## Anti-Hallucination",
        "## Error Recovery",
        "## Working Directory",
        "## Output Formatting",
    ]
    for word in expected:
        if word not in SYSTEM_PROMPT:
            print(f"❌ GUI prompt missing: {word}")
        else:
            print(f"✅ GUI prompt contains: {word}")
    print("\n")

if __name__ == "__main__":
    verify_cli_prompt()
    verify_gui_prompt()
