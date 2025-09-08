-- Add email field to indexing_runs table for transactional email notifications
-- Date: 2025-09-08
-- Description: Stores user email for anonymous uploads to enable wiki completion notifications

-- Add email column to indexing_runs table (nullable for authenticated users)
ALTER TABLE indexing_runs ADD COLUMN IF NOT EXISTS email TEXT;

-- Add index for performance when querying by email
CREATE INDEX IF NOT EXISTS idx_indexing_runs_email ON indexing_runs(email) WHERE email IS NOT NULL;

-- Add comment to explain the purpose
COMMENT ON COLUMN indexing_runs.email IS 'User email for notification purposes, stored for anonymous uploads, nullable for authenticated users';