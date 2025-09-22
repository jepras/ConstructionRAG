-- Revert to the working version from migration 20250902000003
-- Date: 2025-09-02
-- Description: Revert the UUID cast change that broke the function

-- Drop the broken function
DROP FUNCTION IF EXISTS public.match_chunks CASCADE;

-- Recreate the WORKING function from migration 20250902000003
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
COMMENT ON FUNCTION public.match_chunks IS 'REVERTED to working version: Returns K nearest neighbors using HNSW index. Threshold parameter is IGNORED.';

-- Verify
DO $$
BEGIN
  RAISE NOTICE 'Reverted match_chunks to the working version from migration 20250902000003';
END $$;