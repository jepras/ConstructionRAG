-- Migration: Add pipeline_config field to query_runs table for configuration tracking

-- 1) Add pipeline_config column if it doesn't exist
ALTER TABLE query_runs
ADD COLUMN IF NOT EXISTS pipeline_config JSONB DEFAULT '{}';

-- 2) Create GIN index for faster querying/filtering if needed
CREATE INDEX IF NOT EXISTS idx_query_runs_pipeline_config ON query_runs USING GIN (pipeline_config);

-- 3) Comment for documentation
COMMENT ON COLUMN query_runs.pipeline_config IS 'Stores the exact pipeline configuration used for this query run, including step configurations and user overrides';

