# Context Manager CLI

Smart context management for local LLMs via LM Studio or Ollama. Prevents context rot with automatic compression, tiered memory, and session persistence — all from your terminal.

## Features

- **Tiered Memory**: Recent messages kept in full detail, older messages summarized
- **Verbatim Compaction**: Preserves code blocks, errors, and file paths exactly
- **LLM Summarization**: Intelligent compression using another model call
- **Session Persistence**: Save and resume conversations across restarts
- **Project Memory**: Persist key facts, decisions, and tech stack across sessions
- **Rich CLI**: Real-time context statistics and status via Rich panels
- **Streaming Responses**: Real-time token count and context stats during generation

## Installation

```bash
cd context-manager-cli
pip install -e .
```

## Usage

```bash
# Start a chat session
context chat

# Match your model's context window
context chat --max-tokens 4096
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--url, -u` | LM Studio/Ollama API URL (default: http://localhost:1234/v1) |
| `--model, -m` | Model name (auto-detected if omitted) |
| `--max-tokens, -t` | Maximum context tokens (default: 8000) |
| `--no-stream` | Disable streaming responses |
| `--project` | Set the project root for workspace-aware context |

## Commands (in CLI)

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show context statistics (tokens, messages, memory) |
| `/stream` | Toggle streaming mode |
| `/compress` | Manually trigger memory compression |
| `/clear` | Clear all context |
| `/tokens` | Show token usage breakdown |
| `/save [name]` | Save current session to disk |
| `/params` | Show or set inference parameters |
| `/reindex` | Rebuild Flashlight symbol index |
| `/beam [query]` | Run Flashlight beam search |
| `/files` | List recently accessed files |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Context Manager CLI                     │
├─────────────────────────────────────────────────────┤
│  Terminal REPL (Typer + Rich)                        │
│       │                                             │
│       ▼                                             │
│  Tiered Memory                                      │
│  ├─ L0: Active prompt + beam + tool results         │
│  ├─ L1: Recent messages (full detail)               │
│  ├─ L2: Compressed summaries + state extraction     │
│  └─ L3: Persistent project memory (.context-memory) │
│       │                                             │
│       ▼                                             │
│  Tool Registry + Flashlight Index                   │
│       │                                             │
│       ▼                                             │
│  LM Studio / Ollama API (http://localhost:1234/v1)  │
└─────────────────────────────────────────────────────┘
```

## How It Works

1. **Token Budget**: Default 8000 tokens (85% of context window)
2. **Compression Trigger**: At 70% capacity
3. **Preservation Priority**: Code blocks (exact), errors (full traces), file paths (preserved), explanations (summarized)
4. **Compression Methods**: Verbatim (remove empty lines, normalize whitespace) and LLM summarization

## Requirements

- Python 3.9+
- LM Studio or Ollama running locally with a chat-capable model
- Dependencies: typer, rich, httpx, tiktoken, psutil
