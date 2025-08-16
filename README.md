# Codebase Semantic Search

Codebase indexing and search tool in command line and Neovim.

**Features:**

- Embedding: OpenAI-compatible embedding API / sentence_transformer support
- AST-based code chunker via treesitter
- Command-line tool & Neovim plugin integration

[Screenshots](https://github.com/jiangyinzuo/codebase-semantic-search/wiki#screenshots)

## How to Use
### Installation

**Build and Install Python Package**

```bash
python -m build
pip install .
```

**Install PGVector via Docker**

```bash
docker pull pgvector/pgvector:0.8.0-pg17
# POSTGRES_HOST_AUTH_METHOD=trust: Allows connections without a password
# -d: run in detached mode
# -p: host:container port mapping, `sudo lsof -i :5432` to see if port is in use
docker run --name codebase-indexing-jyz -e POSTGRES_HOST_AUTH_METHOD=trust -p 5439:5432 -d pgvector/pgvector:0.8.0-pg17
```

### Connect to PGVector

1) Connect from host
```bash
psql -h 127.0.0.1 -p 5439 -U postgres
# or
psql -h 127.0.0.1 -p 5439 -U postgres -c "SELECT version();"
```

2) Connect from container
```bash
docker exec -it codebase-indexing-jyz psql -U postgres
```

### Create Database & Tables

```bash
createdb -h 127.0.0.1 -p 5439 -U postgres codebase_indexing
psql -h 127.0.0.1 -p 5439 -U postgres -d codebase_indexing -f create_tables.sql -v dim=1024
# drop table
psql -h 127.0.0.1 -p 5439 -U postgres -c 'drop database codebase_indexing'
```


### Run Model as Local vLLM Service (Optional)

```bash
vllm serve /home/jiangyinzuo/Qwen3-Embedding-0.6B/ --task embed
# list models, avoid squid http proxy
no_proxy="localhost,127.0.0.1" curl localhost:8000/v1/models
```

The result may be:
```json
{"object":"list","data":[{"id":"/home/jiangyinzuo/Qwen3-Embedding-0.6B/","object":"model","created":1755255045,"owned_by":"vllm","root":"/home/jiangyinzuo/Qwen3-Embedding-0.6B/","parent":null,"max_model_len":32768,"permission":[{"id":"modelperm-d53a57a6eba647fa84deb69634726767","object":"model_permission","created":1755255045,"allow_create_engine":false,"allow_sampling":true,"allow_logprobs":true,"allow_search_indices":false,"allow_view":true,"allow_fine_tuning":false,"organization":"*","group":null,"is_blocking":false}]}]}
```

### Indexing & Searching

```bash
# indexing
ls *.py | codebase-indexing
# searching
psql -h 127.0.0.1 -p 5439 -U postgres -d codebase_indexing -c "select file_path from code_chunks"
psql -h 127.0.0.1 -p 5439 -U postgres -d codebase_indexing -c "select code_text from code_chunks where file_path = 'indexing.py'"
echo "Indexer" | codebase-search

```

### Configuration

Global configuration is in `$XDG_CONFIG_HOME/codebase/config.jsonc`

```jsonc
{
  "pgvector": {
    "dbname": "codebase_indexing",
    "user": "postgres",
    "host": "127.0.0.1",
    // is string
    "port": "5439"
  },
  // openai | sentence_transformer
  "model_provider": "openai",
  "openai": {
    "url": "http://localhost:8000"
  },
  // the last '/' matters
  // See: https://huggingface.co/spaces/mteb/leaderboard to pickup an embedding model
  "model": "/home/jiangyinzuo/Qwen3-Embedding-0.6B/"
}
```

## Neovim Plugin

### Installation

lazy.nvim
```lua
{
  "jiangyinzuo/codebase-semantic-search",
  dependencies = {
    "nvim-lua/plenary.nvim",
  },
}

```

### Usage

- `:Codebase` command: open search panel
- [Snippets example](https://github.com/jiangyinzuo/codebase-semantic-search/wiki/Snippet-Example)
