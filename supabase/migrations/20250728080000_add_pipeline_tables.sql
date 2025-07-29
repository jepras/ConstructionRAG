-- Migration: Add pipeline tables for two-pipeline architecture
-- Date: 2025-07-28

-- Create indexing_runs table for background processing tracking
CREATE TABLE IF NOT EXISTS indexing_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    step_results JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create query_runs table for real-time query tracking
CREATE TABLE IF NOT EXISTS query_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID, -- Future: group queries by project
    query_text TEXT NOT NULL,
    response_text TEXT,
    retrieval_metadata JSONB DEFAULT '{}',
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user_config_overrides table for future UI configurability
CREATE TABLE IF NOT EXISTS user_config_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    config_type TEXT NOT NULL CHECK (config_type IN ('indexing', 'querying')),
    config_key TEXT NOT NULL,
    config_value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, config_type, config_key)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_indexing_runs_document_id ON indexing_runs(document_id);
CREATE INDEX IF NOT EXISTS idx_indexing_runs_status ON indexing_runs(status);
CREATE INDEX IF NOT EXISTS idx_indexing_runs_started_at ON indexing_runs(started_at);

CREATE INDEX IF NOT EXISTS idx_query_runs_user_id ON query_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_query_runs_created_at ON query_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_query_runs_project_id ON query_runs(project_id);

CREATE INDEX IF NOT EXISTS idx_user_config_overrides_user_id ON user_config_overrides(user_id);
CREATE INDEX IF NOT EXISTS idx_user_config_overrides_config_type ON user_config_overrides(config_type);

-- Add RLS policies for security
ALTER TABLE indexing_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_config_overrides ENABLE ROW LEVEL SECURITY;

-- RLS policies for indexing_runs (users can only see their own document runs)
CREATE POLICY "Users can view indexing runs for their own documents" ON indexing_runs
    FOR SELECT USING (
        document_id IN (
            SELECT id FROM documents WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert indexing runs for their own documents" ON indexing_runs
    FOR INSERT WITH CHECK (
        document_id IN (
            SELECT id FROM documents WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update indexing runs for their own documents" ON indexing_runs
    FOR UPDATE USING (
        document_id IN (
            SELECT id FROM documents WHERE user_id = auth.uid()
        )
    );

-- RLS policies for query_runs (users can only see their own queries)
CREATE POLICY "Users can view their own query runs" ON query_runs
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own query runs" ON query_runs
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own query runs" ON query_runs
    FOR UPDATE USING (user_id = auth.uid());

-- RLS policies for user_config_overrides (users can only see their own configs)
CREATE POLICY "Users can view their own config overrides" ON user_config_overrides
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own config overrides" ON user_config_overrides
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own config overrides" ON user_config_overrides
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Users can delete their own config overrides" ON user_config_overrides
    FOR DELETE USING (user_id = auth.uid());

-- Add updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_indexing_runs_updated_at 
    BEFORE UPDATE ON indexing_runs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_config_overrides_updated_at 
    BEFORE UPDATE ON user_config_overrides 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 