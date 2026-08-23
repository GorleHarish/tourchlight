---
trigger: always_on
description: MANDATORY HARD RULE: Always query graphify first for codebase-level search, architecture exploration, dependencies, and component relationships.
---

## Graphify Codebase Exploration & Dependency Hard Rules

This project maintains a graphify knowledge graph at `graphify-out/`.

### 1. Mandatory Graphify-First Codebase Search
- **Primary Search & Discovery Tool**: For ANY codebase-level search, architecture question, symbol discovery, or relationship exploration, you **MUST ALWAYS** start by querying graphify:
  - **Codebase Search & Concept Query**: Run `graphify query "<question or symbol>"` (CLI) or `query_graph` (MCP).
  - **Component Dependencies & Interactions**: Run `graphify path "<A>" "<B>"` (CLI) or `shortest_path` (MCP) to trace connections, data flows, and import/call chains.
  - **Focused Component Inspection**: Run `graphify explain "<concept/symbol>"` (CLI) or `get_node` (MCP) for focused structure and immediate callers/callees.
  - **Architectural Hubs & Central Nodes**: Run `graphify god-nodes` to identify central dependencies and entry points.
- **Strict Anti-Pattern Prohibition**: NEVER start codebase exploration with blind whole-directory reads or massive grep scans. Always inspect the scoped subgraph returned by graphify first to minimize token waste and maintain high precision.

### 2. Dependency & Relationship Analysis
- When asked about how modules, classes, or functions depend on each other, interact, or flow data:
  - Run `graphify path "<source_component>" "<target_component>"` to retrieve the exact call/import relationship path.
  - Run `graphify explain "<component>"` to inspect all incoming and outgoing dependencies, callers, and callees.
- If `graphify-out/wiki/index.md` exists, consult it for high-level module architecture and subsystem boundaries.
- Consult `graphify-out/GRAPH_REPORT.md` only when broad, global architecture review is required.

### 3. Graph Synchronization
- **Keep Graph Current**: After creating or modifying code files in a session, execute `graphify update .` (or `graphify extract . --code-only`) to ensure the knowledge graph and dependencies stay synchronized with the active codebase.
