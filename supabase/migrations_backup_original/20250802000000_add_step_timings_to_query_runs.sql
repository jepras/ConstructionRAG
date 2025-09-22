-- Add step_timings column to query_runs table
-- This migration adds individual step timing information to track pipeline performance

-- Add step_timings column to store individual step execution times
ALTER TABLE query_runs 
ADD COLUMN step_timings JSONB;

-- Add comment for documentation
COMMENT ON COLUMN query_runs.step_timings IS 'JSON object containing individual step execution times in seconds (e.g., {"query_processing": 1.23, "retrieval": 2.45, "generation": 9.12})';

-- Update the query_analytics view to include step timing information
CREATE OR REPLACE VIEW query_analytics AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_queries,
    COUNT(CASE WHEN final_response IS NOT NULL THEN 1 END) as successful_queries,
    COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed_queries,
    AVG(response_time_ms) as avg_response_time_ms,
    AVG((performance_metrics->>'confidence')::float) as avg_confidence,
    AVG((quality_metrics->>'relevance_score')::float) as avg_relevance_score,
    -- Add step timing averages
    AVG((step_timings->>'query_processing')::float) as avg_query_processing_time,
    AVG((step_timings->>'retrieval')::float) as avg_retrieval_time,
    AVG((step_timings->>'generation')::float) as avg_generation_time
FROM query_runs
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- Drop the existing function first, then recreate with new return type
DROP FUNCTION IF EXISTS get_recent_query_performance(INTEGER);

-- Update the get_recent_query_performance function to include step timing metrics
CREATE OR REPLACE FUNCTION get_recent_query_performance(hours_back INTEGER DEFAULT 24)
RETURNS TABLE (
    total_queries BIGINT,
    successful_queries BIGINT,
    failed_queries BIGINT,
    avg_response_time_ms NUMERIC,
    success_rate NUMERIC,
    avg_query_processing_time NUMERIC,
    avg_retrieval_time NUMERIC,
    avg_generation_time NUMERIC
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
        END as success_rate,
        AVG((step_timings->>'query_processing')::float) as avg_query_processing_time,
        AVG((step_timings->>'retrieval')::float) as avg_retrieval_time,
        AVG((step_timings->>'generation')::float) as avg_generation_time
    FROM query_runs
    WHERE created_at >= NOW() - INTERVAL '1 hour' * hours_back;
END;
$$ LANGUAGE plpgsql; 