# Codebase Semantic Search

Semantic code search with CLI, Neovim plugin, and MCP server integration.

## Features

- **Semantic Search**: Find code by meaning, not just text
- **Multi-language**: Python, C++ via Tree-sitter
- **Flexible Backends**: Local models or OpenAI-compatible APIs
- **Neovim Integration**: Built-in editor workflow
- **MCP Server**: AI assistant integration via Model Context Protocol
- **Vector Database**: PostgreSQL with pgvector
- **Hierarchical Config**: Global + project JSONC settings

## Quick Start

```bash
# Install
python -m build && pip install .

# Setup PostgreSQL with pgvector
docker run --name codebase-indexing -e POSTGRES_HOST_AUTH_METHOD=trust -p 5439:5432 -d pgvector/pgvector:0.8.0-pg17
createdb -h 127.0.0.1 -p 5439 -U postgres codebase_indexing
psql -h 127.0.0.1 -p 5439 -U postgres -d codebase_indexing -f create_tables.sql -v dim=1024

# Index and search
codebase index -a "`ls`"
codebase search -q "your search query"
```

## MCP Server

Integrates with AI assistants like Claude Code:

```bash
# Start MCP server
codebase-mcp
```

Configure in your AI assistant settings:
```json
{
  "mcpServers": {
    "codebase": {
      "command": "codebase-mcp"
    }
  }
}
```

Use semantic search: `Find authentication-related code in the codebase`

## Neovim Plugin

```lua
{
  "jiangyinzuo/codebase-semantic-search",
  dependencies = {"nvim-lua/plenary.nvim"},
}
```

- `:Codebase` - Open search panel
- `<C-S>` - Submit query

## Configuration

Example `~/.config/codebase/config.jsonc`:
```jsonc
{
  "pgvector": {
    "dbname": "codebase_indexing",
    "user": "postgres",
    "host": "127.0.0.1",
    "port": "5439"
  },
  "model_provider": "openai",
  "openai": {"url": "http://localhost:8000"},
  "model": "/path/to/local/model/"
}
```

## Development

```bash
# Run tests
pytest

# Run with database
python run_integration_tests.py --with-db

# MCP server tests
pytest tests/test_mcp_server.py -v --asyncio-mode=auto
```

Project structure: `src/codebase/` with CLI, indexing, search, MCP server, and model providers.

MIT License