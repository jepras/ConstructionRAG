-- Migration: Fix embedding dimensions for voyage-large-2
-- Date: 2025-01-28
-- Description: Update embedding column to support 1536 dimensions for voyage-large-2

-- Drop existing HNSW index first
DROP INDEX IF EXISTS idx_document_chunks_embedding_hnsw;

-- Update embedding column to 1536 dimensions for voyage-large-2
ALTER TABLE document_chunks 
ALTER COLUMN embedding TYPE VECTOR(1536);

-- Recreate HNSW index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

-- Update comments
COMMENT ON COLUMN document_chunks.embedding IS 'Vector embedding using voyage-large-2 (1536 dimensions)'; 