-- Add all_sources column to checklist_results table for multi-source support
-- This column will store a JSON array of source references

ALTER TABLE checklist_results 
ADD COLUMN IF NOT EXISTS all_sources JSONB;

-- Create an index on the JSONB column for performance
CREATE INDEX IF NOT EXISTS idx_checklist_results_all_sources 
    ON checklist_results USING gin(all_sources);

-- Add a comment explaining the column
COMMENT ON COLUMN checklist_results.all_sources IS 'JSON array of source references: [{"document": "file.pdf", "page": 12, "excerpt": "quote"}]';