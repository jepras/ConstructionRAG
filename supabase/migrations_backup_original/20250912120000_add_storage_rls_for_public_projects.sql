-- Storage RLS policies to allow public access to converted user project files
-- This allows anonymous users to access wiki files from user projects that have been
-- converted to public (upload_type = 'email' AND access_level = 'public')

-- Enable RLS on the storage.objects table for the pipeline-assets bucket
-- Note: This only affects the pipeline-assets bucket, not other buckets

-- Function to extract indexing_run_id from user project wiki file paths
-- Path format: users/{user_id}/projects/{project_id}/index-runs/{indexing_run_id}/wiki/{wiki_run_id}/page-X.md
CREATE OR REPLACE FUNCTION extract_indexing_run_id_from_user_path(file_path text)
RETURNS uuid
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    -- Extract UUID from the path pattern: users/.../index-runs/{uuid}/wiki/...
    -- Use regex to match UUID pattern after 'index-runs/'
    RETURN (
        SELECT (regexp_match(
            file_path, 
            'users/[^/]+/projects/[^/]+/index-runs/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', 
            'i'
        ))[1]::uuid
    );
EXCEPTION
    WHEN others THEN
        RETURN NULL;
END;
$$;

-- Storage policy for SELECT (download/view) operations
DROP POLICY IF EXISTS "Allow public access to converted user project wikis" ON storage.objects;
CREATE POLICY "Allow public access to converted user project wikis"
ON storage.objects FOR SELECT
TO public
USING (
    bucket_id = 'pipeline-assets'
    AND (
        -- Allow access to email upload files (existing behavior)
        name LIKE 'email-uploads/%'
        OR
        -- Allow access to user project files IF they have been converted to public
        (
            name LIKE 'users/%/projects/%/index-runs/%/wiki/%'
            AND EXISTS (
                SELECT 1 FROM public.indexing_runs ir
                WHERE ir.id = extract_indexing_run_id_from_user_path(name)
                AND ir.upload_type = 'email'
                AND ir.access_level = 'public'
            )
        )
    )
);

-- Ensure authenticated users can still access their own files
DROP POLICY IF EXISTS "Allow users access to their own files" ON storage.objects;
CREATE POLICY "Allow users access to their own files"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'pipeline-assets'
    AND (
        -- Email uploads (public)
        name LIKE 'email-uploads/%'
        OR
        -- User's own project files
        (
            name LIKE 'users/%'
            AND name LIKE CONCAT('users/', auth.uid()::text, '/%')
        )
        OR
        -- Converted public user project files (same as anonymous access)
        (
            name LIKE 'users/%/projects/%/index-runs/%/wiki/%'
            AND EXISTS (
                SELECT 1 FROM public.indexing_runs ir
                WHERE ir.id = extract_indexing_run_id_from_user_path(name)
                AND ir.upload_type = 'email'
                AND ir.access_level = 'public'
            )
        )
    )
);

-- Service role should have full access (for uploads and management)
DROP POLICY IF EXISTS "Service role has full access" ON storage.objects;
CREATE POLICY "Service role has full access"
ON storage.objects
TO service_role
USING (bucket_id = 'pipeline-assets');

-- Create index on indexing_runs for faster lookups by the storage policies
CREATE INDEX IF NOT EXISTS idx_indexing_runs_upload_type_access_level 
ON public.indexing_runs(upload_type, access_level) 
WHERE upload_type = 'email' AND access_level = 'public';

-- Test the function with a sample path (this will show in logs during migration)
DO $$
DECLARE
    test_path text := 'users/a4be935d-dd17-4db2-aa4e-b4989277bb1a/projects/a231b3cb-cf4c-4d22-8211-e184a2f33cb6/index-runs/181d6cd9-b815-4347-bc0b-1df8dca67519/wiki/35d8fb25-09cc-4819-bf36-cc8d3cc88235/page-1.md';
    extracted_id uuid;
BEGIN
    extracted_id := extract_indexing_run_id_from_user_path(test_path);
    RAISE NOTICE 'Test path: %', test_path;
    RAISE NOTICE 'Extracted indexing_run_id: %', extracted_id;
    
    -- Check if the test case matches your converted project
    IF extracted_id = '181d6cd9-b815-4347-bc0b-1df8dca67519'::uuid THEN
        RAISE NOTICE 'SUCCESS: Function correctly extracted indexing_run_id for your converted project!';
    ELSE
        RAISE WARNING 'Function did not extract the expected indexing_run_id. Expected: 181d6cd9-b815-4347-bc0b-1df8dca67519, Got: %', extracted_id;
    END IF;
END $$;