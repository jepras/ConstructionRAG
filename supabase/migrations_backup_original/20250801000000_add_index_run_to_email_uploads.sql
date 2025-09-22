-- Add index_run_id to email_uploads table to support new storage structure
-- This allows email uploads to follow the same structure as user projects

-- Add index_run_id column to email_uploads table
ALTER TABLE email_uploads ADD COLUMN IF NOT EXISTS index_run_id UUID;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS idx_email_uploads_index_run_id ON email_uploads(index_run_id);

-- Add foreign key constraint to indexing_runs table
ALTER TABLE email_uploads 
ADD CONSTRAINT fk_email_uploads_index_run_id 
FOREIGN KEY (index_run_id) REFERENCES indexing_runs(id) ON DELETE CASCADE;

-- Update RLS policies to include index_run_id
DROP POLICY IF EXISTS "Public can view completed email uploads" ON email_uploads;
CREATE POLICY "Public can view completed email uploads" ON email_uploads
    FOR SELECT USING (status = 'completed' AND expires_at > NOW());

-- Update documents table RLS to include index_run_id for email uploads
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
CREATE POLICY "Users can view their own documents" ON documents
    FOR SELECT USING (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND upload_id IN (
            SELECT id FROM email_uploads WHERE status = 'completed' AND expires_at > NOW()
        ))
    );

-- Update indexing_runs table RLS to include email uploads
DROP POLICY IF EXISTS "Users can view indexing runs for their own documents" ON indexing_runs;
CREATE POLICY "Users can view indexing runs for their own documents" ON indexing_runs
    FOR SELECT USING (
        (upload_type = 'user_project' AND document_id IN (
            SELECT id FROM documents WHERE user_id = auth.uid()
        )) OR
        (upload_type = 'email' AND upload_id IN (
            SELECT id FROM email_uploads WHERE status = 'completed' AND expires_at > NOW()
        ))
    );

-- Add comment to explain the new structure
COMMENT ON COLUMN email_uploads.index_run_id IS 'References the index run that processes all PDFs in this email upload session'; 