-- Checklist Analysis Feature Migration
-- This migration creates tables and policies for the checklist analysis feature

-- Create enums
CREATE TYPE analysis_status AS ENUM ('pending', 'running', 'completed', 'failed');
CREATE TYPE checklist_status AS ENUM ('found', 'missing', 'risk', 'conditions', 'pending_clarification');
CREATE TYPE access_level AS ENUM ('public', 'auth', 'owner', 'private');

-- Note: access_level might already exist, so we'll handle that gracefully
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'access_level') THEN
        CREATE TYPE access_level AS ENUM ('public', 'auth', 'owner', 'private');
    END IF;
END$$;

-- Checklist analysis runs table
CREATE TABLE IF NOT EXISTS checklist_analysis_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indexing_run_id UUID NOT NULL REFERENCES indexing_runs(id),
    user_id UUID REFERENCES auth.users(id),
    checklist_name VARCHAR(255) NOT NULL,
    checklist_content TEXT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    status analysis_status NOT NULL DEFAULT 'pending',
    raw_output TEXT,
    progress_current INT DEFAULT 0,
    progress_total INT DEFAULT 0,
    error_message TEXT,
    access_level access_level NOT NULL DEFAULT 'private',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Individual checklist results table
CREATE TABLE IF NOT EXISTS checklist_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id UUID NOT NULL REFERENCES checklist_analysis_runs(id) ON DELETE CASCADE,
    item_number VARCHAR(50) NOT NULL,
    item_name VARCHAR(500) NOT NULL,
    status checklist_status NOT NULL,
    description TEXT NOT NULL,
    confidence_score DECIMAL(3,2),
    source_document VARCHAR(255),
    source_page INTEGER,
    source_chunk_id UUID REFERENCES document_chunks(id),
    source_excerpt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Checklist templates table (for future use)
CREATE TABLE IF NOT EXISTS checklist_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'custom',
    is_public BOOLEAN DEFAULT FALSE,
    access_level access_level NOT NULL DEFAULT 'private',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_checklist_analysis_runs_indexing_run_id 
    ON checklist_analysis_runs(indexing_run_id);
CREATE INDEX IF NOT EXISTS idx_checklist_analysis_runs_user_id 
    ON checklist_analysis_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_checklist_analysis_runs_status 
    ON checklist_analysis_runs(status);
CREATE INDEX IF NOT EXISTS idx_checklist_results_analysis_run_id 
    ON checklist_results(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_checklist_results_status 
    ON checklist_results(status);
CREATE INDEX IF NOT EXISTS idx_checklist_templates_user_id 
    ON checklist_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_checklist_templates_category 
    ON checklist_templates(category);

-- Enable RLS
ALTER TABLE checklist_analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklist_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklist_templates ENABLE ROW LEVEL SECURITY;

-- RLS Policies for checklist_analysis_runs
CREATE POLICY "Users can access their own analysis runs" 
    ON checklist_analysis_runs
    FOR ALL 
    USING (
        CASE 
            WHEN access_level = 'public' THEN true
            WHEN access_level = 'auth' AND auth.uid() IS NOT NULL THEN true
            WHEN access_level = 'private' AND user_id = auth.uid() THEN true
            ELSE false
        END
    );

-- RLS Policies for checklist_results (inherit access from analysis runs)
CREATE POLICY "Users can access results for accessible analysis runs" 
    ON checklist_results
    FOR ALL 
    USING (
        EXISTS (
            SELECT 1 FROM checklist_analysis_runs 
            WHERE id = analysis_run_id 
            AND (
                CASE 
                    WHEN access_level = 'public' THEN true
                    WHEN access_level = 'auth' AND auth.uid() IS NOT NULL THEN true
                    WHEN access_level = 'private' AND user_id = auth.uid() THEN true
                    ELSE false
                END
            )
        )
    );

-- RLS Policies for checklist_templates
CREATE POLICY "Users can access their own templates or public templates" 
    ON checklist_templates
    FOR ALL 
    USING (
        CASE 
            WHEN is_public = true THEN true
            WHEN user_id = auth.uid() THEN true
            ELSE false
        END
    );

-- Grant necessary permissions
GRANT ALL ON checklist_analysis_runs TO authenticated;
GRANT ALL ON checklist_results TO authenticated;
GRANT ALL ON checklist_templates TO authenticated;

-- Allow anonymous users to read public checklist runs
GRANT SELECT ON checklist_analysis_runs TO anon;
GRANT SELECT ON checklist_results TO anon;
GRANT SELECT ON checklist_templates TO anon;