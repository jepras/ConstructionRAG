-- Migration: Add step_results field to documents table for document-centric step result storage
-- Date: 2025-08-02

-- Add step_results field to documents table
-- This follows the same JSONB structure as indexing_runs.step_results
ALTER TABLE documents 
ADD COLUMN step_results JSONB DEFAULT '{}';

-- Add index for better performance when querying step results
CREATE INDEX IF NOT EXISTS idx_documents_step_results ON documents USING GIN (step_results);

-- Add comment to document the field purpose
COMMENT ON COLUMN documents.step_results IS 'Stores step results for each pipeline step (partition, metadata, enrichment, chunking, embedding)'; 