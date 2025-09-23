-- Unified RLS Policies for Visibility-Based Access Control
-- This migration replaces upload_type-based policies with visibility-based access control

-- Drop existing RLS policies for projects
DROP POLICY IF EXISTS "Users can view own projects" ON projects;
DROP POLICY IF EXISTS "Users can manage own projects" ON projects;
DROP POLICY IF EXISTS "Public project access" ON projects;
DROP POLICY IF EXISTS "Public projects are viewable by everyone" ON projects;
DROP POLICY IF EXISTS "Users can view and manage their own projects" ON projects;
DROP POLICY IF EXISTS "Users can insert their own projects" ON projects;

-- Create new unified RLS policies for projects
CREATE POLICY "Public projects readable by all" ON projects
    FOR SELECT USING (visibility = 'public');

CREATE POLICY "Private projects readable by owner" ON projects
    FOR SELECT USING (
        visibility = 'private'
        AND user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'  -- Anonymous users can't access private projects
    );

CREATE POLICY "Internal projects readable by authenticated users" ON projects
    FOR SELECT USING (
        visibility = 'internal'
        AND auth.role() = 'authenticated'
        AND auth.uid() != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Project owners can manage" ON projects
    FOR ALL USING (
        user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'  -- Anonymous users can't manage projects
    );

CREATE POLICY "Service role full access" ON projects
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Drop existing indexing runs policies
DROP POLICY IF EXISTS "Indexing run access" ON indexing_runs;
DROP POLICY IF EXISTS "Public indexing runs are viewable by everyone" ON indexing_runs;
DROP POLICY IF EXISTS "Users can view and manage their own indexing runs" ON indexing_runs;
DROP POLICY IF EXISTS "Users can insert their own indexing runs" ON indexing_runs;

-- Create new indexing runs policies
CREATE POLICY "Public indexing runs readable by all" ON indexing_runs
    FOR SELECT USING (visibility = 'public');

CREATE POLICY "Private indexing runs readable by owner" ON indexing_runs
    FOR SELECT USING (
        visibility = 'private'
        AND user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Internal indexing runs readable by authenticated users" ON indexing_runs
    FOR SELECT USING (
        visibility = 'internal'
        AND auth.role() = 'authenticated'
        AND auth.uid() != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Indexing run owners can manage" ON indexing_runs
    FOR ALL USING (
        user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Service role full access indexing runs" ON indexing_runs
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Drop existing wiki generation runs policies
DROP POLICY IF EXISTS "Public wiki runs are viewable by everyone" ON wiki_generation_runs;
DROP POLICY IF EXISTS "Users can view and manage their own wiki runs" ON wiki_generation_runs;
DROP POLICY IF EXISTS "Users can insert their own wiki runs" ON wiki_generation_runs;

-- Create new wiki generation runs policies
CREATE POLICY "Public wiki runs readable by all" ON wiki_generation_runs
    FOR SELECT USING (visibility = 'public');

CREATE POLICY "Private wiki runs readable by owner" ON wiki_generation_runs
    FOR SELECT USING (
        visibility = 'private'
        AND user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Internal wiki runs readable by authenticated users" ON wiki_generation_runs
    FOR SELECT USING (
        visibility = 'internal'
        AND auth.role() = 'authenticated'
        AND auth.uid() != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Wiki run owners can manage" ON wiki_generation_runs
    FOR ALL USING (
        user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Service role full access wiki runs" ON wiki_generation_runs
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Drop existing documents policies
DROP POLICY IF EXISTS "Public documents are viewable by everyone" ON documents;
DROP POLICY IF EXISTS "Users can view and manage their own documents" ON documents;
DROP POLICY IF EXISTS "Users can insert their own documents" ON documents;

-- Create new documents policies
CREATE POLICY "Public documents readable by all" ON documents
    FOR SELECT USING (visibility = 'public');

CREATE POLICY "Private documents readable by owner" ON documents
    FOR SELECT USING (
        visibility = 'private'
        AND user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Internal documents readable by authenticated users" ON documents
    FOR SELECT USING (
        visibility = 'internal'
        AND auth.role() = 'authenticated'
        AND auth.uid() != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Document owners can manage" ON documents
    FOR ALL USING (
        user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Service role full access documents" ON documents
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Handle query_runs table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'query_runs') THEN
        -- Drop existing query runs policies
        DROP POLICY IF EXISTS "Public query runs are viewable by everyone" ON query_runs;
        DROP POLICY IF EXISTS "Users can view and manage their own query runs" ON query_runs;
        DROP POLICY IF EXISTS "Users can insert their own query runs" ON query_runs;

        -- Create new query runs policies
        CREATE POLICY "Public query runs readable by all" ON query_runs
            FOR SELECT USING (visibility = 'public');

        CREATE POLICY "Private query runs readable by owner" ON query_runs
            FOR SELECT USING (
                visibility = 'private'
                AND user_id = COALESCE(auth.uid()::text, '00000000-0000-0000-0000-000000000000')
                AND user_id != '00000000-0000-0000-0000-000000000000'
            );

        CREATE POLICY "Internal query runs readable by authenticated users" ON query_runs
            FOR SELECT USING (
                visibility = 'internal'
                AND auth.role() = 'authenticated'
                AND auth.uid()::text != '00000000-0000-0000-0000-000000000000'
            );

        CREATE POLICY "Query run owners can manage" ON query_runs
            FOR ALL USING (
                user_id = COALESCE(auth.uid()::text, '00000000-0000-0000-0000-000000000000')
                AND user_id != '00000000-0000-0000-0000-000000000000'
            );

        CREATE POLICY "Service role full access query runs" ON query_runs
            FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    END IF;
END $$;

-- Handle document_chunks table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_chunks') THEN
        -- Drop existing document chunks policies
        DROP POLICY IF EXISTS "Public chunks are viewable by everyone" ON document_chunks;
        DROP POLICY IF EXISTS "Users can view chunks for their documents" ON document_chunks;

        -- Create new document chunks policies
        CREATE POLICY "Public document chunks readable by all" ON document_chunks
            FOR SELECT USING (visibility = 'public');

        CREATE POLICY "Private document chunks readable by document owner" ON document_chunks
            FOR SELECT USING (
                visibility = 'private'
                AND EXISTS (
                    SELECT 1 FROM documents d
                    WHERE d.id = document_chunks.document_id
                    AND d.user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
                    AND d.user_id != '00000000-0000-0000-0000-000000000000'
                )
            );

        CREATE POLICY "Internal document chunks readable by authenticated users" ON document_chunks
            FOR SELECT USING (
                visibility = 'internal'
                AND auth.role() = 'authenticated'
                AND auth.uid() != '00000000-0000-0000-0000-000000000000'
            );

        CREATE POLICY "Service role full access document chunks" ON document_chunks
            FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    END IF;
END $$;