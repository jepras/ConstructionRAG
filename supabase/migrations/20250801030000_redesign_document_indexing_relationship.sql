-- Migration: Redesign document-indexing relationship
-- Date: 2025-08-01
-- Description: Clean up schema and implement proper many-to-many relationship

-- Step 1: Drop all existing RLS policies for a clean slate
DROP POLICY IF EXISTS "Users can view their own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update their own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
DROP POLICY IF EXISTS "Users can insert their own documents" ON documents;
DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;
DROP POLICY IF EXISTS "Users can view their own pipeline runs" ON pipeline_runs;
DROP POLICY IF EXISTS "Users can insert pipeline runs for their documents" ON pipeline_runs;
DROP POLICY IF EXISTS "Users can view chunks from their documents" ON document_chunks;
DROP POLICY IF EXISTS "Users can insert chunks for their documents" ON document_chunks;
DROP POLICY IF EXISTS "Users can view their own queries" ON queries;
DROP POLICY IF EXISTS "Users can insert their own queries" ON queries;
DROP POLICY IF EXISTS "Users can view indexing runs for their own documents" ON indexing_runs;
DROP POLICY IF EXISTS "Users can insert indexing runs for their own documents" ON indexing_runs;
DROP POLICY IF EXISTS "Users can update indexing runs for their own documents" ON indexing_runs;
DROP POLICY IF EXISTS "Users can view their own query runs" ON query_runs;
DROP POLICY IF EXISTS "Users can insert their own query runs" ON query_runs;
DROP POLICY IF EXISTS "Users can update their own query runs" ON query_runs;
DROP POLICY IF EXISTS "Users can view their own config overrides" ON user_config_overrides;
DROP POLICY IF EXISTS "Users can insert their own config overrides" ON user_config_overrides;
DROP POLICY IF EXISTS "Users can update their own config overrides" ON user_config_overrides;
DROP POLICY IF EXISTS "Users can delete their own config overrides" ON user_config_overrides;
DROP POLICY IF EXISTS "Users can view their own projects" ON projects;
DROP POLICY IF EXISTS "Users can insert their own projects" ON projects;
DROP POLICY IF EXISTS "Users can update their own projects" ON projects;
DROP POLICY IF EXISTS "Users can delete their own projects" ON projects;
DROP POLICY IF EXISTS "Public can view completed email uploads" ON email_uploads;
DROP POLICY IF EXISTS "System can manage email uploads" ON email_uploads;
DROP POLICY IF EXISTS "Allow email uploads insert" ON email_uploads;
DROP POLICY IF EXISTS "Allow indexing runs insert" ON indexing_runs;

-- Step 2: Remove problematic constraint
ALTER TABLE indexing_runs DROP CONSTRAINT IF EXISTS check_document_id_for_user_projects;

-- Step 3: Create junction table for many-to-many relationship
CREATE TABLE IF NOT EXISTS indexing_run_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indexing_run_id UUID NOT NULL REFERENCES indexing_runs(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(indexing_run_id, document_id)
);

-- Step 4: Remove document_id from indexing_runs table
ALTER TABLE indexing_runs DROP COLUMN IF EXISTS document_id;

-- Step 5: Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_indexing_run_documents_indexing_run_id ON indexing_run_documents(indexing_run_id);
CREATE INDEX IF NOT EXISTS idx_indexing_run_documents_document_id ON indexing_run_documents(document_id);

-- Step 6: Enable RLS on new table
ALTER TABLE indexing_run_documents ENABLE ROW LEVEL SECURITY;

-- Step 7: Create minimal, simple RLS policies

-- Documents: Users can access their own documents
CREATE POLICY "Users can access their own documents" ON documents
    FOR ALL USING (user_id::uuid = auth.uid());

-- Documents: System can access all documents (for processing)
CREATE POLICY "System can access all documents" ON documents
    FOR ALL USING (auth.role() = 'service_role');

-- Indexing runs: Users can access runs for documents they own
CREATE POLICY "Users can access indexing runs for their documents" ON indexing_runs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM indexing_run_documents ird
            JOIN documents d ON ird.document_id = d.id
            WHERE ird.indexing_run_id = indexing_runs.id
            AND d.user_id::uuid = auth.uid()
        )
    );

-- Indexing runs: System can access all runs
CREATE POLICY "System can access all indexing runs" ON indexing_runs
    FOR ALL USING (auth.role() = 'service_role');

-- Indexing run documents: Users can access junction records for their documents
CREATE POLICY "Users can access indexing run documents for their documents" ON indexing_run_documents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = indexing_run_documents.document_id
            AND d.user_id::uuid = auth.uid()
        )
    );

-- Indexing run documents: System can access all junction records
CREATE POLICY "System can access all indexing run documents" ON indexing_run_documents
    FOR ALL USING (auth.role() = 'service_role');

-- Email uploads: Public read access for completed uploads
CREATE POLICY "Public can view completed email uploads" ON email_uploads
    FOR SELECT USING (status = 'completed' AND expires_at > NOW());

-- Email uploads: System can manage all email uploads
CREATE POLICY "System can manage email uploads" ON email_uploads
    FOR ALL USING (auth.role() = 'service_role');

-- Document chunks: Users can access chunks for their documents
CREATE POLICY "Users can access chunks for their documents" ON document_chunks
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = document_chunks.document_id
            AND d.user_id::uuid = auth.uid()
        )
    );

-- Document chunks: System can access all chunks
CREATE POLICY "System can access all document chunks" ON document_chunks
    FOR ALL USING (auth.role() = 'service_role');

-- Projects: Users can access their own projects
CREATE POLICY "Users can access their own projects" ON projects
    FOR ALL USING (user_id::uuid = auth.uid());

-- Projects: System can access all projects
CREATE POLICY "System can access all projects" ON projects
    FOR ALL USING (auth.role() = 'service_role');

-- Query runs: Users can access their own queries
CREATE POLICY "Users can access their own query runs" ON query_runs
    FOR ALL USING (user_id::uuid = auth.uid());

-- Query runs: System can access all queries
CREATE POLICY "System can access all query runs" ON query_runs
    FOR ALL USING (auth.role() = 'service_role');

-- User config overrides: Users can access their own configs
CREATE POLICY "Users can access their own config overrides" ON user_config_overrides
    FOR ALL USING (user_id::uuid = auth.uid());

-- User config overrides: System can access all configs
CREATE POLICY "System can access all user config overrides" ON user_config_overrides
    FOR ALL USING (auth.role() = 'service_role');

-- User profiles: Users can access their own profile
CREATE POLICY "Users can access their own profile" ON user_profiles
    FOR ALL USING (id = auth.uid());

-- User profiles: System can access all profiles
CREATE POLICY "System can access all user profiles" ON user_profiles
    FOR ALL USING (auth.role() = 'service_role');

-- Queries: Users can access their own queries
CREATE POLICY "Users can access their own queries" ON queries
    FOR ALL USING (user_id = auth.uid());

-- Queries: System can access all queries
CREATE POLICY "System can access all queries" ON queries
    FOR ALL USING (auth.role() = 'service_role');

-- Pipeline runs: Users can access runs for their documents
CREATE POLICY "Users can access pipeline runs for their documents" ON pipeline_runs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = pipeline_runs.document_id
            AND d.user_id::uuid = auth.uid()
        )
    );

-- Pipeline runs: System can access all runs
CREATE POLICY "System can access all pipeline runs" ON pipeline_runs
    FOR ALL USING (auth.role() = 'service_role'); 