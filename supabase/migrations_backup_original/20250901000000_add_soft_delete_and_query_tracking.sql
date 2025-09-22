-- Add soft delete columns to projects table
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Add index for efficient filtering of non-deleted projects
CREATE INDEX IF NOT EXISTS idx_projects_deleted_at ON projects(deleted_at) WHERE deleted_at IS NULL;

-- Add indexing_run_id to query_runs table to track which indexing run was queried
ALTER TABLE query_runs 
ADD COLUMN IF NOT EXISTS indexing_run_id UUID REFERENCES indexing_runs(id) ON DELETE SET NULL;

-- Add index for efficient lookup of queries by indexing run
CREATE INDEX IF NOT EXISTS idx_query_runs_indexing_run_id ON query_runs(indexing_run_id);

-- Update RLS policies for projects to exclude soft-deleted records
-- Drop existing select policy if exists
DROP POLICY IF EXISTS "Users can view own projects" ON projects;

-- Create new policy that excludes soft-deleted projects
CREATE POLICY "Users can view own non-deleted projects" ON projects
    FOR SELECT
    USING (auth.uid() = user_id AND deleted_at IS NULL);

-- Keep other CRUD policies as they are (INSERT, UPDATE, DELETE remain unchanged)