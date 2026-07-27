"""
Flashlight — automatic codebase illumination for Torchlight.

Instead of a static CLAUDE.md, Flashlight scans the project at startup,
builds a symbol index (files, functions, classes, imports), and for every
user query shines a "beam" — injecting only the most relevant file sections
into the context automatically.

Usage:
    from context_manager.flashlight import Flashlight, SymbolIndex

    index = SymbolIndex(Path("/path/to/project"))
    light = Flashlight(index)
    beam  = light.beam("how does compression work?")
    # beam → list of {path, snippet, reason, symbols}
"""

from .indexer import SymbolIndex
from .beam import Flashlight

__all__ = ["SymbolIndex", "Flashlight"]
