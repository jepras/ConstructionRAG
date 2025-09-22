-- Migration: Update to voyage-multilingual-2 with renamed column
-- Date: 2025-01-28
-- Description: Rename embedding column to embedding_1024 and update for voyage-multilingual-2

-- Drop existing HNSW index first
DROP INDEX IF EXISTS idx_document_chunks_embedding_hnsw;

-- Delete existing chunks with embeddings to allow clean migration
DELETE FROM document_chunks WHERE embedding IS NOT NULL;

-- Rename embedding column to embedding_1024
ALTER TABLE document_chunks 
RENAME COLUMN embedding TO embedding_1024;

-- Update embedding column to 1024 dimensions for voyage-multilingual-2
ALTER TABLE document_chunks 
ALTER COLUMN embedding_1024 TYPE VECTOR(1024);

-- Recreate HNSW index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_1024_hnsw 
ON document_chunks 
USING hnsw (embedding_1024 vector_cosine_ops)
WHERE embedding_1024 IS NOT NULL;

-- Update comments
COMMENT ON COLUMN document_chunks.embedding_1024 IS 'Vector embedding using voyage-multilingual-2 (1024 dimensions)'; 