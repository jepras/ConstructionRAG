-- Migration: Add storage structure support for upload types and projects
-- Date: 2025-07-31
-- Description: Adds support for email uploads and user projects with proper storage structure

-- Create projects table for user project organization
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create email_uploads table for anonymous email-based uploads
CREATE TABLE IF NOT EXISTS email_uploads (
    id TEXT PRIMARY KEY, -- upload_id from storage path
    email TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER,
    status TEXT DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    public_url TEXT, -- Generated page URL
    processing_results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '30 days')
);

-- Add upload type support to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS upload_type TEXT DEFAULT 'user_project' CHECK (upload_type IN ('email', 'user_project'));
ALTER TABLE documents ADD COLUMN IF NOT EXISTS upload_id TEXT; -- For email uploads
ALTER TABLE documents ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE; -- For user projects
ALTER TABLE documents ADD COLUMN IF NOT EXISTS index_run_id UUID; -- For user projects (references indexing_runs.id)

-- Add upload context to indexing_runs table
ALTER TABLE indexing_runs ADD COLUMN IF NOT EXISTS upload_type TEXT DEFAULT 'user_project' CHECK (upload_type IN ('email', 'user_project'));
ALTER TABLE indexing_runs ADD COLUMN IF NOT EXISTS upload_id TEXT; -- For email uploads
ALTER TABLE indexing_runs ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE; -- For user projects

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at);

CREATE INDEX IF NOT EXISTS idx_email_uploads_email ON email_uploads(email);
CREATE INDEX IF NOT EXISTS idx_email_uploads_status ON email_uploads(status);
CREATE INDEX IF NOT EXISTS idx_email_uploads_created_at ON email_uploads(created_at);
CREATE INDEX IF NOT EXISTS idx_email_uploads_expires_at ON email_uploads(expires_at);

CREATE INDEX IF NOT EXISTS idx_documents_upload_type ON documents(upload_type);
CREATE INDEX IF NOT EXISTS idx_documents_upload_id ON documents(upload_id);
CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_index_run_id ON documents(index_run_id);

CREATE INDEX IF NOT EXISTS idx_indexing_runs_upload_type ON indexing_runs(upload_type);
CREATE INDEX IF NOT EXISTS idx_indexing_runs_upload_id ON indexing_runs(upload_id);
CREATE INDEX IF NOT EXISTS idx_indexing_runs_project_id ON indexing_runs(project_id);

-- Enable Row Level Security (RLS)
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_uploads ENABLE ROW LEVEL SECURITY;

-- RLS policies for projects (users can only see their own projects)
CREATE POLICY "Users can view their own projects" ON projects
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own projects" ON projects
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own projects" ON projects
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Users can delete their own projects" ON projects
    FOR DELETE USING (user_id = auth.uid());

-- RLS policies for email_uploads (public read for completed uploads, restricted for processing)
CREATE POLICY "Public can view completed email uploads" ON email_uploads
    FOR SELECT USING (status = 'completed' AND expires_at > NOW());

CREATE POLICY "System can manage email uploads" ON email_uploads
    FOR ALL USING (true); -- System-level access for processing

-- Update existing RLS policies for documents to include upload type
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
CREATE POLICY "Users can view their own documents" ON documents
    FOR SELECT USING (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND upload_id IN (
            SELECT id FROM email_uploads WHERE status = 'completed' AND expires_at > NOW()
        ))
    );

DROP POLICY IF EXISTS "Users can insert their own documents" ON documents;
CREATE POLICY "Users can insert their own documents" ON documents
    FOR INSERT WITH CHECK (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
CREATE POLICY "Users can update their own documents" ON documents
    FOR UPDATE USING (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

-- Update existing RLS policies for indexing_runs to include upload type
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

DROP POLICY IF EXISTS "Users can insert indexing runs for their own documents" ON indexing_runs;
CREATE POLICY "Users can insert indexing runs for their own documents" ON indexing_runs
    FOR INSERT WITH CHECK (
        (upload_type = 'user_project' AND document_id IN (
            SELECT id FROM documents WHERE user_id = auth.uid()
        )) OR
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

DROP POLICY IF EXISTS "Users can update indexing runs for their own documents" ON indexing_runs;
CREATE POLICY "Users can update indexing runs for their own documents" ON indexing_runs
    FOR UPDATE USING (
        (upload_type = 'user_project' AND document_id IN (
            SELECT id FROM documents WHERE user_id = auth.uid()
        )) OR
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

-- Add updated_at trigger for projects table
CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add helper functions for storage path generation
CREATE OR REPLACE FUNCTION get_storage_path_for_document(
    doc_upload_type TEXT,
    doc_upload_id TEXT,
    doc_user_id UUID,
    doc_project_id UUID,
    doc_index_run_id UUID,
    doc_id UUID,
    file_type TEXT,
    filename TEXT
) RETURNS TEXT AS $$
BEGIN
    IF doc_upload_type = 'email' THEN
        RETURN 'email-uploads/' || doc_upload_id || '/processing/' || doc_id || '/' || file_type || '/' || filename;
    ELSE
        RETURN 'users/' || doc_user_id || '/projects/' || doc_project_id || '/index-runs/' || doc_index_run_id || '/' || doc_id || '/' || file_type || '/' || filename;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Add function to cleanup expired email uploads
CREATE OR REPLACE FUNCTION cleanup_expired_email_uploads()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM email_uploads 
    WHERE expires_at < NOW() AND status != 'processing';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add function to get storage usage statistics
CREATE OR REPLACE FUNCTION get_storage_usage_stats(user_uuid UUID DEFAULT NULL)
RETURNS TABLE(
    upload_type TEXT,
    total_documents BIGINT,
    total_size_bytes BIGINT,
    avg_file_size_bytes NUMERIC
) AS $$
BEGIN
    IF user_uuid IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            d.upload_type,
            COUNT(*) as total_documents,
            COALESCE(SUM(d.file_size), 0) as total_size_bytes,
            COALESCE(AVG(d.file_size), 0) as avg_file_size_bytes
        FROM documents d
        WHERE d.user_id = user_uuid
        GROUP BY d.upload_type;
    ELSE
        RETURN QUERY
        SELECT 
            d.upload_type,
            COUNT(*) as total_documents,
            COALESCE(SUM(d.file_size), 0) as total_size_bytes,
            COALESCE(AVG(d.file_size), 0) as avg_file_size_bytes
        FROM documents d
        GROUP BY d.upload_type;
    END IF;
END;
$$ LANGUAGE plpgsql; 