-- Migration: Fix indexing_runs table for email uploads
-- Date: 2025-08-01
-- Description: Clean up existing data and fix schema for email uploads

-- Clean up all existing data (keeping auth tables intact)
TRUNCATE TABLE email_uploads CASCADE;
TRUNCATE TABLE documents CASCADE;
TRUNCATE TABLE indexing_runs CASCADE;
TRUNCATE TABLE query_runs CASCADE;
TRUNCATE TABLE projects CASCADE;
TRUNCATE TABLE user_config_overrides CASCADE;

-- Make document_id nullable since email uploads don't create document records
ALTER TABLE indexing_runs ALTER COLUMN document_id DROP NOT NULL;

-- Add a check constraint to ensure document_id is provided for user_project uploads
ALTER TABLE indexing_runs ADD CONSTRAINT check_document_id_for_user_projects 
    CHECK (
        (upload_type = 'user_project' AND document_id IS NOT NULL) OR
        (upload_type = 'email' AND document_id IS NULL)
    ); 