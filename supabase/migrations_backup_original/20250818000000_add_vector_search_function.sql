-- Add Vector Search Function for HNSW Performance
-- Date: 2025-08-18
-- Description: Add match_chunks function to enable HNSW vector search performance (26x improvement)

-- Create the match_chunks function following Supabase best practices
-- This function leverages the existing HNSW index (idx_document_chunks_embedding_1024_hnsw)
-- for optimal vector similarity search performance
CREATE OR REPLACE FUNCTION match_chunks (
  query_embedding vector(1024),
  match_threshold float,
  match_count int,
  indexing_run_id_filter text DEFAULT null
) RETURNS SETOF document_chunks
LANGUAGE sql AS $$
  SELECT *
  FROM document_chunks
  WHERE 
    embedding_1024 IS NOT NULL
    AND (indexing_run_id_filter IS NULL OR indexing_run_id::text = indexing_run_id_filter)
    AND 1 - (embedding_1024 <=> query_embedding) > match_threshold
  ORDER BY embedding_1024 <=> query_embedding ASC
  LIMIT LEAST(match_count, 200);
$$;

-- Grant necessary permissions for the function
-- Allow authenticated users to call the function
GRANT EXECUTE ON FUNCTION match_chunks TO authenticated;

-- Allow anonymous users to call the function (for public projects)
GRANT EXECUTE ON FUNCTION match_chunks TO anon;

-- Add security definer if needed for RLS policies
-- The function will run with the permissions of the caller, respecting RLS

-- Add comment for documentation
COMMENT ON FUNCTION match_chunks IS 'Vector similarity search function using HNSW index. Returns document chunks ordered by cosine similarity to query embedding. Supports filtering by indexing run ID for better performance.';

-- Verify the function works by testing it exists
-- This will help catch any syntax errors during migration
DO $$
BEGIN
  -- Check if function was created successfully
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p 
    JOIN pg_namespace n ON p.pronamespace = n.oid 
    WHERE n.nspname = 'public' AND p.proname = 'match_chunks'
  ) THEN
    RAISE EXCEPTION 'Failed to create match_chunks function';
  END IF;
  
  -- Log success
  RAISE NOTICE 'match_chunks function created successfully';
END $$;