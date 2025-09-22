-- Migration: Update document_chunks table for embedding step
-- Date: 2025-01-28
-- Description: Add embedding fields, remove redundant columns, update to HNSW index

-- Add new columns for embedding step
ALTER TABLE document_chunks 
ADD COLUMN IF NOT EXISTS indexing_run_id UUID REFERENCES indexing_runs(id),
ADD COLUMN IF NOT EXISTS chunk_id TEXT,
ADD COLUMN IF NOT EXISTS embedding_model TEXT,
ADD COLUMN IF NOT EXISTS embedding_provider TEXT,
ADD COLUMN IF NOT EXISTS embedding_metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS embedding_created_at TIMESTAMP WITH TIME ZONE;

-- Migrate existing data: generate chunk_id from existing chunk_index
UPDATE document_chunks 
SET chunk_id = CONCAT('chunk_', LPAD(chunk_index::TEXT, 6, '0'))
WHERE chunk_id IS NULL;

-- Make chunk_id NOT NULL after migration
ALTER TABLE document_chunks 
ALTER COLUMN chunk_id SET NOT NULL;

-- Migrate page_number and section_title to metadata if they exist and metadata doesn't have them
UPDATE document_chunks 
SET metadata = metadata || 
    CASE 
        WHEN page_number IS NOT NULL THEN jsonb_build_object('page_number', page_number)
        ELSE '{}'::jsonb
    END ||
    CASE 
        WHEN section_title IS NOT NULL THEN jsonb_build_object('section_title', section_title)
        ELSE '{}'::jsonb
    END
WHERE page_number IS NOT NULL OR section_title IS NOT NULL;

-- Drop redundant columns (after migrating data to metadata)
ALTER TABLE document_chunks 
DROP COLUMN IF EXISTS chunk_index,
DROP COLUMN IF EXISTS page_number,
DROP COLUMN IF EXISTS section_title;

-- Update embedding vector dimension to 1536 for voyage-large-2
ALTER TABLE document_chunks 
ALTER COLUMN embedding TYPE VECTOR(1536);

-- Drop old IVFFlat index and create HNSW index
DROP INDEX IF EXISTS idx_document_chunks_embedding;

-- Create HNSW index for vector similarity search (much faster than IVFFlat)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

-- Create GIN index for metadata queries
CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata_gin 
ON document_chunks 
USING gin (metadata);

-- Create index for embedding model/provider filtering
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_model 
ON document_chunks (embedding_model, embedding_provider);

-- Create index for indexing run filtering
CREATE INDEX IF NOT EXISTS idx_document_chunks_indexing_run_id 
ON document_chunks (indexing_run_id);

-- Create unique constraint for chunk_id per document
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_chunks_unique_chunk_per_document
ON document_chunks (document_id, chunk_id);

-- Update RLS policies to handle indexing_run_id
-- (The existing policies should still work, but let's ensure they cover the new field)

-- Add comment for documentation
COMMENT ON TABLE document_chunks IS 'Document chunks with embeddings for vector search. Updated for embedding step with voyage-large-2 support.';
COMMENT ON COLUMN document_chunks.chunk_id IS 'Unique identifier for chunk within document (e.g. chunk_000001)';
COMMENT ON COLUMN document_chunks.embedding IS 'Vector embedding using voyage-large-2 (1536 dimensions)';
COMMENT ON COLUMN document_chunks.metadata IS 'Chunk metadata including page_number, section_title, element_category, etc.';
COMMENT ON COLUMN document_chunks.embedding_metadata IS 'Embedding-specific metadata like processing time, confidence scores, etc.';