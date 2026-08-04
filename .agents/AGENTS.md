## Codebase Exploration & Token Optimization Rules
- **Always Use Graphify Query First**: For understanding codebase architecture, module relationships, or finding specific components, always use `graphify query "<question>"`, `graphify path`, or `graphify explain` (or `query_graph` MCP tool) instead of re-reading raw source files line by line.
- **Token Conservation**: Rely on targeted graph queries and graph output to save context tokens while preserving high analytical quality and accuracy.
- **Keep Graph Current**: After modifying code files in a session, run `graphify update .` to keep the knowledge graph up to date.
