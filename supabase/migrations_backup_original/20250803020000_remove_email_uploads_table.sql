-- Migration: Remove email_uploads table and clean up related fields
-- Date: 2025-08-03
-- Description: Removes redundant email_uploads table and simplifies storage structure

-- Add expires_at field to documents table for email uploads
ALTER TABLE documents ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;

-- Set expires_at for existing email uploads (30 days from created_at)
UPDATE documents 
SET expires_at = created_at + INTERVAL '30 days'
WHERE upload_type = 'email' AND expires_at IS NULL;

-- Remove upload_id field from indexing_runs table (no longer needed)
ALTER TABLE indexing_runs DROP COLUMN IF EXISTS upload_id;

-- Remove upload_id field from documents table (no longer needed)
ALTER TABLE documents DROP COLUMN IF EXISTS upload_id;

-- Drop email_uploads table and all its data
DROP TABLE IF EXISTS email_uploads CASCADE;

-- Update RLS policies to remove email_uploads references
-- Remove the policy that references email_uploads table
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;

-- Create new simplified policy for documents
CREATE POLICY "Users can view their own documents" ON documents
    FOR SELECT USING (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND expires_at > NOW())
    );

-- Update the insert policy
DROP POLICY IF EXISTS "Users can insert their own documents" ON documents;
CREATE POLICY "Users can insert their own documents" ON documents
    FOR INSERT WITH CHECK (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email')
    );

-- Update the update policy
DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
CREATE POLICY "Users can update their own documents" ON documents
    FOR UPDATE USING (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND expires_at > NOW())
    );

-- Create index for expires_at field for efficient cleanup queries
CREATE INDEX IF NOT EXISTS idx_documents_expires_at ON documents(expires_at);

-- Add comment for documentation
COMMENT ON COLUMN documents.expires_at IS 'Expiration timestamp for email uploads (30 days from creation)';

-- Create function to cleanup expired email uploads
CREATE OR REPLACE FUNCTION cleanup_expired_email_uploads()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM documents 
    WHERE upload_type = 'email' 
    AND expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add comment for the cleanup function
COMMENT ON FUNCTION cleanup_expired_email_uploads() IS 'Removes expired email upload documents (older than 30 days)'; 