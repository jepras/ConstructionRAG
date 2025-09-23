-- Unified Storage Migration
-- This migration implements the unified storage pattern with GitHub-style URLs

-- Add username column to user_profiles if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'user_profiles' AND column_name = 'username') THEN
        ALTER TABLE user_profiles ADD COLUMN username TEXT UNIQUE;

        -- Set username for existing users (using email prefix or generated value)
        UPDATE user_profiles
        SET username = CASE
            WHEN email IS NOT NULL THEN LOWER(SPLIT_PART(email, '@', 1))
            ELSE 'user_' || SUBSTRING(id::text, 1, 8)
        END
        WHERE username IS NULL AND id != '00000000-0000-0000-0000-000000000000';

        -- Make username NOT NULL after setting values
        ALTER TABLE user_profiles ALTER COLUMN username SET NOT NULL;
    END IF;
END $$;

-- Create the anonymous user in auth.users first
INSERT INTO auth.users (
    id,
    instance_id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    created_at,
    updated_at,
    is_anonymous
)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    'anonymous@anonymous.local',
    '',
    NOW(),
    NOW(),
    NOW(),
    true
) ON CONFLICT (id) DO NOTHING;

-- Create the anonymous user profile after username column exists
INSERT INTO user_profiles (id, username, full_name, created_at)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'anonymous',
    'Anonymous User',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Update NULL user_ids in projects table to use ANONYMOUS_USER_ID
UPDATE projects
SET user_id = '00000000-0000-0000-0000-000000000000'
WHERE user_id IS NULL;

-- Make user_id NOT NULL in projects table
ALTER TABLE projects ALTER COLUMN user_id SET NOT NULL;

-- Add new columns to projects table for GitHub-style URLs
DO $$
BEGIN
    -- Add username column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'projects' AND column_name = 'username') THEN
        ALTER TABLE projects ADD COLUMN username TEXT NOT NULL DEFAULT 'anonymous';
    END IF;

    -- Add project_slug column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'projects' AND column_name = 'project_slug') THEN
        ALTER TABLE projects ADD COLUMN project_slug TEXT NOT NULL DEFAULT '';
    END IF;

    -- Add visibility column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'projects' AND column_name = 'visibility') THEN
        ALTER TABLE projects ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
            CHECK (visibility IN ('public', 'private', 'internal'));
    END IF;
END $$;

-- Update existing projects with username, project_slug, and visibility
UPDATE projects
SET username = (
    CASE
        WHEN user_id = '00000000-0000-0000-0000-000000000000' THEN 'anonymous'
        ELSE COALESCE((SELECT up.username FROM user_profiles up WHERE up.id = projects.user_id), 'anonymous')
    END
),
project_slug = LOWER(REGEXP_REPLACE(COALESCE(name, 'untitled-project'), '[^a-zA-Z0-9]', '-', 'g')),
visibility = CASE
    WHEN access_level = 'public' THEN 'public'
    WHEN access_level = 'private' THEN 'private'
    ELSE 'internal'
END
WHERE username = 'anonymous' OR project_slug = '';

-- Create unique constraint for username/project_slug combination
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'projects_username_slug_unique') THEN
        ALTER TABLE projects
        ADD CONSTRAINT projects_username_slug_unique
        UNIQUE (username, project_slug);
    END IF;
END $$;

-- Update NULL user_ids in indexing_runs table
UPDATE indexing_runs
SET user_id = '00000000-0000-0000-0000-000000000000'
WHERE user_id IS NULL;

-- Make user_id NOT NULL in indexing_runs
ALTER TABLE indexing_runs ALTER COLUMN user_id SET NOT NULL;

-- Add visibility column to indexing_runs
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'indexing_runs' AND column_name = 'visibility') THEN
        ALTER TABLE indexing_runs ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
            CHECK (visibility IN ('public', 'private', 'internal'));
    END IF;
END $$;

-- Update visibility in indexing_runs based on old patterns
UPDATE indexing_runs
SET visibility = CASE
    WHEN upload_type = 'email' THEN 'public'
    WHEN access_level = 'public' THEN 'public'
    ELSE 'private'
END
WHERE visibility = 'private';

-- Add visibility to wiki_generation_runs
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'wiki_generation_runs' AND column_name = 'visibility') THEN
        ALTER TABLE wiki_generation_runs ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
            CHECK (visibility IN ('public', 'private', 'internal'));
    END IF;
END $$;

-- Update visibility in wiki_generation_runs
UPDATE wiki_generation_runs
SET visibility = CASE
    WHEN EXISTS (SELECT 1 FROM indexing_runs ir WHERE ir.id = wiki_generation_runs.indexing_run_id AND ir.upload_type = 'email') THEN 'public'
    WHEN EXISTS (SELECT 1 FROM indexing_runs ir WHERE ir.id = wiki_generation_runs.indexing_run_id AND ir.access_level = 'public') THEN 'public'
    ELSE 'private'
END
WHERE visibility = 'private';

-- Add visibility to documents table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'documents' AND column_name = 'visibility') THEN
        ALTER TABLE documents ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
            CHECK (visibility IN ('public', 'private', 'internal'));
    END IF;
END $$;

-- Update visibility in documents
UPDATE documents
SET visibility = CASE
    WHEN access_level = 'public' THEN 'public'
    ELSE 'private'
END
WHERE visibility = 'private';

-- Update NULL user_ids in documents table if the column exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'documents' AND column_name = 'user_id') THEN
        UPDATE documents
        SET user_id = '00000000-0000-0000-0000-000000000000'
        WHERE user_id IS NULL;

        ALTER TABLE documents ALTER COLUMN user_id SET NOT NULL;
    END IF;
END $$;

-- Add visibility to query_runs if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'query_runs') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'query_runs' AND column_name = 'visibility') THEN
            ALTER TABLE query_runs ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
                CHECK (visibility IN ('public', 'private', 'internal'));
        END IF;

        -- Update NULL user_ids in query_runs
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'query_runs' AND column_name = 'user_id') THEN
            UPDATE query_runs
            SET user_id = '00000000-0000-0000-0000-000000000000'
            WHERE user_id IS NULL;

            ALTER TABLE query_runs ALTER COLUMN user_id SET NOT NULL;
        END IF;

        -- Update visibility based on access patterns
        UPDATE query_runs
        SET visibility = CASE
            WHEN access_level = 'public' THEN 'public'
            ELSE 'private'
        END
        WHERE visibility = 'private';
    END IF;
END $$;

-- Add visibility to document_chunks if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_chunks') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'document_chunks' AND column_name = 'visibility') THEN
            ALTER TABLE document_chunks ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
                CHECK (visibility IN ('public', 'private', 'internal'));
        END IF;

        -- Update visibility based on parent document
        UPDATE document_chunks
        SET visibility = (
            SELECT COALESCE(d.visibility, 'private')
            FROM documents d
            WHERE d.id = document_chunks.document_id
        )
        WHERE visibility = 'private';
    END IF;
END $$;