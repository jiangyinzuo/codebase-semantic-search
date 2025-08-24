CREATE EXTENSION IF NOT EXISTS vector;

-- 父表：包含所有类型都共享的字段
CREATE TABLE IF NOT EXISTS code_chunks (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(255) NOT NULL UNIQUE,
    code_text TEXT NOT NULL,
    embedding vector(:dim)
);

CREATE INDEX file_path_idx ON code_chunks (file_path);
CREATE INDEX ON code_chunks USING hnsw (embedding vector_cosine_ops);

-- 存储索引元数据（单条记录）
CREATE TABLE IF NOT EXISTS index_metadata (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    last_commit_hash VARCHAR(40),
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入初始记录
INSERT INTO index_metadata (id, last_commit_hash) 
VALUES (1, NULL)
ON CONFLICT (id) DO NOTHING;
