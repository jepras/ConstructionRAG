-- Phase 3: Access control data model additions (with backfills)
-- - Add access_level columns
-- - Add nullable user_id to indexing_runs
-- - Relax user_id nullability where anonymous flows are supported
-- - Backfill access_level values per current data
-- - Set defaults and add helpful indexes

-- 1) Columns
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS access_level VARCHAR(20);

ALTER TABLE indexing_runs
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS access_level VARCHAR(20);

ALTER TABLE query_runs
    ADD COLUMN IF NOT EXISTS access_level VARCHAR(20);

ALTER TABLE wiki_generation_runs
    ADD COLUMN IF NOT EXISTS access_level VARCHAR(20);

-- 2) Allow anonymous flows (drop NOT NULL where applicable)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'user_id'
    ) THEN
        BEGIN
            ALTER TABLE documents ALTER COLUMN user_id DROP NOT NULL;
        EXCEPTION WHEN others THEN
            -- already nullable
            NULL;
        END;
    END IF;
END$$;

DO $$
BEGIN
    BEGIN
        ALTER TABLE query_runs ALTER COLUMN user_id DROP NOT NULL;
    EXCEPTION WHEN others THEN
        -- already nullable
        NULL;
    END;
END$$;

-- 3) Backfill access_level values
-- documents: anonymous → public; owned → private
UPDATE documents
SET access_level = 'public'
WHERE access_level IS NULL AND user_id IS NULL;

UPDATE documents
SET access_level = 'private'
WHERE access_level IS NULL;

-- indexing_runs: if document_id exists, mirror owning document's access_level
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'indexing_runs' AND column_name = 'document_id'
    ) THEN
        UPDATE indexing_runs ir
        SET access_level = 'public'
        FROM documents d
        WHERE ir.access_level IS NULL AND ir.document_id = d.id AND d.user_id IS NULL;
    END IF;
END$$;

UPDATE indexing_runs
SET access_level = 'private'
WHERE access_level IS NULL;

-- query_runs: default private (owner-only)
UPDATE query_runs
SET access_level = 'private'
WHERE access_level IS NULL;

-- wiki_generation_runs: if upload_type exists, email uploads → public
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'wiki_generation_runs' AND column_name = 'upload_type'
    ) THEN
        UPDATE wiki_generation_runs
        SET access_level = 'public'
        WHERE access_level IS NULL AND upload_type = 'email';
    END IF;
END$$;

UPDATE wiki_generation_runs
SET access_level = 'private'
WHERE access_level IS NULL;

-- 4) Set column defaults
ALTER TABLE documents ALTER COLUMN access_level SET DEFAULT 'private';
ALTER TABLE indexing_runs ALTER COLUMN access_level SET DEFAULT 'private';
ALTER TABLE query_runs ALTER COLUMN access_level SET DEFAULT 'private';
ALTER TABLE wiki_generation_runs ALTER COLUMN access_level SET DEFAULT 'private';

-- 5) Indexes (performance)
CREATE INDEX IF NOT EXISTS idx_documents_access_level ON documents(access_level);
CREATE INDEX IF NOT EXISTS idx_documents_user_access ON documents(user_id, access_level);

CREATE INDEX IF NOT EXISTS idx_indexing_runs_access_level ON indexing_runs(access_level);
CREATE INDEX IF NOT EXISTS idx_indexing_runs_user_access ON indexing_runs(user_id, access_level);

CREATE INDEX IF NOT EXISTS idx_query_runs_access_level ON query_runs(access_level);
CREATE INDEX IF NOT EXISTS idx_query_runs_user_access ON query_runs(user_id, access_level);

CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_access_level ON wiki_generation_runs(access_level);
CREATE INDEX IF NOT EXISTS idx_wiki_generation_runs_user_access ON wiki_generation_runs(user_id, access_level);


