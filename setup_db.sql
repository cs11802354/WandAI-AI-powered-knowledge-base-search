CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    raw_content TEXT,
    file_size BIGINT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    document_metadata JSONB,
    version INTEGER DEFAULT 1 NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    replaced_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(1536),
    document_metadata JSONB,
    recency_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    replaced_at TIMESTAMP
);

-- Vector similarity search index
CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Document indexes
CREATE INDEX IF NOT EXISTS documents_hash_idx ON documents(content_hash);
CREATE INDEX IF NOT EXISTS documents_uploaded_at_idx ON documents(uploaded_at);
CREATE INDEX IF NOT EXISTS documents_last_modified_idx ON documents(last_modified);
CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents(filename);
CREATE INDEX IF NOT EXISTS documents_is_active_idx ON documents(is_active);
CREATE INDEX IF NOT EXISTS documents_filename_active_idx ON documents(filename, is_active);

-- Chunk indexes
CREATE INDEX IF NOT EXISTS chunks_document_idx ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS chunks_created_at_idx ON document_chunks(created_at);
CREATE INDEX IF NOT EXISTS chunks_is_active_idx ON document_chunks(is_active);
CREATE INDEX IF NOT EXISTS chunks_active_document_idx ON document_chunks(is_active, document_id);
CREATE INDEX IF NOT EXISTS chunks_recency_score_idx ON document_chunks(recency_score);
CREATE INDEX IF NOT EXISTS chunks_metadata_idx ON document_chunks USING gin(document_metadata);

-- Optimize tables
ANALYZE documents;
ANALYZE document_chunks;

-- Performance settings
ALTER DATABASE knowledge_base SET maintenance_work_mem = '512MB';
ALTER DATABASE knowledge_base SET effective_cache_size = '4GB';