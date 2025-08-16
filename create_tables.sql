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
