-- Migration: Add RLS policy for public access to indexing runs
-- Date: 2025-08-11
-- Description: Allow anonymous users to access indexing_runs with access_level = 'public'

-- Add policy to allow public read access to indexing runs with access_level = 'public'
CREATE POLICY "Public can access public indexing runs" ON indexing_runs
    FOR SELECT USING (access_level = 'public');

-- Verify the policy works by testing the specific case
-- This comment documents the expected behavior:
-- - Anonymous users can SELECT from indexing_runs WHERE access_level = 'public'
-- - This allows QueryService to retrieve public email uploads for access validation
-- - Application code still enforces upload_type = 'email' check after RLS allows the SELECT