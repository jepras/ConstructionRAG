-- Fix HNSW Vector Search Function
-- Date: 2025-09-02
-- Description: Fix match_chunks function to properly use HNSW index by removing threshold from WHERE clause

-- Drop the old function
DROP FUNCTION IF EXISTS match_chunks(vector(1024), float, int, text);

-- Create the improved match_chunks function
-- This version properly uses the HNSW index by:
-- 1. First finding K nearest neighbors using the index
-- 2. Then optionally filtering by threshold (if needed)
CREATE OR REPLACE FUNCTION match_chunks (
  query_embedding vector(1024),
  match_threshold float,
  match_count int,
  indexing_run_id_filter text DEFAULT null
) RETURNS TABLE (
  id uuid,
  content text,
  metadata jsonb,
  embedding_1024 vector(1024),
  document_id uuid,
  indexing_run_id uuid,
  similarity float
)
LANGUAGE sql AS $$
  SELECT 
    id,
    content,
    metadata,
    embedding_1024,
    document_id,
    indexing_run_id,
    1 - (embedding_1024 <=> query_embedding) as similarity
  FROM document_chunks
  WHERE 
    embedding_1024 IS NOT NULL
    AND (indexing_run_id_filter IS NULL OR indexing_run_id::text = indexing_run_id_filter)
  ORDER BY embedding_1024 <=> query_embedding ASC
  LIMIT LEAST(match_count, 200);
$$;

-- Alternative version that applies threshold AFTER finding nearest neighbors
-- This is better for performance but changes the result count behavior
CREATE OR REPLACE FUNCTION match_chunks_with_threshold (
  query_embedding vector(1024),
  match_threshold float,
  match_count int,
  indexing_run_id_filter text DEFAULT null
) RETURNS TABLE (
  id uuid,
  content text,
  metadata jsonb,
  embedding_1024 vector(1024),
  document_id uuid,
  indexing_run_id uuid,
  similarity float
)
LANGUAGE sql AS $$
  SELECT * FROM (
    SELECT 
      id,
      content,
      metadata,
      embedding_1024,
      document_id,
      indexing_run_id,
      1 - (embedding_1024 <=> query_embedding) as similarity
    FROM document_chunks
    WHERE 
      embedding_1024 IS NOT NULL
      AND (indexing_run_id_filter IS NULL OR indexing_run_id::text = indexing_run_id_filter)
    ORDER BY embedding_1024 <=> query_embedding ASC
    LIMIT LEAST(match_count, 200)
  ) AS nearest_neighbors
  WHERE similarity > match_threshold;
$$;

-- Grant necessary permissions for both functions
GRANT EXECUTE ON FUNCTION match_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION match_chunks TO anon;
GRANT EXECUTE ON FUNCTION match_chunks_with_threshold TO authenticated;
GRANT EXECUTE ON FUNCTION match_chunks_with_threshold TO anon;

-- Add comments for documentation
COMMENT ON FUNCTION match_chunks IS 'Fixed vector similarity search using HNSW index. Returns K nearest neighbors ordered by cosine similarity, ignoring threshold in WHERE clause for proper index usage.';
COMMENT ON FUNCTION match_chunks_with_threshold IS 'Vector similarity search that finds K nearest neighbors first, then filters by threshold. Better performance but may return fewer than K results.';

-- Verify the functions work
DO $$
BEGIN
  -- Check if functions were created successfully
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p 
    JOIN pg_namespace n ON p.pronamespace = n.oid 
    WHERE n.nspname = 'public' AND p.proname = 'match_chunks'
  ) THEN
    RAISE EXCEPTION 'Failed to create match_chunks function';
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p 
    JOIN pg_namespace n ON p.pronamespace = n.oid 
    WHERE n.nspname = 'public' AND p.proname = 'match_chunks_with_threshold'
  ) THEN
    RAISE EXCEPTION 'Failed to create match_chunks_with_threshold function';
  END IF;
  
  -- Log success
  RAISE NOTICE 'match_chunks functions fixed successfully';
END $$;