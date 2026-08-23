# Torchlight Rust Port: Performance-Critical Paths

## Goal
Port the performance-critical hot paths from Python to Rust to achieve **10-100x speedups** on token counting, AST parsing, graph operations, compression, and tool parsing — while maintaining full Python compatibility via PyO3 bindings.

## Scope: Performance-Critical Modules (Priority Order)

| Module | Lines | Key Functions | Expected Speedup |
|--------|-------|---------------|------------------|
| `token_counter.py` | 70 | `count()`, `truncate()` | 50-100x (tiktoken native) |
| `flashlight/indexer.py` | 152 | `build()`, `_parse()` | 20-50x (tree-sitter native) |
| `graph_engine.py` | 748 | `build()`, `query()`, `find_path()`, `get_subgraph()` | 10-30x |
| `memory/manager.py` | 1378 | `TieredMemory`, `compress_recent()`, `format_l0_scratchpad()` | 5-15x |
| `memory/selective_compression.py` | 129 | `SelectiveCompressor.compress_turns()` | 10-20x |
| `memory/budget.py` | 117 | `ContextBudget` (adaptive allocations) | 5-10x |
| `compression/summarizer.py` | 96 | `ConversationSummarizer.structured_summarize()` | 5-10x |
| `tools/parser.py` | 314 | `parse_tool_call_payload()`, `tolerant_json_repair()` | 10-20x |

**Total: ~3,000 lines of hot Python → Rust**

---

## Architecture: Rust Crate + PyO3 Bindings

```
torchlight-core/
├── Cargo.toml
├── src/
│   ├── lib.rs                 # PyO3 module definitions
│   ├── token_counter/         # tiktoken-rs + fallback
│   ├── ast_indexer/           # tree-sitter multi-language parsing
│   ├── graph_engine/          # petgraph-based AST knowledge graph
│   ├── memory/
│   │   ├── tiered.rs          # TieredMemory (L0-L3)
│   │   ├── selective.rs       # SelectiveCompressor
│   │   └── budget.rs          # ContextBudget
│   ├── compression/
│   │   └── summarizer.rs      # ConversationSummarizer
│   ├── tools/
│   │   └── parser.rs          # Tool call parsing & repair
│   └── ffi/                   # Python-facing wrapper types
├── benches/                   # Criterion benchmarks
└── tests/                     # Integration tests
```

### FFI Strategy
- **PyO3** for Python bindings (mature, well-supported)
- Each module exposes a clean Rust API + Python-facing `PyClass`/`PyModule`
- **Zero-copy** where possible: `&str` ↔ Python strings, `Vec<u8>` ↔ `bytes`
- **Fallback**: Python imports try Rust first, fall back to pure Python on `ImportError`

---

## Module-by-Module Porting Plan

### 1. `token_counter` → `torchlight_core::token_counter` (Week 1)

**Rust dependencies**: `tiktoken-rs`, `once_cell`

**Porting notes**:
- `tiktoken-rs` uses the same BPE model files (`cl100k_base`, etc.)
- Fallback estimator: port regex logic directly (`regex` crate)
- `truncate()`: use `tiktoken` decode for exact; binary search for fallback

**Python API**:
```python
# Before
from core.memory.token_counter import get_token_counter
tc = get_token_counter("cl100k_base")
tc.count(text)
tc.truncate(text, max_tokens)

# After (auto-fallback)
from torchlight_core import TokenCounter
tc = TokenCounter("cl100k_base")  # or TokenCounter.fallback()
```

---

### 2. `flashlight/indexer.py` → `torchlight_core::ast_indexer` (Week 2)

**Rust dependencies**: `tree-sitter`, `tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-go`, `tree-sitter-rust`, `ignore` (for `.gitignore`-aware walking)

**Porting notes**:
- Replace regex-based parsing with **tree-sitter queries** for each language
- Use `ignore::WalkDir` for directory traversal (respects `.gitignore`)
- Incremental rebuild via `mtime` checks (same as Python)
- `FileEntry` → Rust struct with `Arc<[String]>` for lines, `Vec<Symbol>` for symbols

