-- RLS rollout aligned to AccessLevel semantics (public/auth/owner/private)
-- Enable RLS and define SELECT/INSERT/UPDATE/DELETE policies

-- Documents
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS doc_select_policy ON public.documents;
CREATE POLICY doc_select_policy ON public.documents
FOR SELECT
USING (
  access_level = 'public'
  OR (access_level = 'auth' AND current_setting('request.jwt.claims', true)::jsonb ? 'sub')
  OR (user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, ''))
);

DROP POLICY IF EXISTS doc_modify_owner_policy ON public.documents;
CREATE POLICY doc_modify_owner_policy ON public.documents
FOR ALL
USING (
  user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
)
WITH CHECK (
  user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
);

-- Indexing runs
ALTER TABLE public.indexing_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS idx_select_policy ON public.indexing_runs;
CREATE POLICY idx_select_policy ON public.indexing_runs
FOR SELECT
USING (
  (access_level = 'public' AND upload_type = 'email')
  OR (access_level = 'auth' AND current_setting('request.jwt.claims', true)::jsonb ? 'sub')
  OR (user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, ''))
  OR (
    project_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = indexing_runs.project_id AND p.user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
    )
  )
);

DROP POLICY IF EXISTS idx_modify_owner_policy ON public.indexing_runs;
CREATE POLICY idx_modify_owner_policy ON public.indexing_runs
FOR ALL
USING (
  user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
)
WITH CHECK (
  true
);

-- Document chunks
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS chunks_select_policy ON public.document_chunks;
CREATE POLICY chunks_select_policy ON public.document_chunks
FOR SELECT
USING (
  -- Allowed if parent document visible
  EXISTS (
    SELECT 1 FROM public.documents d
    WHERE d.id = document_chunks.document_id AND (
      d.access_level = 'public'
      OR (d.access_level = 'auth' AND current_setting('request.jwt.claims', true)::jsonb ? 'sub')
      OR (d.user_id IS NOT NULL AND d.user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, ''))
    )
  )
  OR
  -- Or allowed via visible indexing run
  EXISTS (
    SELECT 1 FROM public.indexing_runs r
    WHERE r.id = document_chunks.indexing_run_id AND (
      (r.access_level = 'public' AND r.upload_type = 'email')
      OR (r.access_level = 'auth' AND current_setting('request.jwt.claims', true)::jsonb ? 'sub')
      OR (r.user_id IS NOT NULL AND r.user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, ''))
      OR (
        r.project_id IS NOT NULL AND EXISTS (
          SELECT 1 FROM public.projects p
          WHERE p.id = r.project_id AND p.user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
        )
      )
    )
  )
);

-- Query runs
ALTER TABLE public.query_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS query_select_policy ON public.query_runs;
CREATE POLICY query_select_policy ON public.query_runs
FOR SELECT
USING (
  access_level = 'public'
  OR (access_level = 'auth' AND current_setting('request.jwt.claims', true)::jsonb ? 'sub')
  OR (user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, ''))
);

DROP POLICY IF EXISTS query_modify_owner_policy ON public.query_runs;
CREATE POLICY query_modify_owner_policy ON public.query_runs
FOR ALL
USING (
  user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
)
WITH CHECK (
  true
);

-- Wiki generation runs
ALTER TABLE public.wiki_generation_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS wiki_select_policy ON public.wiki_generation_runs;
CREATE POLICY wiki_select_policy ON public.wiki_generation_runs
FOR SELECT
USING (
  access_level = 'public'
  OR (access_level = 'auth' AND current_setting('request.jwt.claims', true)::jsonb ? 'sub')
  OR (user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, ''))
  OR (
    project_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = wiki_generation_runs.project_id AND p.user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
    )
  )
);

DROP POLICY IF EXISTS wiki_modify_owner_policy ON public.wiki_generation_runs;
CREATE POLICY wiki_modify_owner_policy ON public.wiki_generation_runs
FOR ALL
USING (
  user_id IS NOT NULL AND user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
)
WITH CHECK (
  true
);

-- Optional: ensure auth context is present when needed (no-op when anon)
-- Supabase automatically injects JWT into request.jwt.claims; no further setup here.


