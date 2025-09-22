-- Add indexing_status field to documents table
ALTER TABLE documents
ADD COLUMN indexing_status TEXT DEFAULT 'pending' CHECK (indexing_status IN ('pending', 'running', 'completed', 'failed'));

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_documents_indexing_status ON documents (indexing_status);

-- Add comment for documentation
COMMENT ON COLUMN documents.indexing_status IS 'Tracks the indexing pipeline status for each document: pending, running, completed, failed';

-- Update existing documents to have 'completed' status if they have step results
UPDATE documents 
SET indexing_status = 'completed' 
WHERE step_results IS NOT NULL AND step_results != '{}' AND indexing_status = 'pending'; 