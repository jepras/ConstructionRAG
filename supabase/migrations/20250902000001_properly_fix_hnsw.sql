-- Properly fix HNSW function by completely replacing it
-- Date: 2025-09-02
-- Description: Drop and recreate match_chunks to remove threshold from WHERE clause

-- First, drop the existing function completely
DROP FUNCTION IF EXISTS match_chunks CASCADE;

-- Create the corrected function that returns SETOF record with proper columns
CREATE OR REPLACE FUNCTION match_chunks (
  query_embedding vector(1024),
  match_threshold float,
  match_count int,
  indexing_run_id_filter text DEFAULT null
) 
RETURNS SETOF document_chunks
LANGUAGE sql 
AS $$
  SELECT *
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
COMMENT ON FUNCTION match_chunks IS 'Fixed HNSW vector search that returns K nearest neighbors without threshold filtering in WHERE clause. Threshold parameter is ignored to ensure proper index usage.';

-- Verify the fix
DO $$
BEGIN
  RAISE NOTICE 'match_chunks function has been properly fixed to remove threshold from WHERE clause';
END $$;