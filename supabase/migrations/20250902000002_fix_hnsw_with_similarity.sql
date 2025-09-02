-- Fix HNSW function to return similarity scores properly
-- Date: 2025-09-02
-- Description: Return similarity scores along with chunk data

-- Drop the broken function
DROP FUNCTION IF EXISTS match_chunks CASCADE;

-- Create function that returns results WITH similarity scores
CREATE OR REPLACE FUNCTION match_chunks (
  query_embedding vector(1024),
  match_threshold float,
  match_count int,
  indexing_run_id_filter text DEFAULT null
) 
RETURNS TABLE (
  id uuid,
  content text,
  metadata jsonb,
  embedding_1024 vector(1024),
  document_id uuid,
  indexing_run_id uuid,
  similarity float
)
LANGUAGE sql 
AS $$
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

-- Grant permissions
GRANT EXECUTE ON FUNCTION match_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION match_chunks TO anon;

-- Add comment
COMMENT ON FUNCTION match_chunks IS 'HNSW vector search that returns K nearest neighbors with similarity scores. No threshold filtering in WHERE clause to ensure proper index usage.';

-- Verify
DO $$
BEGIN
  RAISE NOTICE 'match_chunks function fixed: now returns similarity scores and uses index properly';
END $$;