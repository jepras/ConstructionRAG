-- Force complete replacement of match_chunks function
-- Date: 2025-09-02  
-- Description: Completely drop and recreate to ensure no old code remains

-- Drop ALL versions of the function
DROP FUNCTION IF EXISTS public.match_chunks(vector(1024), float, int, text) CASCADE;
DROP FUNCTION IF EXISTS public.match_chunks(vector(1024), float, int) CASCADE;
DROP FUNCTION IF EXISTS public.match_chunks CASCADE;

-- Wait a moment to ensure cleanup
DO $$ BEGIN PERFORM pg_sleep(0.1); END $$;

-- Create the CORRECT function without ANY threshold filtering
CREATE OR REPLACE FUNCTION public.match_chunks (
  query_embedding vector(1024),
  match_threshold float,  -- This parameter is IGNORED for backward compatibility
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
LANGUAGE plpgsql  -- Using plpgsql for better control
AS $$
BEGIN
  -- IMPORTANT: We completely IGNORE match_threshold to ensure we get K nearest neighbors
  -- The threshold should be applied in application code if needed
  
  RETURN QUERY
  SELECT 
    dc.id,
    dc.content,
    dc.metadata,
    dc.embedding_1024,
    dc.document_id,
    dc.indexing_run_id,
    1 - (dc.embedding_1024 <=> query_embedding) as similarity
  FROM document_chunks dc
  WHERE 
    dc.embedding_1024 IS NOT NULL
    AND (
      indexing_run_id_filter IS NULL 
      OR dc.indexing_run_id::text = indexing_run_id_filter
    )
  ORDER BY dc.embedding_1024 <=> query_embedding ASC
  LIMIT LEAST(match_count, 200);
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.match_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_chunks TO anon;
GRANT EXECUTE ON FUNCTION public.match_chunks TO service_role;

-- Add comment
COMMENT ON FUNCTION public.match_chunks IS 'FINAL FIX: Returns K nearest neighbors using HNSW index. Threshold parameter is IGNORED - filtering should be done in application code. This ensures the index is used properly.';

-- Verify the function exists and log success
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_proc p 
    JOIN pg_namespace n ON p.pronamespace = n.oid 
    WHERE n.nspname = 'public' AND p.proname = 'match_chunks'
  ) THEN
    RAISE NOTICE 'SUCCESS: match_chunks function has been completely replaced. Threshold is now IGNORED.';
  ELSE
    RAISE EXCEPTION 'ERROR: Failed to create match_chunks function';
  END IF;
END $$;