**Symbol extraction via tree-sitter queries**:
```rust
// Example for Python
const PY_QUERY: &str = r#"
(function_definition name: (identifier) @func)
(class_definition name: (identifier) @class)
"#;
```

**Python API**:
```python
from torchlight_core import SymbolIndex
idx = SymbolIndex(project_dir)
idx.build()  # returns file count
idx.summary()  # string
```

---

### 3. `graph_engine.py` → `torchlight_core::graph_engine` (Week 3)

**Rust dependencies**: `petgraph`, `serde`, `serde_json`, `dashmap` (concurrent graph cache)

**Porting notes**:
- `ProjectGraph` → `Graph<GraphNode, GraphEdge>` using `petgraph::Graph`
- Nodes: `File`, `Class`, `Function` with metadata (line_start, line_end, docstring)
- Edges: `Contains`, `Calls`, `Imports`
- Incremental update: `update_file()` removes subgraph + re-indexes
- Persistence: `serde_json` to `.torchlight/graph.json`
- Query methods return structured data; Python side formats strings

**Key optimizations**:
- `DashMap<String, NodeIndex>` for O(1) node lookup
- BFS/DFS for `find_path()` using `petgraph::algo`
- Subgraph extraction with depth limit & edge cap (40)

**Python API**:
```python
from torchlight_core import ProjectGraph
graph = ProjectGraph(project_root)
graph.build()
graph.query("search_term", top_k=5)
graph.find_path("source", "target")
graph.get_subgraph("symbol", max_depth=2)
graph.get_structure()
```

---

### 4. `memory/manager.py` → `torchlight_core::memory::tiered` (Week 4)

**Rust dependencies**: `dashmap`, `parking_lot` (RwLock), `smallvec`, `chrono`

**Porting notes**:
- `TieredMemory` → struct with `VecDeque<Message>`, `DashMap<String, PinnedFile>`
- `SessionState` as separate struct with bounded `Vec` collections
- `format_l0_scratchpad()`: pure Rust string building, no Python calls
- `compress_recent()`: orchestrate `SelectiveCompressor` + `ConversationSummarizer`
- Event listeners: `Vec<Box<dyn Fn(MemoryEvent) + Send + Sync>>`

**Concurrency**: All public methods `&self` with internal `RwLock` — allows parallel reads from Python

**Python API**:
```python
from torchlight_core import TieredMemory, MemoryConfig
mem = TieredMemory(MemoryConfig.auto_tune(max_tokens=12288))
mem.add_user_message("hello")
mem.add_assistant_message("hi")
ctx = mem.get_context_for_llm()
scratchpad = mem.format_l0_scratchpad(project_root=".")
```

---

### 5. `memory/selective_compression.py` → `torchlight_core::memory::selective` (Week 5)

**Porting notes**:
- Direct port of `CompressionLevel` enum, `CompressionConfig`, `SelectiveCompressor`
- Uses `TokenCounter` from module 1
- `_compact()` delegates to `TokenCounter::truncate()`
- Pattern matching via `regex` crate (same patterns)

**Python API**:
```python
from torchlight_core import SelectiveCompressor, CompressionConfig
comp = SelectiveCompressor(CompressionConfig())
summaries = comp.compress_turns(messages)
```

---

### 6. `memory/budget.py` → `torchlight_core::memory::budget` (Week 5)

**Porting notes**:
- Direct port of `ContextBudget` struct with all computed properties
- `_clamp` helper function
- No external deps — pure math

**Python API**:
```python
from torchlight_core import ContextBudget
budget = ContextBudget(max_tokens=12288, used_tokens=5000, base_pinned_tokens=600)
print(budget.l0_tokens, budget.pinned_tokens, budget.recent_tokens)
```

---

### 7. `compression/summarizer.py` → `torchlight_core::compression::summarizer` (Week 6)

**Porting notes**:
- `ConversationSummarizer` with `structured_summarize()` and `extract_key_info()`
- Regex patterns ported to `regex` crate
- `Message`/`MessageRole` from memory models (shared types)

**Python API**:
```python
from torchlight_core import ConversationSummarizer
summarizer = ConversationSummarizer()
summary = summarizer.structured_summarize(messages, state)
```

---

