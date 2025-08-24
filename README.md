# Codebase Semantic Search

A powerful codebase indexing and semantic search tool with command-line interface and Neovim plugin integration.

[Screenshots](https://github.com/jiangyinzuo/codebase-semantic-search/wiki#screenshots)

## Overview

Codebase Semantic Search enables semantic search capabilities over your codebase using modern embedding models. It indexes source code files and allows searching for code snippets based on semantic similarity rather than text matching.

**Key Features:**
- **Semantic Code Search**: Find code based on meaning and functionality
- **Multi-language Support**: Python, C++, and extensible via Tree-sitter
- **Flexible Backends**: Local sentence-transformers and OpenAI-compatible APIs
- **Neovim Integration**: Seamless editor workflow integration
- **Vector Database**: PostgreSQL with pgvector for efficient similarity search
- **Flexible Configuration**: Global and project-specific JSONC configuration

## Quick Start

### Installation

1. **Install Python Package:**
   ```bash
   python -m build
   pip install .
   ```

2. **Setup PostgreSQL with pgvector:**
   ```bash
   docker pull pgvector/pgvector:0.8.0-pg17
   docker run --name codebase-indexing -e POSTGRES_HOST_AUTH_METHOD=trust -p 5439:5432 -d pgvector/pgvector:0.8.0-pg17
   ```

3. **Create Database:**
   ```bash
   createdb -h 127.0.0.1 -p 5439 -U postgres codebase_indexing
   psql -h 127.0.0.1 -p 5439 -U postgres -d codebase_indexing -f create_tables.sql -v dim=1024
   ```

4. **Index and Search:**
   ```bash
   # Index files
   codebase index -a "`ls`"
   
   # Search semantically
   codebase search -q "your search query"
   ```

## Configuration

Configuration supports both global (`~/.config/codebase/config.jsonc`) and project-specific (`.codebase/config.jsonc`) settings with recursive merging.

Example configuration:
```jsonc
{
  "pgvector": {
    "dbname": "codebase_indexing",
    "user": "postgres", 
    "host": "127.0.0.1",
    "port": "5439",
    "default_sql": "SELECT query for Neovim plugin"
  },
  "model_provider": "openai",  // or "sentence_transformer"
  "openai": {"url": "http://localhost:8000"},
  "model": "/home/jiangyinzuo/Qwen3-Embedding-0.6B/"
}
```

## Neovim Plugin

**Requirements**: Neovim >= 0.11.0, `plenary.nvim`

**Installation** (lazy.nvim):
```lua
{
  "jiangyinzuo/codebase-semantic-search",
  dependencies = {"nvim-lua/plenary.nvim"},
}
```

**Usage**:
- `:Codebase` - Open search panel
- `<C-S>` - Submit query
- `<leader>tb` - View schema
- `<leader>cf` - View configuration

[Snippets example](https://github.com/jiangyinzuo/codebase-semantic-search/wiki/Snippet-Example)

## Advanced Usage

### CLI Commands

- **Indexing**: `codebase index -a "files" -d "files_to_remove" --dbname custom_db`
- **Searching**: `codebase search -q "query" --dbname custom_db --sql "CUSTOM_SQL"`
- **Configuration**: `codebase config` shows merged settings

### Database Schema

Uses PostgreSQL with pgvector extension:
```sql
CREATE TABLE code_chunks (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(255) NOT NULL UNIQUE,
    code_text TEXT NOT NULL,
    embedding vector(1024)
);
```

### Supported Languages

- Python (`.py`) via Tree-sitter
- C++ (`.cpp`, `.hpp`) via Tree-sitter
- Extensible to other languages

## Troubleshooting

**Common Issues**:
- Database connection: Check PostgreSQL/pgvector running and config
- Model not found: Verify model path and vLLM service
- No results: Ensure proper indexing and model compatibility
- Neovim issues: Check `codebase` in PATH and Neovim version

**Performance Tips**:
- Use local sentence-transformers for faster indexing
- Batch process large codebases
- Clean up unused indexed files

## Development

**Project Structure**:
```
src/codebase/
├── cli.py          # CLI interface
├── config.py       # Configuration  
├── indexing.py     # File indexing
├── model_provider.py # Embedding models
├── pgvector.py     # PostgreSQL
├── search.py       # Search
└── ts_chunk.py     # Tree-sitter
```

**Extending Languages**:
1. Install Tree-sitter grammar
2. Add mapping in `indexing.py`
3. Test with `ts_chunk.py`

**Contributing**: Follow code style, add tests, update docs.

## License

MIT License - see [LICENSE](LICENSE)
