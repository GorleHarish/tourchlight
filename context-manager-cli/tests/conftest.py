import sys
import os
from pathlib import Path

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Add repo root to path so the shared `core` library is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
