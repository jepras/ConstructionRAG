-- Migration: Add wiki generation support
-- Date: 2025-08-08
-- Description: Adds support for wiki generation from indexing runs

-- Create wiki_generation_runs table for tracking wiki generation
CREATE TABLE IF NOT EXISTS wiki_generation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indexing_run_id UUID NOT NULL REFERENCES indexing_runs(id) ON DELETE CASCADE,
    upload_type TEXT NOT NULL DEFAULT 'user_project' CHECK (upload_type IN ('email', 'user_project')),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    upload_id TEXT, -- For email uploads
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    language TEXT DEFAULT 'danish' CHECK (language IN ('danish', 'english')),
    model TEXT DEFAULT 'google/gemini-2.5-flash',
    step_results JSONB DEFAULT '{}',
    wiki_structure JSONB DEFAULT '{}',
    pages_metadata JSONB DEFAULT '{}', -- Store page titles, order, file paths
    storage_path TEXT, -- Base storage path for this wiki run
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_indexing_run_id ON wiki_generation_runs(indexing_run_id);
CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_upload_type ON wiki_generation_runs(upload_type);
CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_user_id ON wiki_generation_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_project_id ON wiki_generation_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_upload_id ON wiki_generation_runs(upload_id);
CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_status ON wiki_generation_runs(status);
CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_started_at ON wiki_generation_runs(started_at);

-- Enable Row Level Security (RLS)
ALTER TABLE wiki_generation_runs ENABLE ROW LEVEL SECURITY;

-- RLS policies for wiki_generation_runs
-- Users can view their own wiki generation runs (user projects)
CREATE POLICY "Users can view their own wiki generation runs" ON wiki_generation_runs
    FOR SELECT USING (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

-- Users can insert their own wiki generation runs (user projects)
CREATE POLICY "Users can insert their own wiki generation runs" ON wiki_generation_runs
    FOR INSERT WITH CHECK (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

-- Users can update their own wiki generation runs (user projects)
CREATE POLICY "Users can update their own wiki generation runs" ON wiki_generation_runs
    FOR UPDATE USING (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

-- Users can delete their own wiki generation runs (user projects)
CREATE POLICY "Users can delete their own wiki generation runs" ON wiki_generation_runs
    FOR DELETE USING (
        (upload_type = 'user_project' AND user_id = auth.uid()) OR
        (upload_type = 'email' AND upload_id IS NOT NULL)
    );

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_wiki_generation_runs_updated_at 
    BEFORE UPDATE ON wiki_generation_runs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column(); 