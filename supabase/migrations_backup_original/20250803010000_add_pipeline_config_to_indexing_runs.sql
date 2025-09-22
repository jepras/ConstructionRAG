-- Migration: Add pipeline_config field to indexing_runs table for configuration tracking
-- Date: 2025-08-03

-- Add pipeline_config field to indexing_runs table
-- This stores the exact configuration used for each indexing run
ALTER TABLE indexing_runs 
ADD COLUMN pipeline_config JSONB DEFAULT '{}';

-- Add index for better performance when querying pipeline configs
CREATE INDEX IF NOT EXISTS idx_indexing_runs_pipeline_config ON indexing_runs USING GIN (pipeline_config);

-- Add comment to document the field purpose
COMMENT ON COLUMN indexing_runs.pipeline_config IS 'Stores the exact pipeline configuration used for this indexing run, including all step configurations and user overrides'; 