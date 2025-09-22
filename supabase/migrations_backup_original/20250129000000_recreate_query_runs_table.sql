-- Drop and recreate query_runs table with correct structure
-- This migration only affects the query_runs table, leaving other tables untouched

-- Drop existing query_runs table and related objects
DROP TABLE IF EXISTS query_runs CASCADE;

-- Create new query_runs table with correct structure
CREATE TABLE query_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User information
    user_id TEXT, -- Changed from UUID to TEXT to match our orchestrator
    
    -- Query information
    original_query TEXT NOT NULL, -- Renamed from query_text
    query_variations JSONB, -- Store the generated query variations
    
    -- Pipeline results
    search_results JSONB, -- Store the retrieved search results
    final_response TEXT, -- Renamed from response_text
    
    -- Performance metrics
    performance_metrics JSONB, -- Store model used, tokens, confidence, etc.
    quality_metrics JSONB, -- Store relevance, confidence, similarity scores
    
    -- Timing and status
    response_time_ms INTEGER, -- Response time in milliseconds
    error_message TEXT, -- Error message if pipeline failed
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_query_runs_user_id ON query_runs(user_id);
CREATE INDEX idx_query_runs_created_at ON query_runs(created_at DESC);
CREATE INDEX idx_query_runs_response_time ON query_runs(response_time_ms);

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_query_runs_updated_at 
    BEFORE UPDATE ON query_runs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create a view for query analytics
CREATE OR REPLACE VIEW query_analytics AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_queries,
    COUNT(CASE WHEN final_response IS NOT NULL THEN 1 END) as successful_queries,
    COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed_queries,
    AVG(response_time_ms) as avg_response_time_ms,
    AVG((performance_metrics->>'confidence')::float) as avg_confidence,
    AVG((quality_metrics->>'relevance_score')::float) as avg_relevance_score
FROM query_runs
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- Create a function to get recent query performance
CREATE OR REPLACE FUNCTION get_recent_query_performance(hours_back INTEGER DEFAULT 24)
RETURNS TABLE (
    total_queries BIGINT,
    successful_queries BIGINT,
    failed_queries BIGINT,
    avg_response_time_ms NUMERIC,
    success_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_queries,
        COUNT(CASE WHEN final_response IS NOT NULL THEN 1 END) as successful_queries,
        COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed_queries,
        AVG(response_time_ms) as avg_response_time_ms,
        CASE 
            WHEN COUNT(*) > 0 THEN 
                (COUNT(CASE WHEN final_response IS NOT NULL THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC) * 100
            ELSE 0 
        END as success_rate
    FROM query_runs
    WHERE created_at >= NOW() - INTERVAL '1 hour' * hours_back;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE query_runs IS 'Stores all queries processed through the query pipeline with results and metrics';
COMMENT ON COLUMN query_runs.query_variations IS 'JSON object containing semantic, hyde, and formal query variations';
COMMENT ON COLUMN query_runs.search_results IS 'Array of search results with content, similarity scores, and metadata';
COMMENT ON COLUMN query_runs.performance_metrics IS 'JSON object with model_used, tokens_used, confidence, sources_count';
COMMENT ON COLUMN query_runs.quality_metrics IS 'JSON object with relevance_score, confidence, top_similarity, result_count'; 