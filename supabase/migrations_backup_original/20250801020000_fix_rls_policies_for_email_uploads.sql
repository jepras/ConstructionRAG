-- Migration: Fix RLS policies and status constraints for email uploads
-- Date: 2025-08-01
-- Description: Fix RLS policies and status constraints to allow anonymous email uploads

-- Drop the problematic indexing_runs INSERT policy that requires auth.uid()
DROP POLICY IF EXISTS "Users can insert indexing runs for their own documents" ON indexing_runs;

-- Create a new INSERT policy that allows both authenticated users and system operations
CREATE POLICY "Allow indexing runs insert" ON indexing_runs
    FOR INSERT WITH CHECK (
        -- For user projects: require authenticated user and valid document
        (upload_type = 'user_project' AND auth.uid() IS NOT NULL AND document_id IN (
            SELECT id FROM documents WHERE user_id = auth.uid()
        )) OR
        -- For email uploads: allow system operations (no auth required)
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

-- Add specific INSERT policy for email_uploads
CREATE POLICY "Allow email uploads insert" ON email_uploads
    FOR INSERT WITH CHECK (true); -- Allow all inserts for email uploads

-- Update the system policy for email_uploads to be more specific
DROP POLICY IF EXISTS "System can manage email uploads" ON email_uploads;
CREATE POLICY "System can manage email uploads" ON email_uploads
    FOR ALL USING (true); -- System-level access for all operations

-- Fix status constraint for indexing_runs to allow 'processing' status
ALTER TABLE indexing_runs DROP CONSTRAINT IF EXISTS indexing_runs_status_check;
ALTER TABLE indexing_runs ADD CONSTRAINT indexing_runs_status_check 
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'processing')); 