### 8. `tools/parser.py` → `torchlight_core::tools::parser` (Week 6)

**Porting notes**:
- All parsing/repair functions ported directly
- `tolerant_json_repair()`: character-by-character state machine (fast in Rust)
- `extract_balanced_json_object()`: same algorithm
- `clean_and_parse_json()`: 4-tier cascade
- `parse_tool_call_payload()`: returns structured result

**Python API**:
```python
from torchlight_core import parse_tool_call_payload, tolerant_json_repair
name, args, meta = parse_tool_call_payload(llm_output)
```

---

## Integration: Python Fallback Pattern

Each Python module gets a **try/except ImportError** wrapper:

```python
# core/memory/token_counter.py
try:
    from torchlight_core import TokenCounter as _RustTokenCounter
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False

class TokenCounter:
    def __init__(self, model="cl100k_base"):
        if _HAS_RUST:
            self._rust = _RustTokenCounter(model)
        else:
            # ... existing Python fallback ...
    
    def count(self, text):
        if _HAS_RUST:
            return self._rust.count(text)
        return self._estimate(text)
    # ...
```

**Build & Distribution**:
- `maturin build --release` → `.whl` for PyPI or local install
- `pip install torchlight-core` (or `maturin develop` for dev)
- Python frontends (`rlm_optimized`, `context-manager-cli`) unchanged

---

## Timeline: 12 Weeks Solo

| Week | Milestone |
|------|-----------|
| 1 | Crate setup, CI, `token_counter` port + benchmarks |
| 2 | `ast_indexer` with tree-sitter (Python, JS/TS, Go, Rust) |
| 3 | `graph_engine` with petgraph + persistence |
| 4 | `memory::tiered` (TieredMemory core) |
| 5 | `memory::selective` + `memory::budget` |
| 6 | `compression::summarizer` + `tools::parser` |
| 7 | PyO3 bindings for all modules, maturin config |
| 8 | Integration: update Python fallbacks, test end-to-end |
| 9 | Performance benchmarking, profiling, optimization |
| 10 | Edge cases, error handling, memory safety audit |
| 11 | Documentation, examples, release prep |
| 12 | Buffer / polish / publish |

---

## Success Metrics

| Operation | Python (baseline) | Rust Target | Measurement |
|-----------|-------------------|-------------|-------------|
| `TokenCounter.count("x" * 10000)` | ~2ms | <0.05ms | Criterion bench |
| `SymbolIndex.build()` (1000 files) | ~3s | <200ms | Integration test |
| `ProjectGraph.query("func")` | ~50ms | <5ms | Integration test |
| `TieredMemory.compress_recent()` | ~100ms | <10ms | Integration test |
| `parse_tool_call_payload()` | ~1ms | <0.1ms | Criterion bench |
| **End-to-end agent turn** | ~2-5s | **<1s** | Manual timing |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| tree-sitter grammar mismatches | Medium | High | Test against real codebases; fallback to regex |
| PyO3 GIL contention | Low | Medium | Use `pyo3::prepare_freethreaded_python()`; minimize GIL hold |
| Incremental graph update bugs | Medium | High | Property-based tests (proptest) for update/remove |
| Memory leaks in long-running TUI | Low | High | `valgrind`/`cargo-instruments` profiling; `Arc` cycles audit |
|tiktoken model file bundling | Low | Medium | Include `.tiktoken` files in crate via `include_bytes!` |

---

## Out of Scope (Future Work)

- Full TUI port to Ratatui (separate effort)
- LLM client backends (llama.cpp, ollama) — already fast via C libraries
- Skill system, debate verifier, autonomous harness — lower ROI
- Web inspector (Playwright) — Node.js dependency

---

## Next Steps

1. **Initialize crate**: `cargo new torchlight-core --lib` + `maturin init`
2. **Add dependencies** to `Cargo.toml` (see module sections)
3. **Port `token_counter` first** — highest ROI, lowest risk
4. **Set up CI**: GitHub Actions with `maturin build --release` on Linux/macOS/Windows
5. **Iterate**: One module per week, integrate, benchmark, repeat

---

*Plan created: 2026-08-12 | Target: Performance-critical paths only | Solo, 12 weeks*