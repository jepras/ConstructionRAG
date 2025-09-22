-- Fix the indexing_run_id filter in match_chunks function
-- Date: 2025-09-02
-- Description: Fix UUID to text comparison issue in the filter

-- Drop the broken function
DROP FUNCTION IF EXISTS public.match_chunks CASCADE;

-- Create the FIXED function with proper UUID handling
CREATE OR REPLACE FUNCTION public.match_chunks (
  query_embedding vector(1024),
  match_threshold float,  -- IGNORED for backward compatibility
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
      OR dc.indexing_run_id = indexing_run_id_filter::uuid  -- Cast filter to UUID instead
    )
  ORDER BY dc.embedding_1024 <=> query_embedding ASC
  LIMIT LEAST(match_count, 200);
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.match_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_chunks TO anon;
GRANT EXECUTE ON FUNCTION public.match_chunks TO service_role;

-- Add comment
COMMENT ON FUNCTION public.match_chunks IS 'FIXED: UUID comparison now works correctly. Returns K nearest neighbors using HNSW index. Threshold parameter is IGNORED.';

-- Verify
DO $$
BEGIN
  RAISE NOTICE 'match_chunks function fixed: indexing_run_id filter now properly casts text to UUID';
END $$;