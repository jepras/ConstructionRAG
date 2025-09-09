-- Add email_notifications_enabled column to indexing_runs table
-- This column controls whether email notifications should be sent when processing is complete

ALTER TABLE indexing_runs 
ADD COLUMN email_notifications_enabled BOOLEAN DEFAULT true;

-- Add comment to document the column purpose
COMMENT ON COLUMN indexing_runs.email_notifications_enabled IS 'Whether to send email notifications when processing is complete. Defaults to true.';